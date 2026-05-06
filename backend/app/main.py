from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.literature import router as literature_router

app = FastAPI(title="Tcm Tech API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(literature_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "tcm-tech-api",
    }
