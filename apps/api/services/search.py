import os
from typing import List, Optional
import uuid
from sqlmodel import Session, select, text
from models import Document
from services.embedding import generate_vector
from services.rerank import alibaba_rerank

async def secure_hybrid_search(
    query: str, 
    db: Session, 
    user_id: str,
    top_k: int = 15, 
    final_k: int = 3,
    include_public: bool = True,
    similarity_threshold: float = 0.6
):
    """
    安全混合搜索：向量搜索（粗排） + Rerank（精排）
    自动应用用户权限过滤
    
    参数：
    - query: 用户查询字符串
    - db: 数据库会话（已设置 RLS 上下文）
    - user_id: 当前用户ID
    - top_k: 粗排阶段返回的文档数量
    - final_k: 精排后最终返回的文档数量
    - include_public: 是否包含公开文档
    - similarity_threshold: 相似度阈值
    """
    
    # 1. 生成问题的向量 (Embedding)
    query_vector = await generate_vector(query)
    
    # 2. 执行安全向量搜索
    # 使用我们创建的 secure_vector_search 函数
    raw_sql = """
    SELECT * FROM secure_vector_search(
        :query_vector, 
        :user_id, 
        :similarity_threshold,
        :limit
    )
    """
    
    result = db.execute(
        text(raw_sql),
        {
            "query_vector": query_vector,
            "user_id": user_id,
            "similarity_threshold": similarity_threshold,
            "limit": top_k
        }
    )
    
    initial_results = []
    for row in result:
        row_dict = dict(row._mapping)
        
        # 获取完整文档信息
        doc = db.get(Document, row_dict['id'])
        if doc:
            initial_results.append({
                "document": doc,
                "similarity": row_dict['similarity'],
                "is_public": row_dict['is_public']
            })
    
    if not initial_results:
        return []

    # 3. 准备重排序数据
    doc_contents = [item["document"].content for item in initial_results]
    
    # 4. 调用 Rerank 服务 (精排)
    try:
        reranked_results = alibaba_rerank(query, doc_contents)
    except Exception as e:
        print(f"Rerank 服务暂时不可用，使用向量搜索结果: {e}")
        # 如果 Rerank 服务不可用，使用向量搜索的相似度分数
        reranked_results = [
            {"index": i, "relevance_score": item["similarity"]}
            for i, item in enumerate(initial_results)
        ]
        # 按相似度降序排序
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
                    "similarity": initial_results[result["index"]]["similarity"],
                    "is_public": initial_results[result["index"]]["is_public"],
                    "user_id": original_doc.user_id,
                    "created_at": original_doc.created_at.isoformat() if original_doc.created_at else None
                })

    return final_docs

async def user_document_search(
    query: str,
    db: Session,
    user_id: str,
    tags: Optional[List[str]] = None,
    is_public: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    用户文档搜索 - 支持标签和可见性过滤
    """
    # 构建基础查询
    conditions = [
        f"d.user_id = {user_id}",
        f"d.is_public = true"
    ]
    
    # 添加标签过滤
    if tags:
        tag_conditions = " OR ".join([f"'{tag}' = ANY(d.tags)" for tag in tags])
        conditions.append(f"({tag_conditions})")
    
    # 添加可见性过滤
    if is_public is not None:
        conditions.append(f"d.is_public = {str(is_public).lower()}")
    
    # 构建 WHERE 子句
    where_clause = " OR ".join(conditions) if len(conditions) > 1 else conditions[0]
    
    # 执行搜索
    search_sql = f"""
    SELECT d.*,
           ts_rank(to_tsvector('zhparser', d.content), 
                   plainto_tsquery('zhparser', :query)) as rank
    FROM document d
    WHERE ({where_clause})
      AND to_tsvector('zhparser', d.content) @@ 
          plainto_tsquery('zhparser', :query)
    ORDER BY rank DESC
    LIMIT :limit OFFSET :offset
    """
    
    result = db.execute(
        text(search_sql),
        {
            "query": query,
            "limit": limit,
            "offset": offset
        }
    )
    
    documents = []
    for row in result:
        row_dict = dict(row._mapping)
        doc = Document(**{k: v for k, v in row_dict.items() if k != 'rank'})
        documents.append({
            "document": doc,
            "rank": row_dict['rank']
        })
    
    return documents

# 兼容旧接口
async def hybrid_search(query: str, db: Session, **kwargs):
    """
    兼容旧接口的安全搜索
    
    注意：这个接口需要从请求上下文中获取用户ID
    """
    user_id = getattr(db, '_rls_context', {}).get('user_id', str(uuid.uuid4()))
    return await secure_hybrid_search(query, db, user_id, **kwargs)