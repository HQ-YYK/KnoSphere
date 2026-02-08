from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from contextlib import asynccontextmanager
from sqlmodel import Session, text
from typing import List, Optional
import os
import io
import time
from datetime import datetime

# 导入新模块
from core.logger import logger, WorkflowLogger, log_api_request, log_api_response, get_performance_monitor
from services.agent_graph import get_agent_workflow, format_workflow_debug
from services.llm import get_llm_service

# 数据库和模型导入
from database import init_db, engine, get_session
from models import User, Document
from services.embedding import generate_vector

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动 KnoSphere API...")
    
    # 健康检查日志
    from core.logger import log_health_check
    log_health_check()
    
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    init_db()
    
    logger.info("✅ 数据库初始化完成")
    
    yield
    
    logger.info("👋 关闭 KnoSphere API...")

app = FastAPI(
    title="KnoSphere API",
    description="2026 企业级智能知识库系统 - Agentic RAG",
    version="2.0.0",
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

# ==================== 中间件：请求日志 ====================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    start_time = time.time()
    
    # 记录请求
    try:
        body = await request.body()
        request_data = {}
        if body:
            try:
                import json
                request_data = json.loads(body)
            except:
                pass
        
        log_api_request(
            request_data,
            str(request.url.path),
            request.headers.get("user-agent")
        )
    except Exception as e:
        logger.warning(f"请求日志记录失败: {e}")
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应
    process_time = time.time() - start_time
    log_api_response(
        str(request.url.path),
        response.status_code,
        process_time
    )
    
    # 添加性能头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# ==================== Agentic RAG 聊天接口 ====================

@app.post("/chat/agent")
async def agent_chat(
    request: dict,
    db: Session = Depends(get_session)
):
    """
    Agentic RAG 聊天接口 - 使用 LangGraph 工作流
    
    请求体:
    {
        "query": "用户的问题",
        "stream": true,  # 是否流式响应
        "debug": false   # 是否返回调试信息
    }
    """
    start_time = time.time()
    query = request.get("query", "").strip()
    stream = request.get("stream", True)
    debug = request.get("debug", False)
    
    if not query:
        return JSONResponse(
            status_code=400,
            content={"error": "请输入问题"}
        )
    
    workflow_id = WorkflowLogger.workflow_start(query)
    
    try:
        # 获取工作流实例
        workflow = get_agent_workflow()
        
        # 准备初始状态
        from langchain_core.messages import HumanMessage
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
        config = {"db": db}
        final_state = await workflow.ainvoke(initial_state, config=config)
        
        # 记录性能
        total_time = time.time() - start_time
        monitor = get_performance_monitor()
        monitor.record_metric("workflow_times", total_time, workflow_id=workflow_id)
        
        # 记录工作流完成
        WorkflowLogger.workflow_complete(workflow_id, final_state, total_time)
        
        # 准备响应
        response_data = {
            "query": query,
            "answer": final_state.get("generation", ""),
            "workflow_id": workflow_id,
            "execution_time": round(total_time, 3),
            "documents_used": len(final_state.get("documents", [])),
            "node_path": [node.get("node") for node in final_state.get("node_history", [])]
        }
        
        if debug:
            response_data["debug"] = format_workflow_debug(final_state)
        
        if stream:
            # 流式响应
            async def generate():
                # 先发送工作流信息
                yield f"data: {json.dumps({'type': 'workflow_info', 'data': response_data})}\n\n"
                
                # 流式发送回答
                answer = final_state.get("generation", "")
                for i in range(0, len(answer), 100):
                    chunk = answer[i:i+100]
                    yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
                    await asyncio.sleep(0.01)  # 模拟流式效果
                
                yield f"data: {json.dumps({'type': 'complete', 'data': {'workflow_id': workflow_id}})}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # 非流式响应
            return response_data
            
    except Exception as e:
        logger.error(f"工作流执行失败: {e}", exc_info=True)
        total_time = time.time() - start_time
        log_api_response("/chat/agent", 500, total_time, str(e))
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "工作流执行失败",
                "detail": str(e),
                "workflow_id": workflow_id,
                "execution_time": round(total_time, 3)
            }
        )

@app.get("/chat/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """获取工作流状态（用于前端轮询）"""
    # 这里可以连接 Redis 或数据库获取实际状态
    # 暂时返回模拟数据
    return {
        "workflow_id": workflow_id,
        "status": "completed",
        "timestamp": datetime.now().isoformat()
    }

# ==================== 健康检查接口 ====================

@app.get("/health")
async def health():
    """健康检查接口"""
    from core.logger import log_health_check
    system_info = log_health_check()
    
    # 检查数据库连接
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except:
        db_ok = False
    
    # 检查向量扩展
    vector_ok = False
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
            vector_ok = result.fetchone() is not None
    except:
        vector_ok = False
    
    return {
        "status": "healthy" if db_ok and vector_ok else "degraded",
        "service": "KnoSphere API v2.0",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": "healthy" if db_ok else "unhealthy",
            "vector_extension": "enabled" if vector_ok else "disabled",
            "system": system_info
        }
    }

@app.get("/metrics")
async def get_metrics():
    """获取性能指标"""
    monitor = get_performance_monitor()
    summary = monitor.get_summary()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": summary,
        "system": {
            "version": "2.0.0",
            "features": ["agentic_rag", "langgraph", "structured_logging"]
        }
    }

# ==================== 保留原有接口 ====================

@app.get("/")
async def root():
    return {"message": "欢迎使用 KnoSphere API v2.0 - 企业级智能知识库系统"}

# ... 保留原有的 /upload, /query, /chat 等接口 ...

if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    logger.info("🚀 启动 KnoSphere Agentic RAG 系统...")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True,
        log_config=None  # 使用我们自定义的日志
    )