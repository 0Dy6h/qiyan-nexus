import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.eval import router as eval_router
from app.api.literature import router as literature_router
from app.api.metrics import router as metrics_router
from app.api.network import router as network_router
from app.api.rag import router as rag_router
from app.api.upload import router as upload_router
from app.core.access_control import install_access_token_middleware
from app.core.logging_config import init_logging
from app.core.logging_middleware import RequestLoggingMiddleware

if "pytest" not in sys.modules:
    init_logging()

app = FastAPI(title="Qiyan Nexus API")
# Order matters: Starlette installs middleware via `insert(0, ...)` and builds
# the stack with `reversed(middleware)`, so the LAST one added is OUTERMOST.
# We want CORS outermost so that 401 responses from the access-control middleware
# still carry Access-Control-Allow-Origin headers for browser callers.
# RequestLoggingMiddleware goes before access control so it captures all requests
# (including 401s) and can log request_id for debugging.
app.add_middleware(RequestLoggingMiddleware)
install_access_token_middleware(app)
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
app.include_router(metrics_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "qiyan-nexus-api",
    }
