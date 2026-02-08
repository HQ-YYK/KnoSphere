from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.pool import StaticPool
import os
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()
sqlite_url = os.getenv("DATABASE_URL")

# 创建带连接的引擎，使用StaticPool避免并发问题
engine = create_engine(
    sqlite_url,
    connect_args = {"check_same_thread": False} if sqlite_url and "sqlite" in sqlite_url else {},
    poolclass=StaticPool  # 使用静态连接池
)

def init_db():
    """初始化数据库"""
    SQLModel.metadata.create_all(engine)

@contextmanager
def get_session():
    """获取数据库会话"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# 直接获取session的函数（用于依赖注入）
def get_db():
    """用于依赖注入的数据库会话"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()