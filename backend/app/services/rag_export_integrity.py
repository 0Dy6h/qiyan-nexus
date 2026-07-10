import hashlib
import hmac
import json
import secrets
from collections.abc import Mapping
from typing import Any

from app.schemas.rag import RagAnswerResponse

# Process-local by design for the current single-process preview profile. A
# restart invalidates old export payloads instead of accepting unsigned or
# client-modified reviewer artifacts.
_EXPORT_SIGNING_KEY = secrets.token_bytes(32)


def _canonical_answer_payload(answer: RagAnswerResponse | Mapping[str, Any]) -> bytes:
    if isinstance(answer, RagAnswerResponse):
        payload = answer.model_dump(mode="json", exclude={"integrity_token"})
    else:
        payload = {key: value for key, value in answer.items() if key != "integrity_token"}
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def attach_export_integrity(answer: RagAnswerResponse) -> RagAnswerResponse:
    token = hmac.new(
        _EXPORT_SIGNING_KEY,
        _canonical_answer_payload(answer),
        hashlib.sha256,
    ).hexdigest()
    return answer.model_copy(update={"integrity_token": token})


def has_valid_export_integrity(answer: RagAnswerResponse | Mapping[str, Any]) -> bool:
    token = (
        answer.integrity_token
        if isinstance(answer, RagAnswerResponse)
        else answer.get("integrity_token")
    )
    if not isinstance(token, str) or not token:
        return False
    expected = hmac.new(
        _EXPORT_SIGNING_KEY,
        _canonical_answer_payload(answer),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(token, expected)
