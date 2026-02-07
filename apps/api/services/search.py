import os
from typing import List, Optional
from sqlmodel import Session, select
from models import Document
from services.embedding import generate_vector
from services.rerank import alibaba_rerank

async def get_embedding_engine():
    """获取嵌入引擎实例"""
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )

async def hybrid_search(query: str, db: Session, top_k: int = 15, final_k: int = 3):
    """
    混合搜索：向量搜索（粗排） + Rerank（精排）
    
    参数：
    - query: 用户查询字符串
    - db: 数据库会话
    - top_k: 粗排阶段返回的文档数量
    - final_k: 精排后最终返回的文档数量
    """
    # 1. 生成问题的向量 (Embedding)
    engine = await get_embedding_engine()
    query_vector = await engine.aembed_query(query)

    # 2. 执行向量搜索 (粗排) - 使用余弦相似度
    # 在 SQLModel 中，我们需要使用原始 SQL 来执行向量搜索
    # 因为 pgvector 的向量距离运算符需要通过 text() 包装
    
    # 方法1：使用原始 SQL（推荐）
    raw_sql = """
    SELECT id, title, content, created_at, 
           embedding <=> CAST(:query_vector AS vector) as distance
    FROM document
    WHERE embedding IS NOT NULL
    ORDER BY distance ASC
    LIMIT :limit
    """
    
    result = db.execute(
        text(raw_sql),
        {
            "query_vector": query_vector,
            "limit": top_k
        }
    )
    
    initial_results = []
    for row in result:
        # 将行转换为字典
        row_dict = dict(row._mapping)
        # 创建 Document 对象以便后续使用
        doc = Document(
            id=row_dict['id'],
            title=row_dict['title'],
            content=row_dict['content'],
            created_at=row_dict['created_at'],
            embedding=query_vector  # 注意：这里只是占位，实际存储的是原始向量
        )
        initial_results.append({
            "document": doc,
            "distance": row_dict['distance']
        })
    
    if not initial_results:
        return []

    # 3. 准备重排序数据
    doc_contents = [item["document"].content for item in initial_results]
    
    # 4. 调用 Rerank 服务 (精排)
    # 注意：这里我们先模拟返回结果，稍后实现真正的 Rerank
    try:
        # 尝试调用阿里百炼 Rerank
        reranked_results = alibaba_rerank(query, doc_contents)
    except Exception as e:
        print(f"Rerank 服务暂时不可用，使用向量搜索结果: {e}")
        # 如果 Rerank 服务不可用，使用向量搜索的距离分数
        reranked_results = [
            {"index": i, "relevance_score": 1.0 - item["distance"]}
            for i, item in enumerate(initial_results)
        ]
        # 按距离降序排序（距离越小，相关性越高）
        reranked_results.sort(key=lambda x: x["relevance_score"], reverse=True)

    # 5. 按照 Rerank 给出的分数重新组装文档
    final_docs = []
    if reranked_results:
        # 只取前 final_k 个结果
        for result in reranked_results[:final_k]:
            if result["index"] < len(initial_results):
                original_doc = initial_results[result["index"]]["document"]
                final_docs.append({
                    "id": original_doc.id,
                    "title": original_doc.title,
                    "content": original_doc.content,
                    "score": result.get("relevance_score", 0.0),
                    "created_at": original_doc.created_at.isoformat() if original_doc.created_at else None
                })

    return final_docs