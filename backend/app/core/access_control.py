"""X-Access-Token middleware for the Qiyan Nexus API.

A2 minimum access control. ``QIYAN_ACCESS_TOKENS`` is read at app construction
time as a comma-separated allowlist. When the allowlist is empty (dev default)
the middleware does nothing. Otherwise every request that is not ``/health`` or
a CORS preflight (``OPTIONS``) must carry a matching ``X-Access-Token`` header
or receive ``401``.

Token comparison is case-sensitive and whitespace-stripped at parse time.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

ACCESS_TOKEN_HEADER = "X-Access-Token"
ACCESS_TOKENS_ENV = "QIYAN_ACCESS_TOKENS"
_OPEN_PATHS: frozenset[str] = frozenset({"/health"})

logger = logging.getLogger(__name__)


def parse_access_tokens(raw: str | None) -> frozenset[str]:
    """Parse ``QIYAN_ACCESS_TOKENS`` raw value into a stripped token allowlist."""

    if not raw:
        return frozenset()
    return frozenset(token.strip() for token in raw.split(",") if token.strip())


class AccessTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, allowed_tokens: frozenset[str]) -> None:
        super().__init__(app)
        self._allowed_tokens = allowed_tokens

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._allowed_tokens:
            return await call_next(request)
        # CORS preflight is normally absorbed by CORSMiddleware (installed outer);
        # this branch stays as a defensive net for OPTIONS requests that reach
        # us anyway (e.g. without an Origin header).
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in _OPEN_PATHS:
            return await call_next(request)

        token = request.headers.get(ACCESS_TOKEN_HEADER)
        if token is None or token not in self._allowed_tokens:
            return JSONResponse(
                status_code=401,
                content={"detail": "missing or invalid X-Access-Token"},
            )

        return await call_next(request)


def install_access_token_middleware(app: FastAPI) -> None:
    """Install ``AccessTokenMiddleware`` reading the env at call time.

    Emits an INFO log line so an empty env does not silently leave the API
    fully open in production. Token values are never logged.
    """

    allowed = parse_access_tokens(os.getenv(ACCESS_TOKENS_ENV))
    if not allowed:
        logger.info(
            "access control disabled: %s unset or empty (open mode)",
            ACCESS_TOKENS_ENV,
        )
    else:
        logger.info(
            "access control enabled with %d token(s) via %s",
            len(allowed),
            ACCESS_TOKENS_ENV,
        )
    app.add_middleware(AccessTokenMiddleware, allowed_tokens=allowed)
