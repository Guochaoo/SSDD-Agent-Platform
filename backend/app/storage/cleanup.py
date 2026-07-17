"""轻量对象清理补偿；由定时器或管理命令按需调用，不引入队列架构。"""
import logging
from sqlalchemy.orm import Session
from app.entity.db_models import DetectionResult, DetectionTask, KnowledgeDocument, ModelVersion
from app.storage.minio_client import MinIOClient

logger = logging.getLogger(__name__)

def retry_pending_cleanups(db: Session, limit: int = 100) -> dict:
    client = MinIOClient()
    models = db.query(ModelVersion).filter(ModelVersion.cleanup_pending.is_(True)).limit(limit).all()
    documents = db.query(KnowledgeDocument).filter(KnowledgeDocument.cleanup_pending.is_(True)).limit(limit).all()
    results = db.query(DetectionResult).filter(DetectionResult.cleanup_pending.is_(True)).limit(limit).all()
    succeeded = 0
    attempted = 0
    for model in models:
        if not model.object_key:
            model.cleanup_pending = False
            continue
        attempted += 1
        try:
            client.delete_file(model.object_key)
            model.cleanup_pending = False
            model.cleanup_error = None
            succeeded += 1
        except Exception as exc:
            model.cleanup_retry_count = (model.cleanup_retry_count or 0) + 1
            model.cleanup_error = str(exc)
            logger.exception("pending model cleanup failed key=%s", model.object_key)

    for document in documents:
        try:
            if document.object_key:
                attempted += 1
                client.delete_file(document.object_key)
                succeeded += 1
            document.cleanup_pending = False
            document.cleanup_error = None
            db.delete(document)
        except Exception as exc:
            document.cleanup_retry_count = (document.cleanup_retry_count or 0) + 1
            document.cleanup_error = str(exc)
            logger.exception("pending document cleanup failed key=%s", document.object_key)

    task_ids = set()
    for result in results:
        task_ids.add(result.task_id)
        failed = False
        for key in (result.original_object_key, result.annotated_object_key):
            if not key:
                continue
            attempted += 1
            try:
                client.delete_file(key)
                succeeded += 1
            except Exception as exc:
                failed = True
                result.cleanup_retry_count = (result.cleanup_retry_count or 0) + 1
                result.cleanup_error = str(exc)
                logger.exception("pending detection result cleanup failed key=%s", key)
        if not failed:
            result.cleanup_pending = False
            result.cleanup_error = None

    # A failed cleanup intentionally keeps the parent task/document row so it
    # can be retried. Finish the deferred database deletion once every result
    # belonging to the task has been cleaned successfully.
    for task_id in task_ids:
        task = db.get(DetectionTask, task_id)
        if task and all(not item.cleanup_pending for item in task.results):
            db.delete(task)
    db.commit()
    return {"attempted": attempted, "succeeded": succeeded}

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
