from sqlmodel import create_engine, SQLModel, Session
import os
from dotenv import load_dotenv

load_dotenv()
sqlite_url = os.getenv("DATABASE_URL")
engine = create_engine(sqlite_url)

def init_db():
    # 自动创建所有定义的表格
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session