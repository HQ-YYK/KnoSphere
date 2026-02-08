import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from celery import Task
from sqlmodel import Session, select
from tasks.celery_app import celery_app
from core.logger import logger
from database import engine
from models import Document

@celery_app.task(bind=True, name="tasks.cleanup_tasks.cleanup_old_files")
def cleanup_old_files(self):
    """清理旧的上传文件"""
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        return {"status": "skipped", "reason": "uploads directory not found"}
    
    cutoff_time = datetime.now() - timedelta(hours=24)  # 24小时前
    deleted_files = []
    total_size = 0
    
    for file_path in uploads_dir.glob("**/*"):
        if file_path.is_file():
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time < cutoff_time:
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_files.append(str(file_path))
                    total_size += file_size
                    logger.debug(f"🗑️ 清理旧文件: {file_path}")
                except Exception as e:
                    logger.warning(f"清理文件失败 {file_path}: {e}")
    
    logger.info(f"✅ 文件清理完成: 删除 {len(deleted_files)} 个文件，释放 {total_size/1024/1024:.2f}MB")
    
    return {
        "status": "completed",
        "deleted_files": len(deleted_files),
        "freed_space_mb": total_size / 1024 / 1024,
        "timestamp": datetime.now().isoformat()
    }

@celery_app.task(bind=True, base=Task, name="tasks.cleanup_tasks.optimize_database")
def optimize_database(self):
    """数据库优化任务"""
    try:
        with Session(engine) as session:
            # 统计文档
            total_docs = session.exec(select(Document)).all()
            total_count = len(total_docs)
            
            # 清理无向量的文档
            docs_without_vectors = session.exec(
                select(Document).where(Document.embedding == None)
            ).all()
            
            if docs_without_vectors:
                for doc in docs_without_vectors:
                    session.delete(doc)
                session.commit()
                deleted_count = len(docs_without_vectors)
                logger.info(f"🗑️ 清理了 {deleted_count} 个无向量文档")
            else:
                deleted_count = 0
            
            return {
                "status": "completed",
                "total_documents": total_count,
                "deleted_documents": deleted_count,
                "remaining_documents": total_count - deleted_count,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"数据库优化失败: {e}")
        return {"status": "failed", "error": str(e)}