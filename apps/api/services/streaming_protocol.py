import json
from typing import Dict, Any, Literal
from enum import Enum

class MessageType(str, Enum):
    """消息类型枚举"""
    STATUS = "status"
    CHUNK = "chunk"
    ERROR = "error"
    THINKING_START = "thinking_start"
    THINKING_END = "thinking_end"
    RETRIEVAL_START = "retrieval_start"
    RETRIEVAL_END = "retrieval_end"
    GENERATION_START = "generation_start"
    GENERATION_END = "generation_end"
    COMPLETE = "complete"

class AgentMessage:
    """代理消息类"""
    
    @staticmethod
    def create(
        type: MessageType,
        data: Any = None,
        stage: str = None,
        progress: float = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        创建标准化消息
        
        参数:
        - type: 消息类型
        - data: 消息数据
        - stage: 当前阶段
        - progress: 进度 (0-100)
        - metadata: 元数据
        """
        message = {
            "type": type.value,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        
        if stage:
            message["stage"] = stage
        
        if progress is not None:
            message["progress"] = progress
        
        if metadata:
            message["metadata"] = metadata
        
        return json.dumps(message) + "\n"
    
    @staticmethod
    def status(message: str, stage: str = None, progress: float = None) -> str:
        """创建状态消息"""
        return AgentMessage.create(
            type=MessageType.STATUS,
            data=message,
            stage=stage,
            progress=progress
        )
    
    @staticmethod
    def thinking_start(query: str, workflow_id: str = None) -> str:
        """开始思考"""
        return AgentMessage.create(
            type=MessageType.THINKING_START,
            data=f"开始分析: {query}",
            stage="thinking",
            progress=0,
            metadata={"query": query[:100], "workflow_id": workflow_id}
        )
    
    @staticmethod
    def retrieval_start(top_k: int = 10, strategy: str = "balanced") -> str:
        """开始检索"""
        return AgentMessage.create(
            type=MessageType.RETRIEVAL_START,
            data=f"正在检索相关知识 (策略: {strategy})",
            stage="retrieval",
            progress=10,
            metadata={"top_k": top_k, "strategy": strategy}
        )
    
    @staticmethod
    def retrieval_end(documents_found: int, strategy: str = "balanced") -> str:
        """检索结束"""
        return AgentMessage.create(
            type=MessageType.RETRIEVAL_END,
            data=f"检索完成，找到 {documents_found} 篇相关文档",
            stage="retrieval",
            progress=40,
            metadata={"documents_found": documents_found, "strategy": strategy}
        )
    
    @staticmethod
    def reranking_start() -> str:
        """开始重排序"""
        return AgentMessage.create(
            type=MessageType.STATUS,
            data="正在进行深度语义重排序",
            stage="reranking",
            progress=50
        )
    
    @staticmethod
    def reranking_end(top_docs: int) -> str:
        """重排序结束"""
        return AgentMessage.create(
            type=MessageType.STATUS,
            data=f"重排序完成，选择最相关的 {top_docs} 篇",
            stage="reranking",
            progress=70
        )
    
    @staticmethod
    def generation_start() -> str:
        """开始生成"""
        return AgentMessage.create(
            type=MessageType.GENERATION_START,
            data="正在生成回答",
            stage="generation",
            progress=80
        )
    
    @staticmethod
    def generation_end() -> str:
        """生成结束"""
        return AgentMessage.create(
            type=MessageType.GENERATION_END,
            data="回答生成完成",
            stage="generation",
            progress=95
        )
    
    @staticmethod
    def chunk(content: str) -> str:
        """内容块"""
        return AgentMessage.create(
            type=MessageType.CHUNK,
            data=content
        )
    
    @staticmethod
    def complete(workflow_id: str = None) -> str:
        """完成"""
        return AgentMessage.create(
            type=MessageType.COMPLETE,
            data="处理完成",
            stage="complete",
            progress=100,
            metadata={"workflow_id": workflow_id}
        )
    
    @staticmethod
    def error(error_message: str, error_type: str = None) -> str:
        """错误"""
        return AgentMessage.create(
            type=MessageType.ERROR,
            data=error_message,
            stage="error",
            metadata={"error_type": error_type}
        )

# 导入 datetime
from datetime import datetime