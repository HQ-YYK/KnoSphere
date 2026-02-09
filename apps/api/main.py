from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from sqlmodel import Session, select
from typing import List, Optional
import os
import uuid
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from core.auth import ACCESS_TOKEN_EXPIRE_MINUTES, LoginRequest, Token, UserCreate, PasswordChange, get_current_active_user
from core.database_middleware import get_secure_db

# 导入 Celery 任务
from tasks.document_tasks import process_large_document, batch_process_documents
from tasks.celery_app import celery_app


from core.logger import logger, log_api_response
from database import get_db, init_db, engine
from models import Document, User

from services.agentic_chat import get_agentic_chat_service
from services.tools import get_tool_manager

# 创建上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动 KnoSphere API...")
    
    # 初始化数据库
    with engine.connect() as conn:
        from sqlmodel import text
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    init_db()
    
    logger.info("✅ 数据库初始化完成")
    
    yield
    
    logger.info("👋 关闭 KnoSphere API...")

app = FastAPI(
    title="KnoSphere API",
    description="2026 企业级智能知识库系统 - 分布式异步处理",
    version="2.1.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from core.database_middleware import DatabaseSessionMiddleware
app.add_middleware(DatabaseSessionMiddleware)

# ==================== 认证路由 ====================
@app.post("/auth/register", response_model=dict)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册"""
    from core.auth import AuthService
    
    auth_service = AuthService()
    
    # 检查用户名是否已存在
    existing_user = db.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    existing_email = db.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="邮箱已存在"
        )
    
    # 创建用户
    hashed_password = auth_service.get_password_hash(user_data.password)
    
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        is_active=True,
        permissions={"documents": ["read", "write"]}
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "message": "注册成功"
    }

@app.post("/auth/login")
async def login(
    login_data: LoginRequest,  # 使用 LoginRequest 而不是 OAuth2PasswordRequestForm
    db: Session = Depends(get_db)
):
    """用户登录"""
    try:
        from core.auth import AuthService
        # 认证用户
        user = await AuthService.authenticate_user(login_data, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={"sub": str(user.id), "username": user.username},  # 确保 user.id 转换为字符串
            expires_delta=access_token_expires
        )
        
        # 返回令牌 - 确保 user.id 转换为字符串
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=str(user.id),  # 这里必须转换为字符串
            username=user.username,
            permissions=user.permissions or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@app.get("/auth/me", response_model=dict)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户信息"""
    return current_user.to_dict()

@app.post("/auth/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    from core.auth import AuthService
    
    auth_service = AuthService()
    
    # 验证当前密码
    if not auth_service.verify_password(
        password_data.current_password, 
        current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )
    
    # 更新密码
    current_user.password_hash = auth_service.get_password_hash(
        password_data.new_password
    )
    db.add(current_user)
    db.commit()
    
    return {"message": "密码修改成功"}


# ==================== 异步上传接口 ====================

@app.post("/upload/async")
async def upload_large_document_async(
    file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    异步上传大文档
    
    立即返回任务ID，文档在后台处理
    """
    start_time = datetime.now(timezone.utc)
    
    # 验证文件类型
    allowed_extensions = {'.txt', '.md', '.pdf', '.docx'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式。支持格式: {', '.join(allowed_extensions)}"
        )
    
    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    temp_filename = f"{file_id}{file_ext}"
    temp_filepath = UPLOAD_DIR / temp_filename
    
    try:
        # 保存文件到临时目录
        content = await file.read()
        with open(temp_filepath, "wb") as f:
            f.write(content)
        
        file_size = len(content) / (1024 * 1024)  # MB
        logger.info(f"📥 文件已保存: {temp_filepath} ({file_size:.2f}MB)")
        
        # 创建文档记录（初始状态）
        document = Document(
            title=file.filename,
            content=f"文件正在处理中... ({file_size:.2f}MB)",
            user_id=user_id
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # 触发异步处理任务
        task = process_large_document.delay(
            str(temp_filepath),
            document.id,
            user_id
        )
        
        response_time = time.time() - start_time
        
        log_api_response("/upload/async", 200, response_time)
        
        return {
            "message": "大文件已进入后台处理流水线",
            "task_id": task.id,
            "document_id": document.id,
            "filename": file.filename,
            "file_size_mb": round(file_size, 2),
            "estimated_time": "处理时间取决于文件大小和内容复杂度",
            "status_url": f"/task/status/{task.id}",
            "document_url": f"/documents/{document.id}"
        }
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}", exc_info=True)
        # 清理临时文件
        if temp_filepath.exists():
            temp_filepath.unlink()
        
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

@app.post("/upload/batch")
async def upload_batch_documents(
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    批量上传文档
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="一次最多上传10个文件")
    
    file_paths = []
    document_ids = []
    
    try:
        for file in files:
            # 验证文件类型
            allowed_extensions = {'.txt', '.md', '.pdf', '.docx'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400, 
                    detail=f"文件 {file.filename} 格式不支持"
                )
            
            # 保存文件
            file_id = str(uuid.uuid4())
            temp_filename = f"{file_id}{file_ext}"
            temp_filepath = UPLOAD_DIR / temp_filename
            
            content = await file.read()
            with open(temp_filepath, "wb") as f:
                f.write(content)
            
            file_paths.append(str(temp_filepath))
            
            # 创建文档记录
            document = Document(
                title=file.filename,
                content=f"文件正在处理中...",
                user_id=user_id
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            document_ids.append(document.id)
        
        # 触发批量处理任务
        task = batch_process_documents.delay(file_paths, user_id)
        
        return {
            "message": f"批量处理任务已启动，共 {len(files)} 个文件",
            "task_id": task.id,
            "document_ids": document_ids,
            "status_url": f"/task/status/{task.id}"
        }
        
    except Exception as e:
        # 清理已保存的文件
        for file_path in file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")

@app.get("/task/status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    前端可以通过轮询此接口获取处理进度
    """
    try:
        task_result = celery_app.AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": task_result.state,
            "timestamp": datetime.now().isoformat()
        }
        
        # 如果任务正在进行中，添加进度信息
        if task_result.state == 'PROGRESS':
            if isinstance(task_result.info, dict):
                response["progress"] = task_result.info.get("progress", 0)
                response["stage"] = task_result.info.get("stage", "处理中")
                response["details"] = task_result.info.get("details", "")
                response["current"] = task_result.info.get("current", 0)
                response["total"] = task_result.info.get("total", 1)
            else:
                response["progress"] = 0
                response["stage"] = "处理中"
        
        # 如果任务已完成，添加结果信息
        elif task_result.state == 'SUCCESS':
            if isinstance(task_result.result, dict):
                response.update(task_result.result)
            else:
                response["result"] = task_result.result
        
        # 如果任务失败，添加错误信息
        elif task_result.state == 'FAILURE':
            response["error"] = str(task_result.info)
            if hasattr(task_result, "traceback"):
                response["traceback"] = task_result.traceback
        
        return response
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return {
            "task_id": task_id,
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/tasks/queue")
async def get_queue_status():
    """
    获取任务队列状态
    """
    try:
        # 获取 Celery 监控信息
        inspector = celery_app.control.inspect()
        
        # 获取活跃任务
        active = inspector.active() or {}
        # 获取预定任务
        scheduled = inspector.scheduled() or {}
        # 获取保留任务
        reserved = inspector.reserved() or {}
        
        # 统计队列长度
        queue_stats = {}
        for worker, tasks in active.items():
            queue_stats[worker] = {
                "active": len(tasks),
                "tasks": [t.get("name", "unknown") for t in tasks[:5]]  # 只显示前5个
            }
        
        # 获取 Redis 队列信息
        import redis
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        
        # 统计各个队列的长度
        queues = ["celery", "documents", "embeddings", "cleanup"]
        queue_lengths = {}
        for queue in queues:
            try:
                length = redis_client.llen(queue)
                queue_lengths[queue] = length
            except:
                queue_lengths[queue] = 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "queues": queue_lengths,
            "workers": queue_stats,
            "total_active": sum(len(tasks) for tasks in active.values()),
            "total_scheduled": sum(len(tasks) for tasks in scheduled.values()),
            "total_reserved": sum(len(tasks) for tasks in reserved.values())
        }
        
    except Exception as e:
        logger.error(f"获取队列状态失败: {e}")
        return {"error": str(e)}

# ==================== 文档管理接口 ====================

@app.get("/documents/processing")
async def get_processing_documents(
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """获取正在处理的文档列表"""
    documents = db.exec(
        select(Document).where(
            Document.content.contains("正在处理中")
        ).offset(offset).limit(limit)
    ).all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "status": "processing",
                "created_at": doc.created_at,
                "user_id": doc.user_id
            }
            for doc in documents
        ],
        "total": len(documents)
    }

@app.get("/documents/recent")
async def get_recent_documents(
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """获取最近处理完成的文档"""
    documents = db.exec(
        select(Document).where(
            ~Document.content.contains("正在处理中")
        ).order_by(Document.created_at.desc()).offset(offset).limit(limit)
    ).all()
    
    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "status": "completed",
                "created_at": doc.created_at,
                "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                "has_vector": doc.embedding is not None,
                "user_id": doc.user_id
            }
            for doc in documents
        ],
        "total": len(documents)
    }

@app.get("/documents/{document_id}")
async def get_document_detail(
    document_id: int,
    db: Session = Depends(get_secure_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取文档详情"""
    from sqlmodel import select
    
    # 获取文档
    document = db.get(Document, document_id)
    
    if not document or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")
    
    # 获取文档中的实体
    from models import EntityDocumentLink
    entity_links = db.exec(
        select(EntityDocumentLink).where(
            EntityDocumentLink.document_id == document_id
        )
    ).all()
    
    entities = []
    for link in entity_links:
        entity = db.get(Entity, link.entity_id)
        if entity:
            entities.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.entity_type,
                "frequency_in_doc": link.frequency_in_doc,
                "significance": link.significance
            })
    
    # 获取与文档相关的关系
    edges = db.exec(
        select(GraphEdge).where(
            GraphEdge.source_document_id == document_id,
            GraphEdge.user_id == current_user.id
        )
    ).all()
    
    # 构建文档统计
    stats = {
        "content_length": len(document.content) if document.content else 0,
        "entity_count": len(entities),
        "relation_count": len(edges),
        "embedding_status": "已向量化" if document.embedding else "未向量化",
        "graph_extracted": "已提取" if document.graph_extracted else "未提取",
        "graph_extraction_time": document.graph_extraction_time.isoformat() if document.graph_extraction_time else None
    }
    
    return {
        "document": {
            "id": document.id,
            "title": document.title,
            "content": document.content,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "user_id": document.user_id,
            "embedding": "已生成" if document.embedding else "未生成",
            "graph_extracted": document.graph_extracted
        },
        "entities": entities,
        "relations": [edge.to_dict() for edge in edges],
        "stats": stats,
        "preview_contexts": _extract_entity_contexts(document.content, entities[:5])  # 提取实体出现的上下文
    }

def _extract_entity_contexts(content: str, entities: list, context_size: int = 200) -> list:
    """提取实体在文档中出现的上下文"""
    if not content or not entities:
        return []
    
    contexts = []
    for entity in entities:
        entity_name = entity["name"]
        # 查找实体在内容中的位置
        pos = content.lower().find(entity_name.lower())
        if pos != -1:
            start = max(0, pos - context_size)
            end = min(len(content), pos + len(entity_name) + context_size)
            context = content[start:end]
            
            # 高亮实体名称
            context = context.replace(entity_name, f"**{entity_name}**")
            
            contexts.append({
                "entity": entity_name,
                "context": f"...{context}...",
                "position": pos
            })
    
    return contexts[:5]  # 返回前5个上下文

# ==================== 流式聊天接口 ====================

@app.post("/chat/stream")
async def chat_stream(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    流式聊天接口 - 支持思考过程可视化
    
    请求体:
    {
        "query": "用户的问题",
        "mode": "full"  # 或 "simple"，full显示详细思考过程
    }
    """
    start_time = time.time()
    query = request.get("query", "").strip()
    mode = request.get("mode", "full")  # full: 完整思考过程，simple: 简化版
    top_k = request.get("top_k", 10)
    final_k = request.get("final_k", 3)
    
    if not query:
        return StreamingResponse(
            iter([AgentMessage.error("请输入问题")]),
            media_type="text/plain"
        )
    
    workflow_id = f"chat_stream_{datetime.now().timestamp()}"
    
    try:
        # 获取聊天服务
        chat_service = get_agentic_chat_service()
        
        if mode == "full":
            # 完整思考过程模式
            async def generate_full():
                async for message in chat_service.stream_chat_with_thinking(
                    query=query,
                    db=db,
                    top_k=top_k,
                    final_k=final_k,
                    workflow_id=workflow_id
                ):
                    yield message
            
            return StreamingResponse(
                generate_full(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Stream-Mode": "full",
                    "X-Workflow-ID": workflow_id
                }
            )
        else:
            # 简化模式
            async def generate_simple():
                async for message in chat_service.stream_simple_chat(
                    query=query,
                    db=db,
                    workflow_id=workflow_id
                ):
                    yield message
            
            return StreamingResponse(
                generate_simple(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Stream-Mode": "simple",
                    "X-Workflow-ID": workflow_id
                }
            )
        
    except Exception as e:
        logger.error(f"流式聊天失败: {e}", exc_info=True)
        return StreamingResponse(
            iter([AgentMessage.error(f"聊天失败: {str(e)}")]),
            media_type="text/plain"
        )

@app.get("/chat/debug/{workflow_id}")
async def get_chat_debug_info(workflow_id: str):
    """获取聊天调试信息"""
    # 这里可以连接数据库或Redis获取实际的工作流状态
    # 暂时返回模拟数据
    return {
        "workflow_id": workflow_id,
        "status": "completed",
        "timestamp": datetime.now().isoformat(),
        "debug_info": {
            "mode": "full",
            "thinking_steps": [
                {"stage": "thinking_start", "time": "2026-01-01T10:00:00"},
                {"stage": "retrieval", "time": "2026-01-01T10:00:01"},
                {"stage": "generation", "time": "2026-01-01T10:00:03"},
                {"stage": "complete", "time": "2026-01-01T10:00:05"}
            ]
        }
    }

# 更新需要安全的 API 使用安全数据库会话
@app.post("/chat/secure")
async def secure_chat(
    request: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_secure_db)
):
    """安全聊天接口 - 使用 RLS 保护的数据库会话"""
    query = request.get("query", "").strip()
    
    if not query:
        raise HTTPException(status_code=400, detail="请输入问题")
    
    try:
        # 设置用户上下文（已在中间件中设置）
        # 直接使用安全搜索
        from services.search import secure_hybrid_search
        
        results = await secure_hybrid_search(
            query=query,
            db=db,
            user_id=current_user.id,
            top_k=10,
            final_k=3
        )
        
        return {
            "query": query,
            "results": results,
            "user_id": current_user.id,
            "documents_found": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


# ==================== 智能体 -- 支持工具调用 ====================

@app.post("/agent/execute")
async def agent_execute(
    request: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_secure_db)
):
    """
    智能体执行接口 - 支持工具调用
    
    请求体:
    {
        "query": "用户问题",
        "use_knowledge": true,  # 是否使用知识库
        "stream": false         # 是否流式输出
    }
    """
    query = request.get("query", "").strip()
    use_knowledge = request.get("use_knowledge", True)
    stream = request.get("stream", False)
    
    if not query:
        raise HTTPException(status_code=400, detail="请输入问题")
    
    # 获取知识库上下文
    context = ""
    if use_knowledge:
        from services.search import secure_hybrid_search
        try:
            docs = await secure_hybrid_search(
                query=query,
                db=db,
                user_id=current_user.id,
                top_k=5,
                final_k=2
            )
            if docs:
                context = "\n".join([doc.get('content', '')[:500] for doc in docs[:2]])
        except Exception as e:
            logger.warning(f"知识库搜索失败: {e}")
    
    if stream:
        # 流式响应
        async def event_generator():
            try:
                # 创建工作流（带writer）
                from services.agent_graph import get_agent_workflow
                app = get_agent_workflow()
                
                # 初始化状态
                initial_state = {
                    "messages": [HumanMessage(content=query)],
                    "documents": [],
                    "generation": "",
                    "current_node": "start",
                    "node_history": [],
                    "start_time": datetime.now(),
                    "error": None,
                    "retry_count": 0,
                    "is_relevant": None
                }
                
                # 执行工作流
                async for event in app.astream(initial_state, {"db": db}):
                    for key, value in event.items():
                        if key == "generation" and value:
                            yield f"data: {json.dumps({'type': 'chunk', 'data': value})}\n\n"
                        elif key == "tool_calls":
                            for tool_call in value:
                                yield f"data: {json.dumps({'type': 'tool_call', 'data': tool_call})}\n\n"
                        elif key == "tool_results":
                            for tool_result in value:
                                yield f"data: {json.dumps({'type': 'tool_result', 'data': tool_result})}\n\n"
                
                yield f"data: {json.dumps({'type': 'complete', 'data': '完成'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'data': f'执行失败: {str(e)}'})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # 非流式响应
        try:
            from services.agent_graph import get_agent_workflow
            app = get_agent_workflow()
            
            initial_state = {
                "messages": [HumanMessage(content=query)],
                "documents": [],
                "generation": "",
                "current_node": "start",
                "node_history": [],
                "start_time": datetime.now(),
                "error": None,
                "retry_count": 0,
                "is_relevant": None
            }
            
            result = await app.ainvoke(initial_state, {"db": db})
            
            return {
                "success": True,
                "query": query,
                "response": result.get("generation", ""),
                "tools_used": result.get("tool_calls", []),
                "tools_count": len(result.get("tool_calls", [])),
                "tool_results": result.get("tool_results", []),
                "user_id": current_user.id,
                "node_history": result.get("node_history", [])
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"智能体执行失败: {str(e)}")

@app.get("/agent/tools")
async def list_available_tools(
    current_user: User = Depends(get_current_active_user)
):
    """列出所有可用工具"""
    tool_manager = get_tool_manager()
    tools = tool_manager.get_tools_description()
    
    return {
        "tools": tools,
        "total": len(tools),
        "user_id": current_user.id
    }

@app.post("/agent/tools/execute")
async def execute_specific_tool(
    request: dict,
    current_user: User = Depends(get_current_active_user)
):
    """直接执行特定工具"""
    tool_name = request.get("tool_name", "").strip()
    tool_args = request.get("tool_args", {})
    
    if not tool_name:
        raise HTTPException(status_code=400, detail="请指定工具名称")
    
    tool_manager = get_tool_manager()
    
    # 执行工具
    result = await tool_manager.execute_tool(tool_name, **tool_args)
    
    return {
        "success": result.get("success", False),
        "tool_name": tool_name,
        "tool_args": tool_args,
        "result": result,
        "user_id": current_user.id,
        "timestamp": datetime.now().isoformat()
    }


# ==================== 知识图谱 ====================

@app.get("/graph/entities")
async def get_entities(
    db: Session = Depends(get_secure_db),
    current_user: User = Depends(get_current_active_user),
    query: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """获取实体列表"""
    from sqlmodel import select
    
    stmt = select(Entity).where(Entity.user_id == current_user.id)
    
    if query:
        stmt = stmt.where(Entity.name.ilike(f"%{query}%"))
    
    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
    
    stmt = stmt.offset(offset).limit(limit)
    
    entities = db.exec(stmt).all()
    
    return {
        "entities": [entity.to_dict() for entity in entities],
        "total": len(entities)
    }

@app.get("/graph/edges")
async def get_edges(
    db: Session = Depends(get_secure_db),
    current_user: User = Depends(get_current_active_user),
    source_id: Optional[int] = None,
    target_id: Optional[int] = None,
    relation_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """获取关系边"""
    from sqlmodel import select
    
    stmt = select(GraphEdge).where(GraphEdge.user_id == current_user.id)
    
    if source_id:
        stmt = stmt.where(GraphEdge.source_id == source_id)
    
    if target_id:
        stmt = stmt.where(GraphEdge.target_id == target_id)
    
    if relation_type:
        stmt = stmt.where(GraphEdge.relation_type == relation_type)
    
    stmt = stmt.offset(offset).limit(limit)
    
    edges = db.exec(stmt).all()
    
    return {
        "edges": [edge.to_dict() for edge in edges],
        "total": len(edges)
    }

@app.get("/graph/data")
async def get_graph_data(
    db: Session = Depends(get_secure_db),
    current_user: User = Depends(get_current_active_user),
    document_id: Optional[int] = None,
    include_documents: bool = True  # 新增参数：是否包含文档信息
):
    """获取图谱数据（用于可视化）"""
    from sqlmodel import select
    
    # 获取实体
    if document_id:
        # 获取特定文档的实体
        from models import EntityDocumentLink
        stmt = select(Entity).join(EntityDocumentLink).where(
            EntityDocumentLink.document_id == document_id,
            Entity.user_id == current_user.id
        ).limit(50)
    else:
        # 获取所有实体（按频率排序）
        stmt = select(Entity).where(
            Entity.user_id == current_user.id
        ).order_by(Entity.frequency.desc()).limit(100)  # 增加到100个
    
    entities = db.exec(stmt).all()
    
    if not entities:
        return {"nodes": [], "links": []}
    
    entity_ids = [e.id for e in entities]
    
    # 获取关系
    edges = db.exec(
        select(GraphEdge).where(
            or_(
                GraphEdge.source_id.in_(entity_ids),
                GraphEdge.target_id.in_(entity_ids)
            ),
            GraphEdge.user_id == current_user.id
        ).limit(300)
    ).all()
    
    # 如果要求包含文档信息，获取实体的关联文档
    entity_docs_map = {}
    if include_documents:
        from models import EntityDocumentLink
        # 查询所有实体的文档关联
        doc_links = db.exec(
            select(EntityDocumentLink).where(
                EntityDocumentLink.entity_id.in_(entity_ids)
            )
        ).all()
        
        # 构建实体到文档的映射
        for link in doc_links:
            if link.entity_id not in entity_docs_map:
                entity_docs_map[link.entity_id] = []
            
            # 获取文档详情
            doc = db.get(Document, link.document_id)
            if doc and doc.user_id == current_user.id:  # 确保文档属于当前用户
                entity_docs_map[link.entity_id].append({
                    "id": doc.id,
                    "title": doc.title,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "relevance": link.significance  # 关联程度
                })
    
    # 构建节点数据
    nodes = []
    for entity in entities:
        node_data = {
            "id": entity.id,
            "name": entity.name,
            "type": entity.entity_type,
            "description": entity.description,
            "group": _get_entity_group(entity.entity_type),
            "frequency": entity.frequency,
            "confidence": entity.confidence,
            "document_count": len(entity.documents) if hasattr(entity, 'documents') else 0
        }
        
        # 添加文档信息
        if include_documents and entity.id in entity_docs_map:
            docs = entity_docs_map[entity.id]
            node_data["documents"] = docs
            # 按关联程度排序，取最相关的文档
            if docs:
                sorted_docs = sorted(docs, key=lambda x: x.get("relevance", 0), reverse=True)
                node_data["primary_doc_id"] = sorted_docs[0]["id"]
                node_data["primary_doc_title"] = sorted_docs[0]["title"]
        
        nodes.append(node_data)
    
    # 构建边数据
    links = []
    for edge in edges:
        links.append({
            "source": edge.source_id,
            "target": edge.target_id,
            "relation": edge.relation_type,
            "weight": edge.weight,
            "description": edge.description,
            "source_context": edge.source_context[:100] if edge.source_context else None,
            "source_document_id": edge.source_document_id  # 记录关系来源文档
        })
    
    # 添加文档节点（如果指定了文档）
    doc_nodes = []
    if document_id:
        doc = db.get(Document, document_id)
        if doc and doc.user_id == current_user.id:
            doc_nodes.append({
                "id": f"doc_{doc.id}",
                "name": doc.title,
                "type": "DOCUMENT",
                "group": 7,  # 文档类型
                "is_document": True,
                "document_id": doc.id,
                "content_preview": doc.content[:200] if doc.content else ""
            })
    
    return {
        "nodes": nodes + doc_nodes,
        "links": links,
        "stats": {
            "total_entities": len(entities),
            "total_edges": len(edges),
            "entity_types": _count_entity_types(entities)
        }
    }

def _get_entity_group(entity_type: str) -> int:
    """根据实体类型返回组ID"""
    type_groups = {
        "PERSON": 1,
        "ORGANIZATION": 2,
        "CONCEPT": 3,
        "PRODUCT": 4,
        "LOCATION": 5,
        "EVENT": 6
    }
    return type_groups.get(entity_type.upper(), 0)

def _count_entity_types(entities):
    """统计实体类型"""
    counts = {}
    for entity in entities:
        counts[entity.entity_type] = counts.get(entity.entity_type, 0) + 1
    return counts

@app.get("/graph/entity/{entity_id}")
async def get_entity_details(
    entity_id: int,
    db: Session = Depends(get_secure_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取实体详情"""
    from sqlmodel import select
    
    entity = db.get(Entity, entity_id)
    
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="实体不存在或无权访问")
    
    # 获取相关关系
    outgoing_edges = db.exec(
        select(GraphEdge).where(
            GraphEdge.source_id == entity_id,
            GraphEdge.user_id == current_user.id
        )
    ).all()
    
    incoming_edges = db.exec(
        select(GraphEdge).where(
            GraphEdge.target_id == entity_id,
            GraphEdge.user_id == current_user.id
        )
    ).all()
    
    # 获取相关文档
    from models import EntityDocumentLink
    doc_links = db.exec(
        select(EntityDocumentLink).where(EntityDocumentLink.entity_id == entity_id)
    ).all()
    
    documents = []
    for link in doc_links:
        doc = db.get(Document, link.document_id)
        if doc:
            documents.append({
                "id": doc.id,
                "title": doc.title,
                "content_preview": doc.content[:200] if doc.content else None,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            })
    
    return {
        "entity": entity.to_dict(),
        "relationships": {
            "outgoing": [edge.to_dict() for edge in outgoing_edges],
            "incoming": [edge.to_dict() for edge in incoming_edges],
            "total": len(outgoing_edges) + len(incoming_edges)
        },
        "documents": documents,
        "stats": {
            "document_count": len(documents),
            "relationship_count": len(outgoing_edges) + len(incoming_edges)
        }
    }

@app.get("/graph/entity/{entity_id}/documents")
async def get_entity_documents(
    entity_id: int,
    db: Session = Depends(get_secure_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = 10,
    offset: int = 0
):
    """获取实体关联的文档列表"""
    from sqlmodel import select
    from models import EntityDocumentLink
    
    # 检查实体是否存在且属于当前用户
    entity = db.get(Entity, entity_id)
    if not entity or entity.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="实体不存在或无权访问")
    
    # 获取文档关联
    doc_links = db.exec(
        select(EntityDocumentLink)
        .where(EntityDocumentLink.entity_id == entity_id)
        .offset(offset)
        .limit(limit)
    ).all()
    
    documents = []
    for link in doc_links:
        doc = db.get(Document, link.document_id)
        if doc and doc.user_id == current_user.id:
            documents.append({
                "id": doc.id,
                "title": doc.title,
                "content_preview": doc.content[:300] if doc.content else "",
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                "relevance": link.significance,
                "frequency_in_doc": link.frequency_in_doc,
                "occurrences": link.occurrences[:5] if link.occurrences else []  # 前5个出现位置
            })
    
    return {
        "entity": {
            "id": entity.id,
            "name": entity.name,
            "type": entity.entity_type
        },
        "documents": documents,
        "total": len(doc_links)
    }

@app.post("/graph/query")
async def graph_query(
    request: dict,
    db: Session = Depends(get_secure_db),
    current_user: User = Depends(get_current_active_user)
):
    """GraphRAG 查询"""
    query = request.get("query", "").strip()
    
    if not query:
        raise HTTPException(status_code=400, detail="请输入查询内容")
    
    from services.graph_rag import get_graph_rag_service
    
    service = get_graph_rag_service(db)
    result = await service.query(query, current_user.id)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "查询失败"))
    
    return result

@app.post("/graph/extract/{document_id}")
async def extract_graph_from_document(
    document_id: int,
    db: Session = Depends(get_secure_db),
    current_user: User = Depends(get_current_active_user)
):
    """手动触发图谱提取"""
    from models import Document
    from tasks.document_tasks import extract_graph_from_document
    
    document = db.get(Document, document_id)
    
    if not document or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文档不存在或无权访问")
    
    # 触发异步任务
    task = extract_graph_from_document.delay(document_id, current_user.id)
    
    return {
        "message": "知识图谱提取任务已开始",
        "task_id": task.id,
        "document_id": document_id,
        "status_url": f"/task/status/{task.id}"
    }

@app.get("/graph/stats")
async def get_graph_stats(
    db: Session = Depends(get_secure_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取图谱统计信息"""
    from sqlmodel import select, func
    
    # 实体统计
    entity_stats = db.exec(
        select(Entity.entity_type, func.count(Entity.id))
        .where(Entity.user_id == current_user.id)
        .group_by(Entity.entity_type)
    ).all()
    
    total_entities = sum(count for _, count in entity_stats)
    
    # 关系统计
    relation_stats = db.exec(
        select(GraphEdge.relation_type, func.count(GraphEdge.id))
        .where(GraphEdge.user_id == current_user.id)
        .group_by(GraphEdge.relation_type)
    ).all()
    
    total_edges = sum(count for _, count in relation_stats)
    
    # 文档统计
    doc_stats = db.exec(
        select(func.count(Document.id))
        .where(
            Document.user_id == current_user.id,
            Document.graph_extracted == True
        )
    ).first()
    
    extracted_docs = doc_stats[0] if doc_stats else 0
    
    total_docs = db.exec(
        select(func.count(Document.id))
        .where(Document.user_id == current_user.id)
    ).first()[0]
    
    return {
        "entities": {
            "total": total_entities,
            "by_type": dict(entity_stats)
        },
        "relationships": {
            "total": total_edges,
            "by_type": dict(relation_stats)
        },
        "documents": {
            "total": total_docs,
            "with_graph": extracted_docs,
            "coverage": f"{(extracted_docs / total_docs * 100):.1f}%" if total_docs > 0 else "0%"
        }
    }

@app.post("/graph/batch-extract")
async def batch_extract_graphs(
    request: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_secure_db)
):
    """批量提取知识图谱"""
    document_ids = request.get("document_ids", [])
    
    if not document_ids:
        raise HTTPException(status_code=400, detail="请提供文档ID列表")
    
    task = batch_extract_graphs.delay(document_ids, current_user.id)
    
    return {
        "message": "批量图谱提取任务已开始",
        "task_id": task.id,
        "document_count": len(document_ids),
        "status_url": f"/task/status/{task.id}"
    }

@app.post("/graph/reprocess-all")
async def reprocess_all_graphs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_secure_db)
):
    """重新提取所有文档的知识图谱"""
    task = reprocess_all_graphs.delay(current_user.id)
    
    return {
        "message": "重新提取所有文档知识图谱任务已开始",
        "task_id": task.id,
        "status_url": f"/task/status/{task.id}"
    }

@app.post("/graph/cleanup")
async def cleanup_graph(
    cleanup_type: str = "all",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_secure_db)
):
    """清理知识图谱"""
    if cleanup_type == "entities":
        task = cleanup_orphaned_entities.delay(current_user.id)
    elif cleanup_type == "edges":
        task = cleanup_orphaned_edges.delay(current_user.id)
    elif cleanup_type == "all":
        # 先清理边，再清理实体
        task1 = cleanup_orphaned_edges.delay(current_user.id)
        task2 = cleanup_orphaned_entities.delay(current_user.id)
        return {
            "message": "知识图谱清理任务已开始",
            "tasks": [
                {"type": "edges", "task_id": task1.id},
                {"type": "entities", "task_id": task2.id}
            ],
            "status_urls": [
                f"/task/status/{task1.id}",
                f"/task/status/{task2.id}"
            ]
        }
    else:
        raise HTTPException(status_code=400, detail="无效的清理类型")
    
    return {
        "message": f"知识图谱清理任务已开始 ({cleanup_type})",
        "task_id": task.id,
        "status_url": f"/task/status/{task.id}"
    }

# ==================== 保留原有接口 ====================

@app.get("/")
async def root():
    return {"message": "欢迎使用 KnoSphere API v2.1 - 分布式异步处理系统"}

@app.get("/health")
async def health():
    """健康检查接口"""
    from core.logger import log_health_check
    system_info = log_health_check()
    
    # 检查数据库连接
    db_ok = False
    try:
        with engine.connect() as conn:
            from sqlmodel import text
            conn.execute(text("SELECT 1"))
            db_ok = True
    except:
        db_ok = False
    
    # 检查 Redis 连接
    redis_ok = False
    try:
        import redis
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        redis_ok = redis_client.ping()
    except:
        redis_ok = False
    
    # 检查 Celery Worker
    celery_ok = False
    try:
        inspector = celery_app.control.inspect()
        stats = inspector.stats() or {}
        celery_ok = len(stats) > 0
    except:
        celery_ok = False
    
    status = "healthy" if db_ok and redis_ok and celery_ok else "degraded"
    
    return {
        "status": status,
        "service": "KnoSphere API v2.1",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": "healthy" if db_ok else "unhealthy",
            "redis": "healthy" if redis_ok else "unhealthy",
            "celery_workers": "healthy" if celery_ok else "unhealthy",
            "system": system_info
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 启动 KnoSphere Agentic RAG 系统...")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True,
        log_config=None  # 使用我们自定义的日志
    )