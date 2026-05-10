from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.eval import router as eval_router
from app.api.literature import router as literature_router
from app.api.network import router as network_router
from app.api.rag import router as rag_router
from app.api.upload import router as upload_router

app = FastAPI(title="Qiyan Nexus API")
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
