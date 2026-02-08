import os
import time
import asyncio
from pathlib import Path
from typing import Dict, Any
from celery import Task
from sqlmodel import Session, select
from tasks.celery_app import celery_app
from core.logger import logger, WorkflowLogger
from services.embedding import generate_vector
from database import engine
from models import Document

class BaseTaskWithDB(Task):
    """带有数据库连接的基础任务类"""
    
    def __init__(self):
        super().__init__()
        self.db_session = None
    
    def before_start(self, task_id, args, kwargs):
        """任务开始前初始化数据库连接"""
        logger.info(f"任务 {task_id} 开始执行")
        self.db_session = Session(engine)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的处理"""
        logger.error(f"任务 {task_id} 失败: {exc}", exc_info=True)
        if self.db_session:
            self.db_session.rollback()
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """任务返回后的清理"""
        if self.db_session:
            self.db_session.close()
        logger.info(f"任务 {task_id} 完成，状态: {status}")

@celery_app.task(bind=True, base=BaseTaskWithDB, name="tasks.document_tasks.process_large_document")
def process_large_document(self, file_path: str, doc_id: int, user_id: int = None):
    """
    处理大文档任务
    
    参数:
    - file_path: 文件路径
    - doc_id: 文档ID
    - user_id: 用户ID（可选）
    """
    task_id = self.request.id
    logger.info(f"🚀 开始后台处理文档 ID: {doc_id}, 任务ID: {task_id}")
    
    try:
        # 1. 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 2. 根据文件类型选择处理方式
        file_ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        
        logger.info(f"📄 处理文件: {file_path} ({file_size:.2f}MB)")
        
        # 3. 读取文件内容
        content = ""
        total_steps = 0
        
        if file_ext == '.pdf':
            content, total_steps = _process_pdf(file_path)
        elif file_ext == '.docx':
            content, total_steps = _process_docx(file_path)
        elif file_ext in ['.txt', '.md']:
            content, total_steps = _process_text(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
        
        # 4. 更新任务进度（25%）
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 1,
                'total': 4,
                'stage': '文件解析完成',
                'progress': 25,
                'details': f"已解析 {len(content)} 字符"
            }
        )
        
        # 5. 分割文档为块（模拟大文档处理）
        chunks = _split_into_chunks(content, max_chunk_size=2000)
        logger.info(f"📑 文档分割为 {len(chunks)} 个块")
        
        # 6. 更新任务进度（50%）
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 2,
                'total': 4,
                'stage': '文档分割完成',
                'progress': 50,
                'details': f"已分割为 {len(chunks)} 个块"
            }
        )
        
        # 7. 为每个块生成向量
        vectors = []
        
        for i, chunk in enumerate(chunks):
            # 根据块的大小动态选择维度
            chunk_len = len(chunk)
            if chunk_len > 1000:
                mode = "precise"
            elif chunk_len > 500:
                mode = "balanced"
            else:
                mode = "fast"
            
            # 生成向量
            vector = asyncio.run(generate_vector(chunk, mode=mode))
            vectors.append(vector)
            
            # 更新子进度
            if i % max(1, len(chunks) // 10) == 0:
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': 2 + (i / len(chunks)),
                        'total': 4,
                        'stage': '向量生成中',
                        'progress': 50 + (i / len(chunks)) * 25,
                        'details': f"已生成 {i+1}/{len(chunks)} 个向量"
                    }
                )
        
        # 8. 更新任务进度（75%）
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 3,
                'total': 4,
                'stage': '向量生成完成',
                'progress': 75,
                'details': f"已生成 {len(vectors)} 个向量"
            }
        )
        
        # 9. 存储到数据库
        file_name = os.path.basename(file_path)
        with self.db_session as session:
            # 更新或创建文档记录
            document = session.get(Document, doc_id)
            if not document:
                document = Document(
                    id=doc_id,
                    title=file_name,
                    content=content[:10000] + "..." if len(content) > 10000 else content,
                    embedding=vectors[0] if vectors else None,
                    user_id=user_id
                )
                session.add(document)
            else:
                document.title = file_name
                document.content = content[:10000] + "..." if len(content) > 10000 else content
                document.embedding = vectors[0] if vectors else None
            
            session.commit()
            
            # 记录向量化结果
            logger.info(f"✅ 文档 {doc_id} 向量化完成，存储 {len(vectors)} 个向量")
            
            # 10. 清理临时文件
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"🗑️ 已清理临时文件: {file_path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
            
            # 11. 最终进度更新
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 4,
                    'total': 4,
                    'stage': '存储完成',
                    'progress': 100,
                    'details': f"文档已成功存储，ID: {doc_id}"
                }
            )
            
            return {
                "status": "completed",
                "doc_id": doc_id,
                "title": file_name,
                "chunks_count": len(chunks),
                "vectors_count": len(vectors),
                "content_length": len(content),
                "task_id": task_id
            }
    
    except Exception as e:
        logger.error(f"❌ 文档处理失败: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)

def _process_pdf(file_path: str) -> tuple[str, int]:
    """处理 PDF 文件"""
    try:
        import PyPDF2
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            content = ""
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                content += page.extract_text() + "\n\n"
                
                # 每处理10页记录一次进度
                if page_num % 10 == 0:
                    logger.debug(f"📄 已处理 {page_num+1}/{total_pages} 页")
            
            logger.info(f"✅ PDF 解析完成: {total_pages} 页")
            return content, total_pages
            
    except ImportError:
        raise ImportError("请安装 PyPDF2: pip install PyPDF2")
    except Exception as e:
        raise Exception(f"PDF 处理失败: {e}")

def _process_docx(file_path: str) -> tuple[str, int]:
    """处理 DOCX 文件"""
    try:
        import docx
        
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        content = "\n".join(paragraphs)
        logger.info(f"✅ DOCX 解析完成: {len(paragraphs)} 段落")
        
        return content, len(paragraphs)
        
    except ImportError:
        raise ImportError("请安装 python-docx: pip install python-docx")
    except Exception as e:
        raise Exception(f"DOCX 处理失败: {e}")

def _process_text(file_path: str) -> tuple[str, int]:
    """处理文本文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        lines = content.count('\n') + 1
        logger.info(f"✅ 文本文件解析完成: {lines} 行")
        
        return content, lines
        
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as file:
                content = file.read()
                
            lines = content.count('\n') + 1
            logger.info(f"✅ 文本文件解析完成 (GBK编码): {lines} 行")
            
            return content, lines
        except:
            raise Exception("文件编码无法识别")
    except Exception as e:
        raise Exception(f"文本文件处理失败: {e}")

def _split_into_chunks(text: str, max_chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    """将文本分割为重叠的块"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chunk_size
        
        # 如果不在段落边界，向前找合适的边界
        if end < len(text):
            # 尝试在段落边界分割
            paragraph_end = text.find('\n\n', start + int(max_chunk_size * 0.8))
            if paragraph_end != -1 and paragraph_end < end + 500:
                end = paragraph_end
        
        chunk = text[start:end]
        chunks.append(chunk)
        
        # 重叠滑动
        start = end - overlap
        
        # 防止无限循环
        if start >= len(text) - 100:
            break
    
    return chunks

# 其他任务：批量向量化
@celery_app.task(bind=True, base=BaseTaskWithDB, name="tasks.document_tasks.batch_process_documents")
def batch_process_documents(self, file_paths: list[str], user_id: int = None):
    """批量处理多个文档"""
    task_id = self.request.id
    logger.info(f"🚀 开始批量处理 {len(file_paths)} 个文档，任务ID: {task_id}")
    
    results = []
    for i, file_path in enumerate(file_paths):
        try:
            # 为每个文档创建一个子任务
            sub_task = process_large_document.apply_async(
                args=[file_path, i + 1000, user_id],  # 使用临时ID
                queue="documents"
            )
            
            results.append({
                "file_path": file_path,
                "task_id": sub_task.id,
                "status": "queued"
            })
            
            # 更新进度
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': len(file_paths),
                    'stage': '任务分发中',
                    'progress': (i + 1) / len(file_paths) * 100,
                    'details': f"已分发 {i+1}/{len(file_paths)} 个任务"
                }
            )
            
        except Exception as e:
            logger.error(f"分发任务失败: {file_path} - {e}")
            results.append({
                "file_path": file_path,
                "error": str(e),
                "status": "failed"
            })
    
    return {
        "status": "completed",
        "total_tasks": len(file_paths),
        "results": results,
        "task_id": task_id
    }