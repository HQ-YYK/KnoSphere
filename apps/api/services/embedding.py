from langchain_openai import OpenAIEmbeddings
import os

# 初始化 Embedding 客户端
# 2026 年的 LangChain 已原生适配 Python 3.14 的并发特性
embeddings_model = OpenAIEmbeddings(
    model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
)

async def generate_vector(text: str):
    """将文本转化为 1536 维的向量"""
    # 这里会自动调用远程或本地模型进行计算
    vector = await embeddings_model.aembed_query(text)
    return vector