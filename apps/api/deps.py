"""
依赖项管理 - 避免循环导入
"""
from models import User
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlmodel import Session, select
import os
import secrets
from fastapi.security import OAuth2PasswordBearer
from database import get_db

# 从环境变量读取配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# OAuth2 方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db) 
):
    """获取当前用户"""
    from models import User
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub") or 0)
        username = payload.get("username") or ""
        
        if user_id is None or username is None:
            raise credentials_exception
        
    except (JWTError, ValueError):
        raise credentials_exception
    
    # 查找用户
    statement = select(User).where(User.id == user_id)
    user = db.exec(statement).first()
    
    if user is None:
        raise credentials_exception
    
    if not getattr(user, 'is_active', True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
):
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="用户未激活"
        )
    return current_user