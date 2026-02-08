import os
from typing import List
from core.logger import logger
from dotenv import load_dotenv

load_dotenv()

def get_embedding_engine():
    """获取嵌入模型引擎"""
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    
    if provider == "alibaba":
        try:
            from langchain_community.embeddings import DashScopeEmbeddings
            api_key = os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                logger.warning("DASHSCOPE_API_KEY 未设置，使用默认值")
                api_key = "your-dashscope-api-key-here"
            
            return DashScopeEmbeddings(
                model=os.getenv("EMBEDDING_MODEL", "gte-v2"),
                dashscope_api_key=api_key
            )
        except ImportError:
            logger.error("需要安装 dashscope: pip install dashscope")
            raise
        except Exception as e:
            logger.error(f"初始化阿里云嵌入模型失败: {e}")
            raise
    elif provider == "deepseek":
        try:
            from langchain_openai import OpenAIEmbeddings
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                logger.warning("DEEPSEEK_API_KEY 未设置，使用默认值")
                api_key = "your-deepseek-api-key-here"
            
            return OpenAIEmbeddings(
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                openai_api_key=api_key,
                openai_api_base="https://api.deepseek.com/v1"
            )
        except Exception as e:
            logger.error(f"初始化 DeepSeek 嵌入模型失败: {e}")
            raise
    elif provider == "azure":
        try:
            from langchain_openai import AzureOpenAIEmbeddings
            return AzureOpenAIEmbeddings(
                azure_deployment=os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"),
                openai_api_version=os.getenv("AZURE_API_VERSION", "2023-05-15"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT", ""),
                api_key=os.getenv("AZURE_API_KEY", "")
            )
        except Exception as e:
            logger.error(f"初始化 Azure OpenAI 嵌入模型失败: {e}")
            raise
    else:
        # 默认使用 OpenAI
        try:
            from langchain_openai import OpenAIEmbeddings
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY 未设置，使用默认值")
                api_key = "your-openai-api-key-here"
            
            return OpenAIEmbeddings(
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                openai_api_key=api_key
            )
        except Exception as e:
            logger.error(f"初始化 OpenAI 嵌入模型失败: {e}")
            raise

# 初始化 Embedding 客户端
embeddings_model = get_embedding_engine()

async def generate_vector(text: str) -> List[float]:
    """生成文本向量"""
    try:
        result = await embeddings_model.aembed_query(text)
        logger.debug(f"生成向量成功，文本长度: {len(text)}")
        return result
    except Exception as e:
        logger.error(f"生成向量失败: {e}")
        raise

async def generate_vectors(texts: List[str]) -> List[List[float]]:
    """批量生成文本向量"""
    try:
        results = await embeddings_model.aembed_documents(texts)
        logger.debug(f"批量生成向量成功，文本数量: {len(texts)}")
        return results
    except Exception as e:
        logger.error(f"批量生成向量失败: {e}")
        raise