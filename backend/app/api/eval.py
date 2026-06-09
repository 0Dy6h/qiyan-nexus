from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas.eval import EvalCorpus
from app.services.eval import get_rag_eval_questions, run_rag_ad_eval_report

router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.get("/rag-ad")
def rag_ad_eval_questions() -> dict[str, list[dict[str, Any]]]:
    return {"items": get_rag_eval_questions()}


@router.get("/rag-ad/report")
def rag_ad_eval_report(
    strategy: str | None = Query(default=None, pattern="^(keyword|vector|hybrid)$"),
    corpus: EvalCorpus = Query(default="seed"),
) -> dict[str, Any]:
    try:
        return run_rag_ad_eval_report(strategy=strategy, corpus=corpus)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="RAG eval report unavailable") from exc
