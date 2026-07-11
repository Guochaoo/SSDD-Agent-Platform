import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logger import get_logger


logger = get_logger(__name__)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            status_code = response.status_code if response is not None else 500
            logger.info(
                "%s %s status=%s duration=%.2fms client=%s",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
                request.client.host if request.client else "-",
            )
