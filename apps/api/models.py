from pgvector.sqlalchemy import Vector
from sqlmodel import Field, SQLModel, Relationship, Column
from typing import List, Optional
from datetime import datetime

# 1. 用户模型
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 建立与文档的关联：一个用户可以拥有多份文档
    documents: List["Document"] = Relationship(back_populates="owner")

# 2. 文档模型（知识库的核心）
class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str  # 原始内容
    
    # 2026 年标配：向量字段
    # 1536 是常用的向量维度（例如 OpenAI 的 text-embedding-3-small）
    embedding: Optional[List[float]] = Field(
        sa_column=Column(Vector(1536))
    )
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    owner: Optional[User] = Relationship(back_populates="documents")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)