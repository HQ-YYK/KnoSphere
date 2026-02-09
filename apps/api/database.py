from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.pool import StaticPool
import os
from dotenv import load_dotenv

load_dotenv()
sqlite_url = os.getenv("DATABASE_URL")

# 创建带连接的引擎，使用StaticPool避免并发问题
engine = create_engine(
    sqlite_url,
    connect_args={"check_same_thread": False} if sqlite_url and "sqlite" in sqlite_url else {},
    poolclass=StaticPool  # 使用静态连接池
)

def init_db():
    """初始化数据库"""
    SQLModel.metadata.create_all(engine)

# 修改：去掉 @contextmanager，直接使用生成器函数
def get_db():
    """用于依赖注入的数据库会话（生成器函数）"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# 如果需要，添加一个同步获取session的函数（不是生成器）
def get_sync_session():
    """同步获取数据库会话（用于非FastAPI环境）"""
    return Session(engine)