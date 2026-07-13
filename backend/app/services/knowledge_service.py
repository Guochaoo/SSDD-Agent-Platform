"""
知识库服务层（RAG）
处理知识文档的入库、分块落库、向量相似度检索
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.entity.db_models import KnowledgeDocument, KnowledgeChunk


class KnowledgeService:
    """知识库服务"""

    @staticmethod
    def create_document(
        db: Session,
        user_id: int | None,
        title: str,
        filename: str,
        file_url: str,
        file_type: str | None = None,
    ) -> KnowledgeDocument:
        """创建知识文档记录（原文件已上传至 MinIO 之后调用）"""
        doc = KnowledgeDocument(
            user_id=user_id,
            title=title,
            filename=filename,
            file_url=file_url,
            file_type=file_type,
            status="processing",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def get_document(db: Session, document_id: int) -> KnowledgeDocument:
        """根据 ID 获取知识文档"""
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="知识文档不存在")
        return doc

    @staticmethod
    def list_documents(db: Session, status: str | None = None) -> list[KnowledgeDocument]:
        """列出知识文档，可按处理状态筛选"""
        query = db.query(KnowledgeDocument)
        if status:
            query = query.filter(KnowledgeDocument.status == status)
        return query.order_by(KnowledgeDocument.created_at.desc()).all()

    @staticmethod
    def add_chunks(db: Session, document_id: int, chunks: list[dict]) -> list[KnowledgeChunk]:
        """
        chunks 形如 [{"chunk_index": 0, "content": "...", "embedding": [...], "token_count": 120}, ...]
        调用方需要先完成文本切分和 embedding 计算，这里只负责落库并把文档状态置为 indexed。
        """
        objs = [KnowledgeChunk(document_id=document_id, **c) for c in chunks]
        db.add_all(objs)

        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        if doc:
            doc.chunk_count = len(objs)
            doc.status = "indexed"

        db.commit()
        for o in objs:
            db.refresh(o)
        return objs

    @staticmethod
    def search_similar_chunks(
        db: Session,
        query_embedding: list[float],
        top_k: int = 5,
        document_id: int | None = None,
    ) -> list[KnowledgeChunk]:
        """RAG 检索：按余弦距离取最相似的 top_k 个分块，供 Agent 回答问题时引用"""
        query = db.query(KnowledgeChunk).order_by(
            KnowledgeChunk.embedding.cosine_distance(query_embedding)
        )
        if document_id:
            query = query.filter(KnowledgeChunk.document_id == document_id)
        return query.limit(top_k).all()

    @staticmethod
    def delete_document(db: Session, document_id: int) -> None:
        """knowledge_chunks 由数据库 ON DELETE CASCADE 自动清除，这里只需删文档本身
        （MinIO 原文件清理请在路由层调用 MinIOClient().delete_file() 后再调这个方法）"""
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        if doc:
            db.delete(doc)
            db.commit()


# 全局单例
knowledge_service = KnowledgeService()
