"""
流式响应协议定义

消息格式：
{
  "type": "status|thinking|chunk|complete|error",
  "data": {
    "content": "消息内容",
    "node": "节点名称",
    "stage": "阶段描述",
    "progress": 0.5,
    "metadata": {}
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
"""

import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel

class MessageType(str, Enum):
    """消息类型枚举"""
    STATUS = "status"        # 状态更新
    THINKING = "thinking"    # 思考过程
    CHUNK = "chunk"         # 回答片段
    COMPLETE = "complete"   # 完成
    ERROR = "error"         # 错误
    TOOL_CALL = "tool_call" # 工具调用
    TOOL_RESULT = "tool_result" # 工具结果

class StreamMessage(BaseModel):
    """流式消息模型"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: str = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.dict(), ensure_ascii=False)
    
    @classmethod
    def create_status(cls, content: str, node: str = None, progress: float = None):
        """创建状态消息"""
        return cls(
            type=MessageType.STATUS,
            data={
                "content": content,
                "node": node,
                "progress": progress
            }
        )
    
    @classmethod
    def create_thinking(cls, content: str, stage: str = None, metadata: Dict = None):
        """创建思考消息"""
        return cls(
            type=MessageType.THINKING,
            data={
                "content": content,
                "stage": stage,
                "metadata": metadata or {}
            }
        )
    
    @classmethod
    def create_chunk(cls, content: str):
        """创建回答片段"""
        return cls(
            type=MessageType.CHUNK,
            data={"content": content}
        )
    
    @classmethod
    def create_tool_call(cls, tool_name: str, tool_input: Dict, tool_id: str = None):
        """创建工具调用消息"""
        return cls(
            type=MessageType.TOOL_CALL,
            data={
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_id": tool_id or f"tool_{datetime.now().timestamp()}"
            }
        )
    
    @classmethod
    def create_tool_result(cls, tool_id: str, result: Any, success: bool = True):
        """创建工具结果消息"""
        return cls(
            type=MessageType.TOOL_RESULT,
            data={
                "tool_id": tool_id,
                "result": result,
                "success": success
            }
        )
    
    @classmethod
    def create_complete(cls, message_id: str = None, metadata: Dict = None):
        """创建完成消息"""
        return cls(
            type=MessageType.COMPLETE,
            data={
                "message_id": message_id,
                "metadata": metadata or {}
            }
        )
    
    @classmethod
    def create_error(cls, error: str, details: Dict = None):
        """创建错误消息"""
        return cls(
            type=MessageType.ERROR,
            data={
                "error": error,
                "details": details or {}
            }
        )

def format_stream_message(message: StreamMessage) -> str:
    """格式化流式消息"""
    return f"data: {message.to_json()}\n\n"

async def send_stream_message(writer, message: StreamMessage):
    """发送流式消息"""
    try:
        data = format_stream_message(message)
        await writer.write(data.encode('utf-8'))
        await writer.drain()
    except Exception as e:
        print(f"发送消息失败: {e}")