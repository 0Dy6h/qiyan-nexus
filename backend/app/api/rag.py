from fastapi import APIRouter, Body, Request
from fastapi.responses import PlainTextResponse

from app.schemas.rag import RagAnswerRequest, RagAnswerResponse
from app.services.rag import answer_question, build_answer_markdown

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/answer", response_model=RagAnswerResponse)
def answer_question_endpoint(
    request_body: RagAnswerRequest,
    request: Request,
) -> RagAnswerResponse:
    # Extract request_id from middleware if available
    request_id = getattr(request.state, "request_id", None)
    return answer_question(
        request_body.question,
        source=request_body.source,
        top_k=request_body.top_k,
        request_id=request_id,
    )


@router.post("/answer/export", response_class=PlainTextResponse)
def export_answer_markdown_endpoint(
    answer: RagAnswerResponse = Body(),
) -> PlainTextResponse:
    markdown = build_answer_markdown(answer)
    return PlainTextResponse(content=markdown, media_type="text/plain; charset=utf-8")
