from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import get_logger


logger = get_logger(__name__)
_SENSITIVE_FIELD_TOKENS = ("password", "token", "secret", "api_key", "authorization")


def resource_detail(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _error_context(request: Request) -> dict:
    return {"path": request.url.path, "request_id": getattr(request.state, "request_id", None)}


def _safe_validation_errors(errors: list[dict]) -> list[dict]:
    """Keep validation diagnostics useful without returning submitted secrets."""
    safe_errors = []
    for error in errors:
        safe_error = dict(error)
        location = safe_error.get("loc", ())
        if any(
            isinstance(part, str) and any(token in part.lower() for token in _SENSITIVE_FIELD_TOKENS)
            for part in location
        ):
            safe_error["input"] = "[redacted]"
        safe_errors.append(safe_error)
    return safe_errors


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = _safe_validation_errors(exc.errors())
        logger.warning("Validation error: %s %s %s", request.method, request.url.path, errors)
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "detail": errors,
                **_error_context(request),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning("HTTP error: %s %s status=%s detail=%s", request.method, request.url.path, exc.status_code, exc.detail)
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": f"HTTP_{exc.status_code}", "message": exc.detail}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "error_code": detail.get("code"),
                "message": detail.get("message"),
                "detail": detail,
                **_error_context(request),
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning("HTTP error: %s %s status=%s detail=%s", request.method, request.url.path, exc.status_code, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "error_code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "detail": {"code": f"HTTP_{exc.status_code}", "message": exc.detail},
                **_error_context(request),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "error_code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "detail": {"code": "INTERNAL_ERROR", "message": "Internal server error"},
                **_error_context(request),
            },
        )
