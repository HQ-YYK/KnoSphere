"""
数据库中间件 - 用于设置 PostgreSQL RLS 上下文
"""
from typing import Optional
from core.logger import logger
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
import ipaddress
from database import engine

def setup_rls_context(session: Session, user_id: Optional[int] = None, **context):
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
        session.execute(text(f"SET app.current_user_id = '{user_id}'"))
        
        # 设置客户端IP
        client_ip = context.get('client_ip')
        if client_ip:
            try:
                ipaddress.ip_address(client_ip)
                session.execute(text(f"SET app.client_ip = '{client_ip}'"))
            except ValueError:
                session.execute(text("SET app.client_ip = '0.0.0.0'"))
        
        # 设置用户代理
        user_agent = context.get('user_agent', '')[:500]
        session.execute(text(f"SET app.user_agent = '{user_agent}'"))
        
        # 设置其他上下文变量
        session.execute(text("SET app.request_time = current_timestamp"))
        
        session.commit()  # 立即提交设置
        
    except Exception as e:
        logger.warning(f"设置 RLS 上下文失败: {e}")
        session.rollback()
        # 回退到安全默认值
        try:
            session.execute(text("SET app.current_user_id = '0'"))
            session.execute(text("SET app.client_ip = '0.0.0.0'"))
            session.execute(text("SET app.user_agent = ''"))
            session.commit()
        except:
            pass

class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    """数据库会话中间件 - 设置 RLS 上下文"""
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 获取用户ID和客户端信息（登录前可能没有用户ID）
        user_id = getattr(request.state, 'user_id', None)
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        
        # 存储到请求状态
        request.state.db_context = {
            "user_id": user_id,
            "client_ip": client_ip,
            "user_agent": user_agent
        }
        
        response = await call_next(request)
        return response

# 修改：使用生成器函数而不是上下文管理器
def get_secure_db(request: Request):
    """
    获取带有 RLS 上下文的数据库会话（生成器函数）
    用于需要RLS保护的路由
    """
    # 创建新的会话
    session = Session(engine)
    try:
        # 从请求状态获取上下文
        context = getattr(request.state, 'db_context', {})
        
        # 设置RLS上下文
        setup_rls_context(session, **context)
        
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()