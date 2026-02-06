# services/embedding.py
import os
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

def get_embedding_engine():
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    
    if provider == "alibaba":
        # 阿里百炼 gte-v2 (1536维) 或 gte-large (1024维)
        return DashScopeEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "gte-v2"),
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )
    elif provider == "deepseek":
        # DeepSeek 的 Embedding 模型（如果有的话）或使用其 OpenAI 兼容接口
        # 注意：DeepSeek 目前主要提供 Chat 模型，Embedding 模型可能需要查看其最新文档
        # 这里假设其 Embedding 模型调用方式与 OpenAI 相同
        return OpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="https://api.deepseek.com/v1"
        )
    else:
        # 默认使用 OpenAI
        return OpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        )

# 初始化 Embedding 客户端
embeddings_model = get_embedding_engine()

async def generate_vector(text: str):
    """将文本转化为向量"""
    vector = await embeddings_model.aembed_query(text)
    return vector