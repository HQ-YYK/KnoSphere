import json
import os
from pgvector.sqlalchemy import Vector
from sqlmodel import Field, SQLModel, Relationship, Column
from typing import Any, Dict, List, Optional, Text
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

"""
这里的维度必须根据你当前选择的 EMBEDDING_MODEL 来定
如果你改了维度，必须删除数据库表重新创建，或者执行 ALTER TABLE 迁移
默认为1536（OpenAI标准）
"""
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "1536"))

# 1. 用户模型
class User(SQLModel, table=True):
    """用户模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    email: str = Field(unique=True, max_length=100)
    password_hash: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    
    # 权限配置 (JSONB 格式)
    permissions: Optional[Dict[str, Any]] = Field(
        default={"documents": ["read", "write"]},
        sa_column=Column(Text, default='{"documents": ["read", "write"]}')
    )
    
    # 建立与文档的关联
    documents: List["Document"] = Relationship(back_populates="owner")
    
    def has_permission(self, resource: str, action: str) -> bool:
        """检查用户权限"""
        if not self.permissions:
            return False
        
        # 管理员拥有所有权限
        if self.permissions.get("admin") is True:
            return True
        
        # 检查特定资源权限
        resource_perms = self.permissions.get(resource, [])
        return action in resource_perms
    
    def to_dict(self) -> dict:
        """转换为字典（排除敏感信息）"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "permissions": self.permissions
        }

# 2. 文档模型（知识库的核心）
class Document(SQLModel, table=True):
    """文档模型（知识库的核心）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, max_length=200)
    content: str  # 原始内容
    
    # 2026 年标配：向量字段
    # 1536 是常用的向量维度（例如 OpenAI 的 text-embedding-3-small）
    embedding: Optional[List[float]] = Field(
        sa_column=Column(Vector(1536))
    )
    
    # 权限控制字段
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    is_public: bool = Field(default=False)
    tags: Optional[List[str]] = Field(
        default=[],
        sa_column=Column(Text, default='[]')
    )
    
    # 细粒度访问控制
    access_control: Optional[Dict[str, List[int]]] = Field(
        default={"read": [], "write": [], "delete": []},
        sa_column=Column(Text, default='{"read": [], "write": [], "delete": []}')
    )
    
    owner: Optional[User] = Relationship(back_populates="documents")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def can_access(self, user_id: int, action: str = "read") -> bool:
        """检查用户是否有权限访问"""
        # 文档所有者拥有所有权限
        if self.user_id == user_id:
            return True
        
        # 公开文档可读
        if action == "read" and self.is_public:
            return True
        
        # 检查访问控制列表
        allowed_users = self.access_control.get(action, [])
        return user_id in allowed_users
    
    def add_access(self, user_id: int, actions: List[str]):
        """添加用户访问权限"""
        for action in actions:
            if action in self.access_control:
                if user_id not in self.access_control[action]:
                    self.access_control[action].append(user_id)
    
    def remove_access(self, user_id: int, actions: List[str]):
        """移除用户访问权限"""
        for action in actions:
            if action in self.access_control:
                if user_id in self.access_control[action]:
                    self.access_control[action].remove(user_id)


# 可选：如果未来需要存储多种向量，可以这样设计
# class DocumentVector(SQLModel, table=True):
#     """多向量存储表（高级功能）"""
#     id: Optional[int] = Field(default=None, primary_key=True)
#     document_id: int = Field(foreign_key="document.id")
#     provider: str = Field(index=True)  # openai, alibaba, deepseek等
#     model: str = Field(index=True)     # 模型名称
#     dimension: int = Field()           # 向量维度
#     embedding: list[float] = Field(
#         sa_column=Column(Vector(VECTOR_DIM))
#     )
#     created_at: datetime = Field(default_factory=datetime.now)


# 辅助函数用于 JSON 序列化
def serialize_permissions(permissions: Dict[str, Any]) -> str:
    """序列化权限字典"""
    return json.dumps(permissions)

def deserialize_permissions(permissions_str: str) -> Dict[str, Any]:
    """反序列化权限字符串"""
    if not permissions_str:
        return {"documents": ["read", "write"]}
    return json.loads(permissions_str)