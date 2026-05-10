from fastapi import APIRouter, HTTPException

from app.services.eval import get_rag_eval_questions, run_rag_ad_eval_report

router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.get("/rag-ad")
def rag_ad_eval_questions() -> dict[str, list[dict]]:
    return {"items": get_rag_eval_questions()}


@router.get("/rag-ad/report")
def rag_ad_eval_report() -> dict:
    try:
        return run_rag_ad_eval_report()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="RAG eval report unavailable") from exc
