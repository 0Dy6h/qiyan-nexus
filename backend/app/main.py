from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.eval import router as eval_router
from app.api.literature import router as literature_router
from app.api.network import router as network_router
from app.api.rag import router as rag_router
from app.api.upload import router as upload_router
from app.core.access_control import install_access_token_middleware

app = FastAPI(title="Qiyan Nexus API")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions to avoid leaking stack traces."""
    return JSONResponse(
        status_code=500,
        content={"detail": "内部错误，请稍后重试。"},
    )


# Order matters: Starlette installs middleware via `insert(0, ...)` and builds
# the stack with `reversed(middleware)`, so the LAST one added is OUTERMOST.
# We want CORS outermost so that 401 responses from the access-control middleware
# still carry Access-Control-Allow-Origin headers for browser callers.
install_access_token_middleware(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
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
