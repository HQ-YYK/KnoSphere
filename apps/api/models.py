import os
from pgvector.sqlalchemy import Vector
from sqlmodel import Field, SQLModel, Relationship, Column
from typing import List, Optional
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
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 建立与文档的关联：一个用户可以拥有多份文档
    documents: List["Document"] = Relationship(back_populates="owner")

# 2. 文档模型（知识库的核心）
class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str  # 原始内容
    
    # 2026 年标配：向量字段
    # 1536 是常用的向量维度（例如 OpenAI 的 text-embedding-3-small）
    embedding: Optional[list[float]] = Field(
        sa_column=Column(Vector(VECTOR_DIM))
    )
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    owner: Optional[User] = Relationship(back_populates="documents")
    
    created_at: datetime = Field(default_factory=datetime.now)


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