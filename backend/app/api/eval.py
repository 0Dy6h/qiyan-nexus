from fastapi import APIRouter

from app.services.eval import get_rag_eval_questions

router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.get("/rag-ad")
def rag_ad_eval_questions() -> dict[str, list[dict]]:
    return {"items": get_rag_eval_questions()}
