from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlmodel import Session
from database import get_session
from models import Document
from services.embedding import generate_vector
import uvicorn

app = FastAPI()

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...), 
    db: Session = Depends(get_session)
):
    # 1. 读取文件内容
    try:
        content = await file.read()
        text_content = content.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="只支持 UTF-8 编码的文本文件")

    # 2. 生成向量 (AI 核心步骤)
    vector = await generate_vector(text_content)

    # 3. 存储到 PostgreSQL 17
    new_doc = Document(
        title=file.filename,
        content=text_content,
        embedding=vector  # 存入我们之前定义的 Vector 字段
    )
    
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    return {"message": "上传成功", "document_id": new_doc.id}

if __name__ == "__main__":
    # 使用 uv 运行时的极速模式
    uvicorn.run(app, host="0.0.0.0", port=8000)