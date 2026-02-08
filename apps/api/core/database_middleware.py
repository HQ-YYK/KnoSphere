"""
数据库中间件 - 用于设置 PostgreSQL RLS 上下文
"""
import logging
from fastapi import Request
from sqlalchemy import event
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import ipaddress

logger = logging.getLogger(__name__)

class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    """数据库会话中间件 - 设置 RLS 上下文"""
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 获取用户ID和客户端信息
        user_id = getattr(request.state, 'user_id', None)
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # 设置数据库上下文
        request.state.db_context = {
            "user_id": user_id,
            "client_ip": client_ip,
            "user_agent": user_agent
        }
        
        response = await call_next(request)
        return response

def setup_rls_context(session: Session, user_id: int = None, **context):
    """
    设置 PostgreSQL RLS 上下文
    
    参数:
    - session: SQLAlchemy 会话
    - user_id: 当前用户ID
    - context: 其他上下文信息
    """
    if not user_id:
        user_id = 0  # 匿名用户
    
    try:
        # 设置当前用户ID
        session.execute(f"SET app.current_user_id = '{user_id}'")
        
        # 设置客户端IP
        client_ip = context.get('client_ip')
        if client_ip:
            # 验证IP地址
            try:
                ipaddress.ip_address(client_ip)
                session.execute(f"SET app.client_ip = '{client_ip}'")
            except ValueError:
                session.execute("SET app.client_ip = '0.0.0.0'")
        
        # 设置用户代理
        user_agent = context.get('user_agent', '')[:500]  # 限制长度
        session.execute(f"SET app.user_agent = '{user_agent}'")
        
        # 设置其他上下文变量
        session.execute("SET app.request_time = current_timestamp")
        
    except Exception as e:
        logger.warning(f"设置 RLS 上下文失败: {e}")
        # 回退到安全默认值
        session.execute("SET app.current_user_id = '0'")
        session.execute("SET app.client_ip = '0.0.0.0'")
        session.execute("SET app.user_agent = ''")

@event.listens_for(Session, "after_begin")
def setup_rls(session, transaction, connection):
    """会话开始时设置 RLS 上下文"""
    # 从会话的 info 字典中获取上下文
    context = getattr(session, '_rls_context', {})
    user_id = context.get('user_id', 0)
    
    # 设置 RLS 上下文
    setup_rls_context(session, user_id, **context)

def get_db_with_context(request: Request) -> Session:
    """
    获取带有 RLS 上下文的数据库会话
    
    这是一个替代的依赖项，用于需要 RLS 的接口
    """
    from database import SessionLocal
    
    db = SessionLocal()
    
    try:
        # 设置 RLS 上下文
        context = getattr(request.state, 'db_context', {})
        db._rls_context = context
        
        yield db
    finally:
        db.close()

# 创建需要 RLS 的数据库会话依赖项
from fastapi import Depends
def get_secure_db(request: Request) -> Session:
    return next(get_db_with_context(request))