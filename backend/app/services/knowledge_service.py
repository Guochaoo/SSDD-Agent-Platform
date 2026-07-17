"""
知识库服务层（RAG）
处理知识文档的入库、分块落库、向量相似度检索

权限边界原则（对应后续分工文档"数据库权限边界隔离"要求）：
  - user_id 为 NULL 的文档视为系统内置文档，所有登录用户可读，但只有管理员可删/改
  - 非管理员用户只能读取"自己上传的文档 + 系统文档"，看不到别人上传的私有资料
  - 向量检索（search_similar_chunks）同样按上述可见范围过滤，避免通过 RAG
    问答间接泄露别人上传的私有文档内容
"""

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.entity.db_models import KnowledgeChunk, KnowledgeDocument
from app.storage.minio_client import MinIOClient


class KnowledgeService:
    """知识库服务"""

    # ── 创建 ─────────────────────────────────────────────

    @staticmethod
    def create_document(
        db: Session,
        user_id: int | None,
        title: str,
        filename: str,
        file_url: str,
        file_type: str | None = None,
    ) -> KnowledgeDocument:
        """创建知识文档记录（原文件已上传至 MinIO 之后调用）。
        user_id=None 表示系统内置文档，只能由管理员触发（由路由层校验 is_superuser 后传入）。"""
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
    def add_chunks(db: Session, document_id: int, chunks: list[dict]) -> list[KnowledgeChunk]:
        """
        chunks 形如 [{"chunk_index": 0, "content": "...", "embedding": [...], "token_count": 120}, ...]
        调用方需要先完成文本切分和 embedding 计算，这里只负责落库并把文档状态置为 indexed。
        """
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="知识文档不存在")

        objs = [KnowledgeChunk(document_id=document_id, **c) for c in chunks]
        db.add_all(objs)
        doc.chunk_count = len(objs)
        doc.status = "indexed" if objs else "failed"

        db.commit()
        for o in objs:
            db.refresh(o)
        return objs

    @staticmethod
    def mark_failed(db: Session, document_id: int) -> None:
        """文本提取/切分/向量化失败时调用，避免文档卡在 processing 状态"""
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        if doc:
            doc.status = "failed"
            db.commit()

    # ── 查询（带权限边界） ────────────────────────────────

    @staticmethod
    def _visibility_filter(query, user_id: int, is_superuser: bool):
        """非管理员只能看到：自己的文档 + 系统内置文档（user_id IS NULL）"""
        if is_superuser:
            return query
        return query.filter(
            or_(KnowledgeDocument.user_id == user_id, KnowledgeDocument.user_id.is_(None))
        )

    @staticmethod
    def get_document(
        db: Session, document_id: int, user_id: int, is_superuser: bool = False
    ) -> KnowledgeDocument:
        """根据 ID 获取知识文档，非管理员只能访问自己的文档或系统文档"""
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="知识文档不存在")
        if not is_superuser and doc.user_id is not None and doc.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权访问该文档")
        return doc

    @staticmethod
    def list_documents(
        db: Session,
        user_id: int,
        is_superuser: bool = False,
        status: str | None = None,
    ) -> list[KnowledgeDocument]:
        """列出知识文档，可按处理状态筛选；非管理员只能看到自己的文档 + 系统文档"""
        query = db.query(KnowledgeDocument)
        query = KnowledgeService._visibility_filter(query, user_id, is_superuser)
        if status:
            query = query.filter(KnowledgeDocument.status == status)
        return query.order_by(KnowledgeDocument.created_at.desc()).all()

    @staticmethod
    def search_similar_chunks(
        db: Session,
        query_embedding: list[float],
        user_id: int,
        is_superuser: bool = False,
        top_k: int = 5,
        document_id: int | None = None,
    ) -> list[KnowledgeChunk]:
        """RAG 检索：按余弦距离取最相似的 top_k 个分块，供 Agent 回答问题时引用。
        只在当前用户可见的文档范围内检索（自己的 + 系统内置的，管理员不受限）。"""
        query = (
            db.query(KnowledgeChunk)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .filter(KnowledgeDocument.status == "indexed")
        )
        if not is_superuser:
            query = query.filter(
                or_(KnowledgeDocument.user_id == user_id, KnowledgeDocument.user_id.is_(None))
            )
        if document_id:
            # 显式指定 document_id 时也要过一遍权限边界，防止越权拼接一篇不可见的文档 ID
            KnowledgeService.get_document(db, document_id, user_id, is_superuser)
            query = query.filter(KnowledgeChunk.document_id == document_id)

        query = query.order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
        return query.limit(top_k).all()

    # ── 删除 ─────────────────────────────────────────────

    @staticmethod
    def delete_document(
        db: Session, document_id: int, user_id: int, is_superuser: bool = False
    ) -> None:
        """删除知识文档：非管理员只能删自己上传的文档，系统内置文档只有管理员能删。
        knowledge_chunks 由数据库 ON DELETE CASCADE 自动清除；这里同时清理 MinIO 原文件，
        MinIO 清理失败不阻断数据库删除（策略与 history_service.delete_task 保持一致）。"""
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="知识文档不存在")
        if not is_superuser and doc.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权删除该文档")

        try:
            MinIOClient().delete_by_url(doc.file_url)
        except Exception:
            pass

        db.delete(doc)
        db.commit()


# 全局单例
knowledge_service = KnowledgeService()
