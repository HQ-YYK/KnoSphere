"""
知识图谱提取服务
使用 LLM 自动从文档中提取实体和关系
"""

import re
from typing import List, Dict, Any, Optional, Tuple
import json
import asyncio
from datetime import datetime, timezone
from sqlmodel import Session, select
import logging

from models import Entity, GraphEdge, EntityDocumentLink, Document
from services.llm import get_llm_service
from core.logger import logger
from services.langsmith_integration import trace_function

# 预定义的关系类型
RELATION_TYPES = {
    # 人物相关
    "person-person": ["同事", "合作", "朋友", "家人", "导师", "学生"],
    "person-org": ["任职于", "创办", "管理", "隶属于", "代表"],
    "person-concept": ["研究", "擅长", "提出", "发明", "开发"],
    "person-product": ["开发", "设计", "使用", "推广"],
    
    # 组织相关
    "org-org": ["合作", "竞争", "子公司", "母公司", "收购", "合并"],
    "org-concept": ["专注于", "涉及", "投资于", "研究"],
    "org-product": ["开发", "生产", "销售", "拥有"],
    "org-location": ["位于", "总部在", "分公司在"],
    
    # 概念相关
    "concept-concept": ["相关", "属于", "包含", "对立", "补充"],
    "concept-product": ["应用于", "实现为", "体现于"],
    
    # 产品相关
    "product-product": ["替代", "竞争", "互补", "依赖"],
    "product-location": ["产自", "销售于", "流行于"],
    
    # 通用
    "general": ["关联", "影响", "导致", "促进", "限制"]
}

class GraphExtractor:
    """知识图谱提取器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.llm_service = get_llm_service()
        
    
    @trace_function(name="Graph-Extraction", run_type="chain")
    async def extract_from_document(self, document: Document) -> Dict[str, Any]:
        """从单个文档中提取知识图谱"""
        try:
            logger.info(f"开始从文档提取知识图谱: {document.id} - {document.title}")
            
            content = document.content
            if not content or len(content) < 50:
                logger.warning(f"文档内容太短，跳过图谱提取: {document.id}")
                return {"success": False, "error": "内容太短"}
            
            # 分块处理（大文档需要分块）
            chunks = self._split_into_chunks(content)
            
            all_entities = []
            all_relations = []
            
            # 处理每个块
            for i, chunk in enumerate(chunks):
                logger.debug(f"处理文档块 {i+1}/{len(chunks)}")
                
                # 提取实体
                entities = await self._extract_entities_from_chunk(chunk, document.id)
                all_entities.extend(entities)
                
                # 提取关系（如果有足够实体）
                if len(entities) >= 2:
                    relations = await self._extract_relations_from_chunk(chunk, entities, document.id)
                    all_relations.extend(relations)
                
                # 避免过快请求
                await asyncio.sleep(0.1)
            
            # 去重和合并实体
            unique_entities = self._merge_entities(all_entities)
            
            # 保存到数据库
            saved_entities = await self._save_entities_to_db(unique_entities, document)
            saved_relations = await self._save_relations_to_db(all_relations, document)
            
            # 更新文档状态
            document.graph_extracted = True
            document.graph_extraction_time = datetime.now(timezone.utc)
            self.db.add(document)
            self.db.commit()
            
            logger.info(f"文档知识图谱提取完成: {document.id}, "
                       f"实体: {len(saved_entities)}, 关系: {len(saved_relations)}")
            
            return {
                "success": True,
                "document_id": document.id,
                "entities_extracted": len(all_entities),
                "entities_saved": len(saved_entities),
                "relations_extracted": len(all_relations),
                "relations_saved": len(saved_relations),
                "entities": saved_entities,
                "relations": saved_relations
            }
            
        except Exception as e:
            logger.error(f"文档图谱提取失败: {document.id}, 错误: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _split_into_chunks(self, text: str, chunk_size: int = 2000) -> List[str]:
        """将文本分割成块"""
        # 按段落分割
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def _extract_entities_from_chunk(self, chunk: str, document_id: int) -> List[Dict[str, Any]]:
        """从文本块中提取实体"""
        system_prompt = """你是一个专业的实体提取专家。请从文本中提取所有重要的实体。

实体类型包括：
1. PERSON - 人名、职位
2. ORGANIZATION - 公司、机构、团队
3. CONCEPT - 概念、理论、技术、方法
4. PRODUCT - 产品、工具、软件、服务
5. LOCATION - 地点、国家、城市
6. EVENT - 事件、会议、活动

请严格按照以下 JSON 格式输出：
[
  {
    "name": "实体名称",
    "type": "实体类型",
    "description": "简要描述",
    "confidence": 0.8
  }
]

要求：
1. 只提取文本中明确提到的实体
2. 确保名称准确完整
3. 给出合适的描述
4. 输出必须是有效的 JSON 数组"""

        try:
            response_text = ""
            async for chunk in self.llm_service.stream_response(system_prompt, f"请从以下文本中提取实体：\n\n{chunk}"):
                response_text += chunk
            
            # 清理响应，提取 JSON 部分
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                entities_json = json_match.group()
                entities = json.loads(entities_json)
                
                # 添加元数据
                for entity in entities:
                    entity['source_chunk'] = chunk[:500]
                    entity['source_document_id'] = document_id
                
                return entities
            else:
                # 尝试直接解析整个响应
                try:
                    entities = json.loads(response_text)
                    for entity in entities:
                        entity['source_chunk'] = chunk[:500]
                        entity['source_document_id'] = document_id
                    return entities
                except:
                    logger.warning(f"无法解析实体提取响应: {response_text[:200]}")
                    return []
                    
        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return []
    
    async def _extract_relations_from_chunk(self, chunk: str, entities: List[Dict], document_id: int) -> List[Dict[str, Any]]:
        """从文本块中提取实体关系"""
        if len(entities) < 2:
            return []
        
        # 准备实体列表
        entity_list = [f"{i+1}. {e['name']} ({e['type']})" for i, e in enumerate(entities)]
        
        system_prompt = f"""你是一个关系提取专家。请分析文本中的实体之间的关系。

文本中的实体：
{chr(10).join(entity_list)}

关系类型包括（但不仅限于）：
- 任职于、隶属于、管理、创办
- 合作、竞争、收购、合并
- 研究、开发、设计、生产
- 位于、总部在、分公司在
- 影响、导致、促进、限制
- 属于、包含、相关、对立

请严格按照以下 JSON 格式输出：
[
  {{
    "source": "源实体名称",
    "target": "目标实体名称",
    "relation": "关系类型",
    "description": "关系描述",
    "confidence": 0.8,
    "context": "出现此关系的原文片段"
  }}
]

要求：
1. 只提取文本中明确提到的关系
2. 关系必须是双向的（如：A管理B，B隶属于A）
3. 提供具体的原文片段作为证据
4. 输出必须是有效的 JSON 数组"""

        try:
            response_text = ""
            async for chunk in self.llm_service.stream_response(system_prompt, f"请分析以下文本中实体之间的关系：\n\n{chunk}"):
                response_text += chunk
            
            # 清理响应，提取 JSON 部分
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                relations_json = json_match.group()
                relations = json.loads(relations_json)
                
                # 验证关系中的实体是否存在
                valid_relations = []
                entity_names = [e['name'] for e in entities]
                
                for rel in relations:
                    if rel['source'] in entity_names and rel['target'] in entity_names:
                        rel['source_document_id'] = document_id
                        valid_relations.append(rel)
                
                return valid_relations
            else:
                return []
                
        except Exception as e:
            logger.error(f"关系提取失败: {e}")
            return []
    
    def _merge_entities(self, entities: List[Dict]) -> List[Dict]:
        """合并相同的实体"""
        entity_map = {}
        
        for entity in entities:
            name = entity['name'].strip()
            normalized_name = name.lower().replace(' ', '_')
            
            if normalized_name not in entity_map:
                entity_map[normalized_name] = {
                    'name': name,
                    'type': entity['type'],
                    'description': entity.get('description', ''),
                    'confidence': entity.get('confidence', 0.0),
                    'frequency': 1,
                    'source_chunks': [entity.get('source_chunk', '')],
                    'source_documents': [entity.get('source_document_id')]
                }
            else:
                # 合并相同实体
                existing = entity_map[normalized_name]
                existing['frequency'] += 1
                if entity.get('description'):
                    existing['description'] = entity['description']
                existing['confidence'] = max(existing['confidence'], entity.get('confidence', 0.0))
                existing['source_chunks'].append(entity.get('source_chunk', ''))
                if entity.get('source_document_id') not in existing['source_documents']:
                    existing['source_documents'].append(entity.get('source_document_id'))
        
        # 转换为列表
        merged_entities = []
        for norm_name, data in entity_map.items():
            merged_entities.append({
                'name': data['name'],
                'normalized_name': norm_name,
                'type': data['type'],
                'description': data['description'],
                'confidence': data['confidence'],
                'frequency': data['frequency'],
                'metadata': {
                    'source_chunks': data['source_chunks'][:5],  # 保留前5个上下文
                    'source_document_ids': data['source_documents']
                }
            })
        
        return merged_entities
    
    async def _save_entities_to_db(self, entities: List[Dict], document: Document) -> List[Entity]:
        """保存实体到数据库"""
        saved_entities = []
        
        for entity_data in entities:
            try:
                # 检查是否已存在
                normalized_name = entity_data['normalized_name']
                existing_entity = self.db.exec(
                    select(Entity).where(
                        Entity.normalized_name == normalized_name,
                        Entity.user_id == document.user_id
                    )
                ).first()
                
                if existing_entity:
                    # 更新现有实体
                    existing_entity.frequency += entity_data['frequency']
                    existing_entity.confidence = max(existing_entity.confidence, entity_data['confidence'])
                    if entity_data.get('description'):
                        existing_entity.description = entity_data['description']
                    
                    # 更新元数据
                    if existing_entity.metadata:
                        metadata = existing_entity.metadata.copy()
                        if 'source_document_ids' in metadata:
                            if document.id not in metadata['source_document_ids']:
                                metadata['source_document_ids'].append(document.id)
                        else:
                            metadata['source_document_ids'] = [document.id]
                        existing_entity.metadata = metadata
                    else:
                        existing_entity.metadata = {'source_document_ids': [document.id]}
                    
                    existing_entity.updated_at = datetime.now(timezone.utc)
                    self.db.add(existing_entity)
                    saved_entity = existing_entity
                else:
                    # 创建新实体
                    saved_entity = Entity(
                        name=entity_data['name'],
                        normalized_name=normalized_name,
                        entity_type=entity_data['type'],
                        description=entity_data.get('description'),
                        frequency=entity_data['frequency'],
                        confidence=entity_data['confidence'],
                        metadata=entity_data.get('metadata', {}),
                        user_id=document.user_id
                    )
                    self.db.add(saved_entity)
                
                # 创建实体-文档关联
                link = EntityDocumentLink(
                    entity_id=saved_entity.id if saved_entity.id else None,  # 会在提交后获取
                    document_id=document.id,
                    frequency_in_doc=entity_data['frequency'],
                    significance=entity_data['confidence']
                )
                self.db.add(link)
                
                self.db.flush()  # 获取ID但不提交
                saved_entities.append(saved_entity)
                
            except Exception as e:
                logger.error(f"保存实体失败: {entity_data.get('name')}, 错误: {e}")
                continue
        
        self.db.commit()
        return saved_entities
    
    async def _save_relations_to_db(self, relations: List[Dict], document: Document) -> List[GraphEdge]:
        """保存关系到数据库"""
        saved_relations = []
        
        for rel_data in relations:
            try:
                # 查找源实体和目标实体
                source_entity = self.db.exec(
                    select(Entity).where(
                        Entity.name == rel_data['source'],
                        Entity.user_id == document.user_id
                    )
                ).first()
                
                target_entity = self.db.exec(
                    select(Entity).where(
                        Entity.name == rel_data['target'],
                        Entity.user_id == document.user_id
                    )
                ).first()
                
                if not source_entity or not target_entity:
                    logger.warning(f"找不到实体: {rel_data['source']} -> {rel_data['target']}")
                    continue
                
                # 检查关系是否已存在
                existing_edge = self.db.exec(
                    select(GraphEdge).where(
                        GraphEdge.source_id == source_entity.id,
                        GraphEdge.target_id == target_entity.id,
                        GraphEdge.relation_type == rel_data['relation'],
                        GraphEdge.user_id == document.user_id
                    )
                ).first()
                
                if existing_edge:
                    # 更新现有关系
                    existing_edge.weight = max(existing_edge.weight, rel_data.get('weight', 1.0))
                    existing_edge.confidence = max(existing_edge.confidence, rel_data.get('confidence', 0.0))
                    if rel_data.get('description'):
                        existing_edge.description = rel_data['description']
                    existing_edge.updated_at = datetime.now(timezone.utc)
                    saved_relations.append(existing_edge)
                else:
                    # 创建新关系
                    edge = GraphEdge(
                        source_id=source_entity.id,
                        target_id=target_entity.id,
                        relation_type=rel_data['relation'],
                        description=rel_data.get('description'),
                        weight=rel_data.get('weight', 1.0),
                        confidence=rel_data.get('confidence', 0.0),
                        source_document_id=document.id,
                        source_context=rel_data.get('context', ''),
                        user_id=document.user_id
                    )
                    self.db.add(edge)
                    saved_relations.append(edge)
                
            except Exception as e:
                logger.error(f"保存关系失败: {rel_data.get('source')} -> {rel_data.get('target')}, 错误: {e}")
                continue
        
        self.db.commit()
        return saved_relations

# 全局提取器实例
_graph_extractor = None

def get_graph_extractor(db: Session) -> GraphExtractor:
    """获取图谱提取器实例"""
    global _graph_extractor
    if _graph_extractor is None:
        _graph_extractor = GraphExtractor(db)
    return _graph_extractor