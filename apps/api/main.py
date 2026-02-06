from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import init_db, engine
from sqlmodel import text
from models import User, Document  # 导入模型，确保表被创建

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    with engine.connect() as conn:
        # 激活向量扩展，这是 2026 年 RAG 系统的核心
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    init_db()  # 这会创建所有表，包括 User 和 Document
    yield
    # 关闭时执行（如果需要清理资源）

app = FastAPI(lifespan=lifespan)