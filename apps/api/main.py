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
from datetime import datetime, timezone
from pathlib import Path

from deps import get_current_active_user
from core.auth import ACCESS_TOKEN_EXPIRE_MINUTES, Token, UserCreate, PasswordChange
from core.database_middleware import get_secure_db

# 导入 Celery 任务
from tasks.document_tasks import process_large_document, batch_process_documents
from tasks.celery_app import celery_app


from core.logger import logger, log_api_response
from database import get_db, init_db, engine, get_session
from models import Document, User

from services.agentic_chat import get_agentic_chat_service

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
    db: Session = Depends(get_session)
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

@app.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)  # 使用普通的get_db，而不是带RLS的
):
    """用户登录"""
    from core.auth import AuthService
    
    auth_service = AuthService()
    
    # 使用认证服务的统一方法
    user = await auth_service.authenticate_user(
        form_data.username, 
        form_data.password, 
        db
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建令牌
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        username=user.username,
        permissions=getattr(user, 'permissions', {})
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
    db: Session = Depends(get_session)
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
    user_id: Optional[int] = None,
    db: Session = Depends(get_session)
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
    user_id: Optional[int] = None,
    db: Session = Depends(get_session)
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
    db: Session = Depends(get_session),
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
    db: Session = Depends(get_session),
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


# ==================== 流式聊天接口 ====================

@app.post("/chat/stream")
async def chat_stream(
    request: dict,
    db: Session = Depends(get_session)
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