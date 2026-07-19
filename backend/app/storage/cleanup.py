"""Durable object-cleanup compensation, invoked by the API lifecycle."""
import logging

from sqlalchemy.orm import Session

from app.entity.db_models import DetectionResult, DetectionTask, KnowledgeDocument, ModelVersion
from app.services.scene_service import SceneService
from app.storage.minio_client import MinIOClient

logger = logging.getLogger(__name__)


def retry_pending_cleanups(db: Session, limit: int = 100) -> dict:
    client = None

    def storage_client() -> MinIOClient:
        nonlocal client
        if client is None:
            client = MinIOClient()
        return client

    models = db.query(ModelVersion).filter(ModelVersion.cleanup_pending.is_(True)).limit(limit).all()
    documents = db.query(KnowledgeDocument).filter(KnowledgeDocument.cleanup_pending.is_(True)).limit(limit).all()
    results = db.query(DetectionResult).filter(DetectionResult.cleanup_pending.is_(True)).limit(limit).all()
    attempted = succeeded = 0

    for model in models:
        attempted += 1
        errors = SceneService._cleanup_model_files(model)
        if not errors:
            model.cleanup_pending = False
            model.cleanup_error = None
            succeeded += 1
        else:
            model.cleanup_retry_count = (model.cleanup_retry_count or 0) + 1
            model.cleanup_error = "; ".join(errors)
            logger.warning("pending model cleanup failed model_id=%s errors=%s", model.id, model.cleanup_error)

    for document in documents:
        try:
            attempted += 1
            if document.object_key:
                storage_client().delete_file(document.object_key)
            elif document.file_url:
                storage_client().delete_by_url(document.file_url)
            document.cleanup_pending = False
            document.cleanup_error = None
            db.delete(document)
            succeeded += 1
        except Exception as exc:
            document.cleanup_retry_count = (document.cleanup_retry_count or 0) + 1
            document.cleanup_error = str(exc)
            logger.exception("pending document cleanup failed key=%s", document.object_key)

    task_ids = set()
    for result in results:
        task_ids.add(result.task_id)
        failed = False
        for key, legacy_url in (
            (result.original_object_key, result.image_path),
            (result.annotated_object_key, result.annotated_image_url),
        ):
            if not key and not legacy_url:
                continue
            attempted += 1
            try:
                if key:
                    storage_client().delete_file(key)
                else:
                    storage_client().delete_by_url(legacy_url)
                succeeded += 1
            except Exception as exc:
                failed = True
                result.cleanup_retry_count = (result.cleanup_retry_count or 0) + 1
                result.cleanup_error = str(exc)
                logger.exception("pending detection result cleanup failed key=%s url=%s", key, legacy_url)
        if not failed:
            result.cleanup_pending = False
            result.cleanup_error = None

    for task_id in task_ids:
        task = db.get(DetectionTask, task_id)
        if task and all(not item.cleanup_pending for item in task.results):
            db.delete(task)
    db.commit()
    return {"attempted": attempted, "succeeded": succeeded}


def find_orphan_objects(db: Session, prefix: str = "") -> list[str]:
    """Report objects not referenced by stable object keys; never delete them automatically."""
    client = MinIOClient()
    referenced = set()
    for model in db.query(ModelVersion.object_key).filter(ModelVersion.object_key.isnot(None)):
        referenced.add(model[0])
    for document in db.query(KnowledgeDocument.object_key).filter(KnowledgeDocument.object_key.isnot(None)):
        referenced.add(document[0])
    for result in db.query(DetectionResult.original_object_key, DetectionResult.annotated_object_key):
        referenced.update(key for key in result if key)
    return [item.object_name for item in client.list_objects(prefix) if item.object_name not in referenced]
