import os
import json
from typing import List, Dict, Any
import httpx
from typing import Optional

class AlibabaRerankClient:
    """阿里百炼 Rerank 客户端"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://dashscope.aliyuncs.com"):
        self.api_key = api_key or os.getenv("ALIBABA_API_KEY", "")
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def rerank(self, query: str, documents: List[str], model: str = "gte-rerank-v2") -> List[Dict[str, Any]]:
        """执行重排序"""
        if not self.api_key:
            raise ValueError("阿里百炼 API Key 未设置")
        
        if not documents:
            return []
        
        # 准备请求数据
        request_data = {
            "model": model,
            "input": {
                "query": query,
                "documents": documents
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/rerank",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=request_data
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析返回结果
            if "output" in result and "results" in result["output"]:
                return result["output"]["results"]
            else:
                raise ValueError(f"返回结果格式错误: {result}")
                
        except httpx.HTTPError as e:
            print(f"HTTP 错误: {e}")
            raise
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            raise
        finally:
            await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

# 全局 Rerank 客户端实例
_rerank_client: Optional[AlibabaRerankClient] = None

async def get_rerank_client() -> AlibabaRerankClient:
    """获取 Rerank 客户端实例"""
    global _rerank_client
    if _rerank_client is None:
        _rerank_client = AlibabaRerankClient()
    return _rerank_client

async def alibaba_rerank(query: str, documents: List[str]) -> List[Dict[str, Any]]:
    """
    使用阿里百炼进行文档重排序
    
    参数：
    - query: 查询字符串
    - documents: 文档内容列表
    
    返回：
    - 重排序后的文档列表，每个文档包含 index 和 relevance_score
    """
    # 如果阿里百炼 API Key 未设置，返回模拟结果
    if not os.getenv("ALIBABA_API_KEY"):
        print("⚠️  阿里百炼 API Key 未设置，使用模拟重排序")
        return [
            {"index": i, "relevance_score": 1.0 - (i * 0.1)}
            for i in range(len(documents))
        ]
    
    try:
        client = await get_rerank_client()
        results = await client.rerank(query, documents)
        return results
    except Exception as e:
        print(f"阿里百炼 Rerank 调用失败: {e}")
        # 降级到模拟结果
        return [
            {"index": i, "relevance_score": 1.0 - (i * 0.1)}
            for i in range(len(documents))
        ]

# 本地 Rerank 实现（如果不想使用阿里百炼）
class LocalRerank:
    """本地 Rerank 实现（基于 TF-IDF 和 BM25）"""
    
    def __init__(self):
        try:
            from rank_bm25 import BM25Okapi
            import jieba
            self.BM25Okapi = BM25Okapi
            self.jieba = jieba
            self._has_dependencies = True
        except ImportError:
            print("⚠️  未安装 rank-bm25 和 jieba，本地 Rerank 不可用")
            print("    可以使用: uv add rank-bm25 jieba")
            self._has_dependencies = False
    
    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        return list(self.jieba.cut(text))
    
    async def rerank(self, query: str, documents: List[str]) -> List[Dict[str, Any]]:
        """基于 BM25 的本地重排序"""
        if not self._has_dependencies or not documents:
            return [
                {"index": i, "relevance_score": 1.0}
                for i in range(len(documents))
            ]
        
        # 分词
        tokenized_docs = [self._tokenize(doc) for doc in documents]
        tokenized_query = self._tokenize(query)
        
        # 创建 BM25 模型
        bm25 = self.BM25Okapi(tokenized_docs)
        
        # 计算相关性分数
        scores = bm25.get_scores(tokenized_query)
        
        # 标准化分数到 0-1 范围
        if len(scores) > 0:
            max_score = max(scores)
            if max_score > 0:
                scores = scores / max_score
        
        # 返回结果
        results = []
        for i, score in enumerate(scores):
            results.append({
                "index": i,
                "relevance_score": float(score)
            })
        
        # 按分数降序排序
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results

async def local_rerank(query: str, documents: List[str]) -> List[Dict[str, Any]]:
    """使用本地 Rerank"""
    local_reranker = LocalRerank()
    return await local_reranker.rerank(query, documents)