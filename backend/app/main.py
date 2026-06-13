import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.eval import router as eval_router
from app.api.literature import router as literature_router
from app.api.network import router as network_router
from app.api.rag import router as rag_router
from app.api.upload import router as upload_router
from app.core.access_control import install_access_token_middleware
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Maximum request body size: 50MB (prevents DoS via large payloads)
MAX_REQUEST_SIZE = 50 * 1024 * 1024

app = FastAPI(title="Qiyan Nexus API")


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies larger than MAX_REQUEST_SIZE to prevent DoS."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"请求体过大，最大允许 {MAX_REQUEST_SIZE // 1024 // 1024}MB"
                    },
                )
        return await call_next(request)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions to avoid leaking stack traces.

    Logs the full exception for debugging while returning a safe error to clients.
    In development, returns detailed error information for easier debugging.
    """
    # Log the full exception with stack trace for troubleshooting
    logger.exception(
        "Unhandled exception during %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )

    settings = get_settings()

    # In development, return detailed error information
    if settings.environment == "dev":
        return JSONResponse(
            status_code=500,
            content={
                "detail": "内部错误",
                "error": str(exc),
                "type": type(exc).__name__,
            },
        )

    # In production, return generic message
    return JSONResponse(
        status_code=500,
        content={"detail": "内部错误，请稍后重试。"},
    )


# Order matters: Starlette installs middleware via `insert(0, ...)` and builds
# the stack with `reversed(middleware)`, so the LAST one added is OUTERMOST.
# We want CORS outermost so that 401 responses from the access-control middleware
# still carry Access-Control-Allow-Origin headers for browser callers.
# Request size limit is added after access control to reject large bodies early.
install_access_token_middleware(app)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(literature_router)
app.include_router(rag_router)
app.include_router(eval_router)
app.include_router(upload_router)
app.include_router(network_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "qiyan-nexus-api",
    }
