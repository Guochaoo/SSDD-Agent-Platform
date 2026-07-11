from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.history import router as history_router
from app.api.scenes import router as scenes_router
from app.api.training import router as training_router
from app.config.settings import settings

try:
    from app.api.health import router as health_router
except ImportError:
    health_router = None
try:
    from app.core.exceptions import register_exception_handlers
except ImportError:
    register_exception_handlers = None
try:
    from app.core.logger import get_logger, setup_logging
except ImportError:
    get_logger = logging.getLogger
    setup_logging = lambda: None
try:
    from app.middleware.request_logger import RequestLogMiddleware
except ImportError:
    RequestLogMiddleware = None

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
    yield
    logger.info("Service stopped")


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
if RequestLogMiddleware is not None:
    app.add_middleware(RequestLogMiddleware)
if register_exception_handlers is not None:
    register_exception_handlers(app)

app.include_router(auth_router)
if health_router is not None:
    app.include_router(health_router)
app.include_router(history_router)
app.include_router(scenes_router)
app.include_router(training_router)


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

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
