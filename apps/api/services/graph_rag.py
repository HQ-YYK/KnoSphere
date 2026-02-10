# services/graph_rag.py
"""
GraphRAG 查询引擎
结合向量搜索和知识图谱进行智能问答
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import Session, select, or_
import json
import networkx as nx
from collections import defaultdict

from models import Entity, GraphEdge, Document, EntityDocumentLink
from services.search import secure_hybrid_search
from services.llm import get_llm_service
from core.logger import logger
from services.langsmith_integration import trace_function

class GraphRAGService:
    """GraphRAG 服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm_service = get_llm_service()
    
    @trace_function(name="GraphRAG-Query", run_type="chain")
    async def query(self, query: str, user_id: str, top_k: int = 10) -> Dict[str, Any]:
        """GraphRAG 查询"""
        try:
            # 步骤1: 向量搜索（传统的 RAG）
            documents = await secure_hybrid_search(query, self.db, user_id=user_id, top_k=top_k)
            
            # 步骤2: 从相关文档中提取关键实体
            key_entities = await self._extract_key_entities_from_docs(query, documents)
            
            # 步骤3: 在知识图谱中查找相关实体和路径
            graph_results = await self._query_knowledge_graph(query, key_entities, user_id)
            
            # 步骤4: 结合文档和图谱结果生成最终回答
            final_answer = await self._generate_final_answer(query, documents, graph_results)
            
            return {
                "success": True,
                "query": query,
                "answer": final_answer,
                "documents_used": [doc['id'] for doc in documents[:3]],
                "entities_found": [e['name'] for e in graph_results['entities'][:5]],
                "paths_found": len(graph_results['paths']),
                "documents": documents[:5],
                "graph": graph_results
            }
            
        except Exception as e:
            logger.error(f"GraphRAG 查询失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "answer": f"抱歉，GraphRAG 查询失败: {str(e)}"
            }
    
    async def _extract_key_entities_from_docs(self, query: str, documents: List[Dict]) -> List[Dict]:
        """从相关文档中提取关键实体"""
        # 合并文档内容
        content = "\n\n".join([doc.get('content', '')[:500] for doc in documents[:3]])
        
        system_prompt = """你是一个实体识别专家。请从给定的文本中提取与用户问题相关的关键实体。

请输出 JSON 格式：
[
  {
    "name": "实体名称",
    "type": "实体类型",
    "relevance": 0.8
  }
]

只提取最相关的3-5个实体。"""
        
        full_prompt = f"用户问题: {query}\n\n相关文本:\n{content}"
        
        response = ""
        async for chunk in self.llm_service.stream_response(system_prompt, full_prompt):
            response += chunk
        
        try:
            # 提取 JSON
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return []
    
    async def _query_knowledge_graph(self, query: str, key_entities: List[Dict], user_id: str) -> Dict[str, Any]:
        """查询知识图谱"""
        if not key_entities:
            return {"entities": [], "paths": [], "subgraph": {}}
        
        # 查找相关实体
        entity_names = [e['name'] for e in key_entities]
        entities = self.db.exec(
            select(Entity).where(
                or_(*[Entity.name.ilike(f"%{name}%") for name in entity_names]),
                Entity.user_id == user_id
            ).limit(20)
        ).all()
        
        if not entities:
            return {"entities": [], "paths": [], "subgraph": {}}
        
        # 构建图网络
        G = nx.Graph()
        
        # 添加节点
        for entity in entities:
            G.add_node(entity.id, 
                      name=entity.name,
                      type=entity.entity_type,
                      data=entity.to_dict())
        
        # 添加边
        entity_ids = [e.id for e in entities]
        edges = self.db.exec(
            select(GraphEdge).where(
                or_(
                    GraphEdge.source_id.in_(entity_ids),
                    GraphEdge.target_id.in_(entity_ids)
                ),
                GraphEdge.user_id == user_id
            ).limit(100)
        ).all()
        
        for edge in edges:
            if edge.source_id in entity_ids and edge.target_id in entity_ids:
                G.add_edge(edge.source_id, edge.target_id,
                          relation=edge.relation_type,
                          weight=edge.weight,
                          data=edge.to_dict())
        
        # 查找连接路径
        paths = []
        for i in range(min(5, len(entities))):
            for j in range(i+1, min(5, len(entities))):
                try:
                    if nx.has_path(G, entities[i].id, entities[j].id):
                        path = nx.shortest_path(G, entities[i].id, entities[j].id)
                        if len(path) <= 4:  # 只保留短路径
                            paths.append(path)
                except:
                    continue
        
        # 构建子图数据（用于前端可视化）
        subgraph = self._build_subgraph_data(G, entities[:10], edges)
        
        return {
            "entities": [e.to_dict() for e in entities],
            "paths": paths,
            "subgraph": subgraph
        }
    
    def _build_subgraph_data(self, graph: nx.Graph, entities: List[Entity], edges: List[GraphEdge]) -> Dict[str, Any]:
        """构建子图数据用于可视化"""
        nodes = []
        links = []
        
        # 节点
        for entity in entities:
            # 获取关联的文档信息
            related_docs = []
            if hasattr(entity, 'documents') and entity.documents:
                # 实体直接关联的文档
                for doc in entity.documents[:3]:  # 只取前3个相关文档
                    if hasattr(doc, 'id') and hasattr(doc, 'title'):
                        related_docs.append({
                            "id": doc.id,
                            "title": doc.title,
                            "content_preview": doc.content[:100] if hasattr(doc, 'content') else ""
                        })
            else:
                # 通过实体-文档关联表查询
                from models import EntityDocumentLink
                try:
                    doc_links = self.db.exec(
                        select(EntityDocumentLink).where(EntityDocumentLink.entity_id == entity.id)
                    ).all()
                    
                    for link in doc_links[:3]:  # 只取前3个
                        doc = self.db.get(Document, link.document_id)
                        if doc:
                            related_docs.append({
                                "id": doc.id,
                                "title": doc.title,
                                "content_preview": doc.content[:100] if doc.content else ""
                            })
                except:
                    pass
            
            nodes.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.entity_type,
                "description": entity.description,
                "size": entity.frequency,
                "group": self._get_entity_group(entity.entity_type),
                "documents": related_docs,  # 关联文档信息
                "primary_doc_id": related_docs[0]["id"] if related_docs else None,
                "doc_count": len(related_docs),
                "metadata": entity.metadata or {}
            })
        
        # 边
        for edge in edges:
            if graph.has_edge(edge.source_id, edge.target_id):
                links.append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relation": edge.relation_type,
                    "weight": edge.weight,
                    "description": edge.description,
                    "source_document_id": edge.source_document_id,
                    "context": edge.source_context[:100] if edge.source_context else None
                })
        
        return {"nodes": nodes, "links": links}
    
    def _get_entity_group(self, entity_type: str) -> int:
        """根据实体类型返回组ID"""
        type_groups = {
            "PERSON": 1,
            "ORGANIZATION": 2,
            "CONCEPT": 3,
            "PRODUCT": 4,
            "LOCATION": 5,
            "EVENT": 6
        }
        return type_groups.get(entity_type.upper(), 0)
    
    async def _generate_final_answer(self, query: str, documents: List[Dict], graph_results: Dict) -> str:
        """结合文档和图谱生成最终回答"""
        # 准备文档上下文
        doc_context = "\n".join([
            f"文档 {i+1}: {doc.get('title', '无标题')}\n内容: {doc.get('content', '')[:300]}"
            for i, doc in enumerate(documents[:3])
        ])
        
        # 准备图谱上下文
        graph_context = ""
        if graph_results['entities']:
            graph_context = "知识图谱信息:\n"
            for entity in graph_results['entities'][:5]:
                graph_context += f"- {entity['name']} ({entity['type']}): {entity.get('description', '无描述')}\n"
            
            if graph_results['paths']:
                graph_context += "\n发现的关系路径:\n"
                for path in graph_results['paths'][:3]:
                    # 这里简化显示路径，实际应该查询实体名称
                    graph_context += f"路径: {' -> '.join([str(p) for p in path])}\n"
        
        system_prompt = f"""你是一个 GraphRAG 助手，同时拥有文档信息和知识图谱信息。

用户问题: {query}

相关文档信息:
{doc_context}

{graph_context}

请结合文档内容和知识图谱信息，给出全面、准确的回答。如果图谱信息与文档信息有冲突，以文档信息为准。

回答要求:
1. 先给出直接回答
2. 然后说明信息来源（哪些文档、哪些实体关系）
3. 如果知识图谱提供了额外的上下文关系，可以说明
4. 保持专业、准确"""
        
        response = ""
        async for chunk in self.llm_service.stream_response(system_prompt, "请根据以上信息回答用户问题"):
            response += chunk
        
        return response

def get_graph_rag_service(db: Session) -> GraphRAGService:
    """获取 GraphRAG 服务实例"""
    return GraphRAGService(db)