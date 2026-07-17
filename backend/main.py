import warnings
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

# Pydantic v2 reserves "model_" prefix; suppress the harmless lint
warnings.filterwarnings("ignore", message='Field "model_id" has conflict')
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.detection import router as detection_router
from app.api.agent import router as agent_router
from app.api.health import router as health_router
from app.api.history import router as history_router
from app.api.knowledge import router as knowledge_router
from app.api.operation_logs import router as operation_logs_router
from app.api.scenes import router as scenes_router
from app.api.training import router as training_router
from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.core.logger import get_logger, setup_logging
from app.database.session import SessionLocal
from app.middleware.request_logger import RequestLogMiddleware
from app.storage.cleanup import retry_pending_cleanups
from app.services.detection_service import detection_service
import asyncio


setup_logging()
logger = get_logger(__name__)


def init_minio():
    try:
        from app.storage.minio_client import MinIOClient

        minio_client = MinIOClient()
        logger.info("MinIO bucket '%s' initialized", minio_client.bucket_name)
    except Exception as exc:
        logger.warning("MinIO initialization failed: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting service")
    init_minio()
    asyncio.create_task(asyncio.to_thread(detection_service.warmup_models))
    cleanup_task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        await asyncio.gather(cleanup_task, return_exceptions=True)
        logger.info("Service stopped")


async def _cleanup_loop():
    """Retry durable object deletions while the API process is running."""
    while True:
        try:
            db = SessionLocal()
            try:
                retry_pending_cleanups(db)
            finally:
                db.close()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Resource cleanup retry failed: %s", exc)
        await asyncio.sleep(settings.CLEANUP_RETRY_INTERVAL_SECONDS)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="YOLOv11 object detection agent platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLogMiddleware)
register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(detection_router)
app.include_router(agent_router)
app.include_router(health_router)
app.include_router(history_router)
app.include_router(operation_logs_router)
app.include_router(scenes_router)
app.include_router(training_router)
app.include_router(knowledge_router)


@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(Path(__file__).parent / "app")],
        reload_excludes=["**/__pycache__/**", "**/*.pyc"],
        reload_delay=0.5,
        ws_ping_interval=20,
        ws_ping_timeout=20,
    )
