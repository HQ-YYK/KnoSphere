from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from contextlib import asynccontextmanager
from sqlmodel import Session, text
from typing import List
import os

# 数据库和模型导入
from database import init_db, engine, get_session
from models import User, Document
from services.embedding import generate_vector

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("🚀 启动 KnoSphere API...")
    with engine.connect() as conn:
        # 激活向量扩展，这是 2026 年 RAG 系统的核心
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    init_db()  # 这会创建所有表，包括 User 和 Document
    print("✅ 数据库初始化完成")
    yield
    # 关闭时执行（如果需要清理资源）
    print("👋 关闭 KnoSphere API...")

app = FastAPI(
    title="KnoSphere API",
    description="2026 企业级智能知识库系统",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "欢迎使用 KnoSphere API - 2026 企业级智能知识库系统"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "KnoSphere API"}

@app.get("/documents")
async def list_documents(
    db: Session = Depends(get_session),
    limit: int = 10,
    offset: int = 0
):
    """获取文档列表"""
    documents = db.query(Document).offset(offset).limit(limit).all()
    return {
        "total": db.query(Document).count(),
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "created_at": doc.created_at,
                "content_preview": doc.content[:100] + "..." if len(doc.content) > 100 else doc.content
            }
            for doc in documents
        ]
    }

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...), 
    db: Session = Depends(get_session)
):
    """
    上传文档并生成向量
    支持格式：.txt, .md, .pdf, .docx
    """
    # 1. 验证文件类型
    allowed_extensions = {'.txt', '.md', '.pdf', '.docx'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式。支持格式: {', '.join(allowed_extensions)}"
        )
    
    # 2. 读取文件内容
    try:
        content = await file.read()
        
        # 处理不同文件类型
        if file_ext == '.pdf':
            # PDF 处理 - 需要额外的依赖
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text()
            except ImportError:
                # 如果未安装 PyPDF2，提示安装
                raise HTTPException(
                    status_code=400,
                    detail="PDF 处理需要安装 PyPDF2。请运行: uv add PyPDF2"
                )
        elif file_ext == '.docx':
            # DOCX 处理
            try:
                import docx
                doc = docx.Document(io.BytesIO(content))
                text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                raise HTTPException(
                    status_code=400,
                    detail="DOCX 处理需要安装 python-docx。请运行: uv add python-docx"
                )
        else:
            # 文本文件处理
            text_content = content.decode("utf-8")
            
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用 UTF-8 编码")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件读取失败: {str(e)}")

    # 3. 检查文本长度
    if len(text_content.strip()) == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")
    
    # 4. 生成向量 (AI 核心步骤)
    try:
        vector = await generate_vector(text_content)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"向量生成失败: {str(e)}。请检查 OPENAI_API_KEY 环境变量"
        )

    # 5. 存储到 PostgreSQL 17
    try:
        new_doc = Document(
            title=file.filename,
            content=text_content,
            embedding=vector  # 存入我们之前定义的 Vector 字段
        )
        
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        
        return {
            "message": "上传成功", 
            "document_id": new_doc.id,
            "title": new_doc.title,
            "vector_dimensions": len(vector) if vector else 0,
            "content_length": len(text_content)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库存储失败: {str(e)}")

# 添加缺失的导入
import io

# 如果需要添加更多文件格式处理，可以取消下面的注释并安装相应依赖
# @app.on_event("startup")
# async def check_dependencies():
#     """检查可选依赖"""
#     try:
#         import PyPDF2
#         print("✅ PyPDF2 已安装，支持 PDF 处理")
#     except ImportError:
#         print("⚠️  PyPDF2 未安装，PDF 文件处理将不可用")
#     
#     try:
#         import docx
#         print("✅ python-docx 已安装，支持 DOCX 处理")
#     except ImportError:
#         print("⚠️  python-docx 未安装，DOCX 文件处理将不可用")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
    )