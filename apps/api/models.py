import os
from pgvector.sqlalchemy import Vector
from sqlmodel import Field, SQLModel, Relationship, Column
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from sqlalchemy import Text as SQLText
from sqlalchemy.dialects.postgresql import JSONB as SQLJSONB, ARRAY, UUID
from sqlalchemy import Float as SQLFloat
import uuid

from dotenv import load_dotenv

load_dotenv()


# ==================== 知识图谱模型 ====================

class EntityDocumentLink(SQLModel, table=True):
    """实体与文档的关联表"""
    __tablename__ = "entity_document_links"
    
    # 移除单独的 id 字段，使用复合主键
    entity_id: int = Field(foreign_key="entities.id", primary_key=True)
    document_id: uuid.UUID = Field(foreign_key="documents.id", primary_key=True)
    
    # 在文档中出现的信息
    occurrences: Optional[List[str]] = Field(
        sa_column=Column(SQLJSONB, nullable=True), 
        default=[]
    )
    frequency_in_doc: int = Field(default=1)
    significance: float = Field(default=0.0)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Entity(SQLModel, table=True):
    """知识图谱实体"""
    __tablename__ = "entities"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    normalized_name: str = Field(index=True)
    entity_type: str = Field(index=True)
    description: Optional[str] = None
    
    entity_metadata: Optional[Dict[str, Any]] = Field(
        sa_column=Column(SQLJSONB, nullable=True), 
        default={}
    )
    
    embedding: Optional[List[float]] = Field(
        sa_column=Column(ARRAY(SQLFloat)), 
        default=None
    )
    
    frequency: int = Field(default=1)
    confidence: float = Field(default=0.0)
    
    user_id: Optional[uuid.UUID] = Field(foreign_key="users.id", default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    outgoing_edges: List["GraphEdge"] = Relationship(
        back_populates="source_entity",
        sa_relationship_kwargs={
            "foreign_keys": "[GraphEdge.source_id]",
            "cascade": "all, delete-orphan"
        }
    )
    
    incoming_edges: List["GraphEdge"] = Relationship(
        back_populates="target_entity",
        sa_relationship_kwargs={
            "foreign_keys": "[GraphEdge.target_id]",
            "cascade": "all, delete-orphan"
        }
    )
    
    documents: List["Document"] = Relationship(
        back_populates="entities",
        link_model=EntityDocumentLink
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.entity_type,
            "description": self.description,
            "entity_metadata": self.entity_metadata,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "user_id": str(self.user_id) if self.user_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class GraphEdge(SQLModel, table=True):
    """知识图谱关系边"""
    __tablename__ = "graph_edges"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="entities.id", index=True)
    target_id: int = Field(foreign_key="entities.id", index=True)
    relation_type: str = Field(index=True)
    description: Optional[str] = None
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # 关系来源
    source_document_id: Optional[uuid.UUID] = Field(foreign_key="documents.id", default=None)
    source_context: Optional[str] = None
    
    edge_metadata: Optional[Dict[str, Any]] = Field(
        sa_column=Column(SQLJSONB, nullable=True), 
        default={}
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    user_id: Optional[uuid.UUID] = Field(foreign_key="users.id", default=None)
    
    source_entity: Entity = Relationship(
        back_populates="outgoing_edges",
        sa_relationship_kwargs={
            "foreign_keys": "[GraphEdge.source_id]"
        }
    )
    
    target_entity: Entity = Relationship(
        back_populates="incoming_edges",
        sa_relationship_kwargs={
            "foreign_keys": "[GraphEdge.target_id]"
        }
    )
    
    source_document: Optional["Document"] = Relationship(back_populates="edges")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation_type,
            "description": self.description,
            "weight": self.weight,
            "confidence": self.confidence,
            "source_document_id": str(self.source_document_id) if self.source_document_id else None,
            "source_context": self.source_context,
            "user_id": str(self.user_id) if self.user_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


# ==================== 基本模型 ====================
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "1536"))


# 1. 用户模型
class User(SQLModel, table=True):
    """用户模型"""
    __tablename__ = "users"
    
    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        primary_key=True
    )
    username: str = Field(index=True, unique=True, max_length=50)
    email: str = Field(unique=True, max_length=100)
    password_hash: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    
    permissions: Optional[Dict[str, Any]] = Field(
        default={"documents": ["read", "write"]},
        sa_column=Column(SQLJSONB, default=lambda: {"documents": ["read", "write"]})
    )
    
    documents: List["Document"] = Relationship(back_populates="owner")
    
    def has_permission(self, resource: str, action: str) -> bool:
        if not self.permissions:
            return False
        
        if self.permissions.get("admin") is True:
            return True
        
        resource_perms = self.permissions.get(resource, [])
        return action in resource_perms
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id else None,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "permissions": self.permissions
        }


# 2. 文档模型 - 适配现有数据库结构
class Document(SQLModel, table=True):
    """文档模型（知识库的核心）"""
    __tablename__ = "documents"
    
    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        primary_key=True
    )
    title: str = Field(index=True, max_length=200)
    content: str
    
    # 检查是否已有 embedding 字段
    embedding: Optional[List[float]] = Field(
        sa_column=Column(Vector(VECTOR_DIM), nullable=True)
    )
    
    # 注意：这里使用 metadata 字段，但之前有警告说与 SQLModel 冲突
    # 我们将其重命名为 doc_metadata
    doc_metadata: Optional[Dict[str, Any]] = Field(
        sa_column=Column(SQLJSONB, nullable=True),
        default={}
    )
    
    # 检查是否已有 user_id 字段
    user_id: Optional[uuid.UUID] = Field(foreign_key="users.id", default=None)
    is_public: bool = Field(default=False)
    tags: Optional[List[str]] = Field(
        default=[],
        sa_column=Column(SQLJSONB, default=lambda: [])
    )
    
    # 检查是否已有 access_control 字段
    access_control: Optional[Dict[str, List[str]]] = Field(
        default={"read": [], "write": [], "delete": []},
        sa_column=Column(SQLJSONB, default=lambda: {"read": [], "write": [], "delete": []})
    )

    # 检查是否已有 created_at 和 updated_at 字段
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 新字段 - 可能需要迁移
    graph_extracted: bool = Field(default=False)
    graph_extraction_time: Optional[datetime] = None
    
    entities: List[Entity] = Relationship(
        back_populates="documents",
        link_model=EntityDocumentLink
    )
    
    edges: List[GraphEdge] = Relationship(back_populates="source_document")
    
    owner: Optional[User] = Relationship(back_populates="documents")
    
    def can_access(self, user_id: uuid.UUID, action: str = "read") -> bool:
        if self.user_id == user_id:
            return True
        
        if action == "read" and self.is_public:
            return True
        
        # 将 UUID 转换为字符串进行比较
        user_id_str = str(user_id) if user_id else None
        allowed_users = self.access_control.get(action, [])
        return user_id_str in allowed_users
    
    def add_access(self, user_id: uuid.UUID, actions: List[str]):
        user_id_str = str(user_id) if user_id else None
        for action in actions:
            if action in self.access_control:
                if user_id_str not in self.access_control[action]:
                    self.access_control[action].append(user_id_str)
    
    def remove_access(self, user_id: uuid.UUID, actions: List[str]):
        user_id_str = str(user_id) if user_id else None
        for action in actions:
            if action in self.access_control:
                if user_id_str in self.access_control[action]:
                    self.access_control[action].remove(user_id_str)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": str(self.id) if self.id else None,
            "title": self.title,
            "content": self.content,
            "doc_metadata": self.doc_metadata,
            "user_id": str(self.user_id) if self.user_id else None,
            "is_public": self.is_public,
            "tags": self.tags,
            "access_control": self.access_control,
            "graph_extracted": self.graph_extracted,
            "graph_extraction_time": self.graph_extraction_time.isoformat() if self.graph_extraction_time else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

# 辅助函数
def serialize_permissions(permissions: Dict[str, Any]) -> str:
    return json.dumps(permissions)


def deserialize_permissions(permissions_str: str) -> Dict[str, Any]:
    if not permissions_str:
        return {"documents": ["read", "write"]}
    return json.loads(permissions_str)