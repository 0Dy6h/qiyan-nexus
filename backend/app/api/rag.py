from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError

from app.schemas.rag import RagAnswerRequest, RagAnswerResponse
from app.services.rag import answer_question, build_answer_markdown
from app.services.rag_docx import build_answer_docx
from app.services.rag_export_integrity import has_valid_export_integrity

router = APIRouter(prefix="/api/rag", tags=["rag"])

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
EXPORT_INTEGRITY_ERROR = "RAG answer export integrity check failed"


@router.post("/answer", response_model=RagAnswerResponse)
def answer_question_endpoint(
    request_body: RagAnswerRequest,
    request: Request,
) -> RagAnswerResponse:
    request_id = getattr(request.state, "request_id", None)
    return answer_question(
        request_body.question,
        source=request_body.source,
        top_k=request_body.top_k,
        request_id=request_id,
    )


@router.post("/answer/export", response_class=PlainTextResponse)
def export_answer_markdown_endpoint(
    payload: dict[str, Any] = Body(),
) -> PlainTextResponse:
    answer = _validated_export_answer(payload)
    markdown = build_answer_markdown(answer)
    return PlainTextResponse(content=markdown, media_type="text/plain; charset=utf-8")


@router.post("/answer/export/docx")
def export_answer_docx_endpoint(
    payload: dict[str, Any] = Body(),
) -> Response:
    answer = _validated_export_answer(payload)
    docx_bytes = build_answer_docx(answer)
    return Response(content=docx_bytes, media_type=DOCX_MEDIA_TYPE)


def _validated_export_answer(payload: dict[str, Any]) -> RagAnswerResponse:
    has_integrity_token = isinstance(payload.get("integrity_token"), str)
    if has_integrity_token and not has_valid_export_integrity(payload):
        raise HTTPException(status_code=409, detail=EXPORT_INTEGRITY_ERROR)
    try:
        answer = RagAnswerResponse.model_validate(payload)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    if not has_valid_export_integrity(payload):
        raise HTTPException(status_code=409, detail=EXPORT_INTEGRITY_ERROR)
    return answer
