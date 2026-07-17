"""轻量对象清理补偿；由定时器或管理命令按需调用，不引入队列架构。"""
import logging
from sqlalchemy.orm import Session
from app.entity.db_models import ModelVersion, KnowledgeDocument, DetectionResult
from app.storage.minio_client import MinIOClient

logger = logging.getLogger(__name__)

def retry_pending_cleanups(db: Session, limit: int = 100) -> dict:
    client = MinIOClient()
    pending = []
    for model in db.query(ModelVersion).filter(ModelVersion.cleanup_pending.is_(True)).limit(limit).all():
        pending.append((model, model.object_key))
    for doc in db.query(KnowledgeDocument).filter(KnowledgeDocument.cleanup_pending.is_(True)).limit(limit).all():
        pending.append((doc, doc.object_key))
    for result in db.query(DetectionResult).filter(DetectionResult.cleanup_pending.is_(True)).limit(limit).all():
        pending.append((result, result.original_object_key))
        pending.append((result, result.annotated_object_key))
    succeeded = 0
    for record, key in pending:
        if not key:
            record.cleanup_pending = False
            continue
        try:
            client.delete_file(key)
            record.cleanup_pending = False
            record.cleanup_error = None
            succeeded += 1
        except Exception as exc:
            record.cleanup_retry_count = (record.cleanup_retry_count or 0) + 1
            record.cleanup_error = str(exc)
            logger.exception("pending object cleanup failed key=%s", key)
    db.commit()
    return {"attempted": len(pending), "succeeded": succeeded}

def find_orphan_objects(db: Session, prefix: str = "") -> list[str]:
    """返回 MinIO 中不再被稳定 object_key 引用的对象；只报告，不自动删除。"""
    client = MinIOClient()
    referenced = set()
    for model in db.query(ModelVersion.object_key).filter(ModelVersion.object_key.isnot(None)):
        referenced.add(model[0])
    for doc in db.query(KnowledgeDocument.object_key).filter(KnowledgeDocument.object_key.isnot(None)):
        referenced.add(doc[0])
    for result in db.query(DetectionResult.original_object_key, DetectionResult.annotated_object_key):
        referenced.update(key for key in result if key)
    return [item.object_name for item in client.list_objects(prefix) if item.object_name not in referenced]
