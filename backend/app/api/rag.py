from fastapi import APIRouter, Body

from app.schemas.rag import RagAnswerRequest, RagAnswerResponse
from app.services.rag import answer_question

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/answer", response_model=RagAnswerResponse)
def answer_question_endpoint(
    request: RagAnswerRequest = Body(),
) -> RagAnswerResponse:
    return answer_question(request.question)
