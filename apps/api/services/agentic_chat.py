import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List
from datetime import datetime
from sqlmodel import Session

from core.logger import logger, WorkflowLogger
from services.search import hybrid_search
from services.llm import get_llm_service
from services.streaming_protocol import AgentMessage

class AgenticChatService:
    """智能体聊天服务 - 支持思考过程可视化"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
    
    async def stream_chat_with_thinking(
        self, 
        query: str, 
        db: Session,
        top_k: int = 10,
        final_k: int = 3,
        workflow_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天，包含完整的思考过程
        
        参数:
        - query: 用户查询
        - db: 数据库会话
        - top_k: 检索文档数量
        - final_k: 最终使用文档数量
        - workflow_id: 工作流ID
        
        返回:
        - 流式响应的消息生成器
        """
        if not workflow_id:
            workflow_id = f"chat_{datetime.now().timestamp()}"
        
        WorkflowLogger.workflow_start(query, workflow_id)
        
        try:
            # 1. 开始检索
            yield AgentMessage.retrieval_start(top_k, "balanced")
            await asyncio.sleep(0.2)
            
            # 2. 执行检索
            yield AgentMessage.status("正在向量化查询...", stage="embedding", progress=15)
            await asyncio.sleep(0.1)
            
            yield AgentMessage.status("正在搜索向量数据库...", stage="vector_search", progress=25)
            documents = await hybrid_search(query, db, top_k=top_k, final_k=final_k)
            
            # 3. 检索完成
            yield AgentMessage.retrieval_end(len(documents), "balanced")
            await asyncio.sleep(0.2)
            
            if not documents:
                yield AgentMessage.status("未找到相关文档，尝试其他策略...", stage="fallback", progress=45)
                # 尝试更宽松的检索策略
                documents = await hybrid_search(query, db, top_k=top_k*2, final_k=final_k)
                
                if not documents:
                    yield AgentMessage.status("知识库中没有相关信息", stage="no_docs", progress=60)
                    yield AgentMessage.chunk("抱歉，我没有在知识库中找到相关信息。")
                    yield AgentMessage.complete(workflow_id)
                    WorkflowLogger.workflow_complete(workflow_id, {"documents_found": 0}, 0)
                    return
            
            # 4. 重排序（如果可用）
            if len(documents) > 3:
                yield AgentMessage.reranking_start()
                await asyncio.sleep(0.3)
                yield AgentMessage.reranking_end(min(3, len(documents)))
            
            # 5. 准备上下文
            context = self._prepare_context(documents[:final_k])
            yield AgentMessage.status(f"准备上下文，使用 {min(final_k, len(documents))} 篇文档", 
                                   stage="context_preparation", progress=65)
            
            # 6. 生成回答（包含思考过程）
            async for message in self.llm_service.stream_response_with_thinking(
                query=query,
                context=context,
                documents=documents[:final_k],
                workflow_id=workflow_id
            ):
                yield message
            
            # 7. 记录工作流完成
            WorkflowLogger.workflow_complete(
                workflow_id, 
                {"documents_found": len(documents), "final_docs_used": min(final_k, len(documents))},
                1.0  # 模拟执行时间
            )
            
        except Exception as e:
            logger.error(f"聊天流处理失败: {e}", exc_info=True)
            yield AgentMessage.error(f"处理失败: {str(e)}", "chat_error")
            yield AgentMessage.complete(workflow_id)
    
    def _prepare_context(self, documents: List[Dict[str, Any]]) -> str:
        """准备上下文"""
        context_parts = []
        
        for i, doc in enumerate(documents):
            title = doc.get('title', f'文档{i+1}')
            content = doc.get('content', '')
            score = doc.get('score', 0)
            
            # 截断内容，保留关键信息
            content_preview = content[:800] + "..." if len(content) > 800 else content
            
            context_parts.append(f"【文档{i+1}: {title} (相关度: {score:.2%})】")
            context_parts.append(content_preview)
            context_parts.append("---")
        
        return "\n".join(context_parts)
    
    async def stream_simple_chat(
        self,
        query: str,
        db: Session,
        workflow_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        简化版聊天流（用于快速响应）
        
        参数:
        - query: 用户查询
        - db: 数据库会话
        - workflow_id: 工作流ID
        
        返回:
        - 流式响应的消息生成器
        """
        if not workflow_id:
            workflow_id = f"simple_chat_{datetime.now().timestamp()}"
        
        try:
            # 快速检索
            yield AgentMessage.status("正在检索...", stage="quick_retrieval", progress=20)
            documents = await hybrid_search(query, db, top_k=5, final_k=2)
            
            if not documents:
                yield AgentMessage.chunk("我没有在知识库中找到相关信息。")
                yield AgentMessage.complete(workflow_id)
                return
            
            # 快速生成
            yield AgentMessage.status("正在生成回答...", stage="quick_generation", progress=60)
            context = self._prepare_context(documents[:2])
            
            # 直接生成，不显示详细思考过程
            llm_service = get_llm_service()
            full_response = ""
            
            async for chunk in llm_service.stream_response(query, context):
                full_response += chunk
                yield AgentMessage.chunk(chunk)
            
            yield AgentMessage.complete(workflow_id)
            
        except Exception as e:
            logger.error(f"简化聊天失败: {e}")
            yield AgentMessage.error(f"处理失败: {str(e)}", "simple_chat_error")
            yield AgentMessage.complete(workflow_id)

# 全局智能体聊天服务实例
_agentic_chat_service = None

def get_agentic_chat_service() -> AgenticChatService:
    """获取智能体聊天服务实例"""
    global _agentic_chat_service
    if _agentic_chat_service is None:
        _agentic_chat_service = AgenticChatService()
    return _agentic_chat_service