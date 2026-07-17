"""
RAG 知识库 API 路由
- POST   /api/knowledge/documents           上传知识文档（提取文本 → 分块 → 向量化 → 落库）
- GET    /api/knowledge/documents           列出知识文档（非管理员只看自己的 + 系统内置）
- GET    /api/knowledge/documents/{id}      文档详情（含分块列表，不含向量本身）
- DELETE /api/knowledge/documents/{id}      删除文档（非管理员只能删自己的）
- POST   /api/knowledge/search              RAG 相似度检索

权限边界：所有接口都要求登录；文档级别的可见/删除权限由 knowledge_service 统一把关，
避免在多个路由里重复写、写漏。
"""
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import (
    KnowledgeChunkResponse,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
)
from app.services.document_parser import chunk_text, extract_text, guess_file_type
from app.services.embedding_service import embedding_service
from app.services.knowledge_service import knowledge_service
from app.storage.minio_client import MinIOClient

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024


@router.post("/documents", response_model=KnowledgeDocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    is_system: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传知识文档：txt/md/pdf/docx。
    is_system=True 表示登记为系统内置文档（对所有用户可读，只能被管理员删除），
    只有管理员可以传 True，否则忽略并按普通私有文档处理。
    """
    filename = file.filename or "untitled"
    file_type = guess_file_type(filename)

    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="文档不能为空")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="文档大小不能超过 20MB")

    owner_id = None if (is_system and current_user.is_superuser) else current_user.id

    object_name = f"knowledge/{owner_id or 'system'}/{uuid4().hex}/{filename}"
    file_url = MinIOClient().upload_bytes(object_name, content, file.content_type or "application/octet-stream")

    doc = knowledge_service.create_document(
        db,
        user_id=owner_id,
        title=(title or filename).strip() or filename,
        filename=filename,
        file_url=file_url,
        file_type=file_type,
    )

    try:
        text = extract_text(filename, content)
        pieces = chunk_text(text)
        if not pieces:
            raise HTTPException(status_code=400, detail="文档解析结果为空，无法建立索引")

        vectors = embedding_service.embed_batch(pieces)
        chunks = [
            {"chunk_index": i, "content": piece, "embedding": vector, "token_count": len(piece)}
            for i, (piece, vector) in enumerate(zip(pieces, vectors))
        ]
        knowledge_service.add_chunks(db, doc.id, chunks)
        db.refresh(doc)
    except HTTPException:
        knowledge_service.mark_failed(db, doc.id)
        raise
    except Exception as exc:
        knowledge_service.mark_failed(db, doc.id)
        raise HTTPException(status_code=500, detail=f"知识文档索引失败: {exc}") from exc

    return doc


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
def list_documents(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出可见的知识文档：自己上传的 + 系统内置的；管理员可看到全部"""
    return knowledge_service.list_documents(
        db, user_id=current_user.id, is_superuser=current_user.is_superuser, status=status
    )


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return knowledge_service.get_document(
        db, document_id, user_id=current_user.id, is_superuser=current_user.is_superuser
    )


@router.get("/documents/{document_id}/chunks", response_model=list[KnowledgeChunkResponse])
def list_document_chunks(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看某篇文档切分出的分块原文（不返回向量本身）"""
    doc = knowledge_service.get_document(
        db, document_id, user_id=current_user.id, is_superuser=current_user.is_superuser
    )
    return sorted(doc.chunks, key=lambda c: c.chunk_index)


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    knowledge_service.delete_document(
        db, document_id, user_id=current_user.id, is_superuser=current_user.is_superuser
    )
    return {"message": "知识文档已删除"}


@router.post("/search", response_model=list[KnowledgeChunkResponse])
def search_knowledge(
    payload: KnowledgeSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """RAG 相似度检索：把 query 转成向量后取最相似的 top_k 个分块，检索范围受权限边界约束"""
    query_embedding = embedding_service.embed_text(payload.query)
    return knowledge_service.search_similar_chunks(
        db,
        query_embedding=query_embedding,
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
        top_k=payload.top_k,
        document_id=payload.document_id,
    )
