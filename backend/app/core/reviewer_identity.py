"""Trusted reviewer identity extracted from the reverse-proxy boundary."""

from __future__ import annotations

import re

from fastapi import HTTPException, Request

REVIEWER_ID_HEADER = "X-Qiyan-Reviewer"
REVIEWER_ID_STATE_ATTR = "qiyan_reviewer_id"
LOCAL_REVIEWER_ID = "local-preview"
_REVIEWER_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def normalize_reviewer_id(raw_reviewer_id: str | None) -> str | None:
    """Return a canonical reviewer id, or ``None`` for an invalid value."""

    if raw_reviewer_id is None or not raw_reviewer_id.strip():
        return None
    reviewer_id = raw_reviewer_id.strip()
    if not _REVIEWER_ID_PATTERN.fullmatch(reviewer_id):
        return None
    return reviewer_id


def require_reviewer_id(request: Request) -> str:
    """Return only the reviewer identity trusted by access-control middleware."""

    reviewer_id = getattr(request.state, REVIEWER_ID_STATE_ATTR, None)
    if not isinstance(reviewer_id, str):
        raise HTTPException(
            status_code=401,
            detail="missing or invalid X-Qiyan-Reviewer",
        )
    return reviewer_id
