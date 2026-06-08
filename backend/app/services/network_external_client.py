import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.repositories.network_cache import NetworkCacheRepository, build_network_cache_key
from app.schemas.network import NetworkDataSource

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NetworkExternalJsonResult:
    payload: Any | None
    data_source: NetworkDataSource
    warning: str | None
    from_cache: bool
    request_count: int
    latency_ms: int


@dataclass(frozen=True)
class NetworkExternalTextResult:
    payload: str | None
    data_source: NetworkDataSource
    warning: str | None
    from_cache: bool
    request_count: int
    latency_ms: int


class NetworkExternalClient:
    def __init__(
        self,
        *,
        cache_repo: NetworkCacheRepository,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 15.0,
        rate_limit_per_second: float = 1.0,
    ) -> None:
        self.cache_repo = cache_repo
        self.http_client = http_client or httpx.Client(timeout=timeout_seconds)
        self.timeout_seconds = timeout_seconds
        self.rate_limit_per_second = rate_limit_per_second

    def get_json(
        self,
        *,
        provider: str,
        url: str,
        query: str,
        params: dict[str, Any],
        license_note: str | None = None,
    ) -> NetworkExternalJsonResult:
        cache_key = build_network_cache_key(provider=provider, query=query, params=params)
        cached = self.cache_repo.read_json(cache_key)
        if cached is not None:
            data_source = NetworkDataSource(
                name=provider,
                source_record_id=query,
                url=url,
                retrieved_at=None,
                license_note=license_note,
                cache_key=cache_key,
                from_cache=True,
            )
            logger.info(
                "network_external_request",
                extra={
                    "provider": provider,
                    "cache_hit": True,
                    "latency_ms": 0,
                    "status_code": None,
                    "request_count": 0,
                },
            )
            return NetworkExternalJsonResult(
                payload=cached,
                data_source=data_source,
                warning=None,
                from_cache=True,
                request_count=0,
                latency_ms=0,
            )

        started = time.perf_counter()
        last_status: int | None = None
        last_error: str | None = None
        request_count = 0
        for attempt in range(2):
            if attempt > 0 and self.rate_limit_per_second > 0:
                time.sleep(1 / self.rate_limit_per_second)
            try:
                response = self.http_client.get(url, params=params, timeout=self.timeout_seconds)
                request_count += 1
                last_status = response.status_code
                if response.status_code < 400:
                    payload = response.json()
                    self.cache_repo.write_json(cache_key, payload)
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    data_source = NetworkDataSource(
                        name=provider,
                        source_record_id=query,
                        url=str(response.url),
                        retrieved_at=datetime.now(UTC).isoformat(),
                        license_note=license_note,
                        cache_key=cache_key,
                        from_cache=False,
                    )
                    logger.info(
                        "network_external_request",
                        extra={
                            "provider": provider,
                            "cache_hit": False,
                            "latency_ms": latency_ms,
                            "status_code": response.status_code,
                            "request_count": request_count,
                        },
                    )
                    return NetworkExternalJsonResult(
                        payload=payload,
                        data_source=data_source,
                        warning=None,
                        from_cache=False,
                        request_count=request_count,
                        latency_ms=latency_ms,
                    )
                last_error = f"HTTP {response.status_code}"
            except (httpx.HTTPError, ValueError) as exc:
                request_count += 1
                last_error = str(exc)

        latency_ms = int((time.perf_counter() - started) * 1000)
        warning = f"{provider} request failed after retry: {last_error or 'unknown error'}"
        data_source = NetworkDataSource(
            name=provider,
            source_record_id=query,
            url=url,
            retrieved_at=datetime.now(UTC).isoformat(),
            license_note=license_note,
            cache_key=cache_key,
            from_cache=False,
        )
        logger.warning(
            "network_external_request_failed",
            extra={
                "provider": provider,
                "cache_hit": False,
                "latency_ms": latency_ms,
                "status_code": last_status,
                "request_count": request_count,
            },
        )
        return NetworkExternalJsonResult(
            payload=None,
            data_source=data_source,
            warning=warning,
            from_cache=False,
            request_count=request_count,
            latency_ms=latency_ms,
        )

    def get_text(
        self,
        *,
        provider: str,
        url: str,
        query: str,
        params: dict[str, Any],
        license_note: str | None = None,
    ) -> NetworkExternalTextResult:
        cache_key = build_network_cache_key(provider=provider, query=query, params=params)
        cached = self.cache_repo.read_json(cache_key)
        if isinstance(cached, str):
            data_source = NetworkDataSource(
                name=provider,
                source_record_id=query,
                url=url,
                retrieved_at=None,
                license_note=license_note,
                cache_key=cache_key,
                from_cache=True,
            )
            logger.info(
                "network_external_request",
                extra={
                    "provider": provider,
                    "cache_hit": True,
                    "latency_ms": 0,
                    "status_code": None,
                    "request_count": 0,
                },
            )
            return NetworkExternalTextResult(
                payload=cached,
                data_source=data_source,
                warning=None,
                from_cache=True,
                request_count=0,
                latency_ms=0,
            )

        started = time.perf_counter()
        last_status: int | None = None
        last_error: str | None = None
        request_count = 0
        for attempt in range(2):
            if attempt > 0 and self.rate_limit_per_second > 0:
                time.sleep(1 / self.rate_limit_per_second)
            try:
                response = self.http_client.get(url, params=params, timeout=self.timeout_seconds)
                request_count += 1
                last_status = response.status_code
                if response.status_code < 400:
                    payload = response.text
                    self.cache_repo.write_json(cache_key, payload)
                    latency_ms = int((time.perf_counter() - started) * 1000)
                    data_source = NetworkDataSource(
                        name=provider,
                        source_record_id=query,
                        url=str(response.url),
                        retrieved_at=datetime.now(UTC).isoformat(),
                        license_note=license_note,
                        cache_key=cache_key,
                        from_cache=False,
                    )
                    logger.info(
                        "network_external_request",
                        extra={
                            "provider": provider,
                            "cache_hit": False,
                            "latency_ms": latency_ms,
                            "status_code": response.status_code,
                            "request_count": request_count,
                        },
                    )
                    return NetworkExternalTextResult(
                        payload=payload,
                        data_source=data_source,
                        warning=None,
                        from_cache=False,
                        request_count=request_count,
                        latency_ms=latency_ms,
                    )
                last_error = f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                request_count += 1
                last_error = str(exc)

        latency_ms = int((time.perf_counter() - started) * 1000)
        warning = f"{provider} request failed after retry: {last_error or 'unknown error'}"
        data_source = NetworkDataSource(
            name=provider,
            source_record_id=query,
            url=url,
            retrieved_at=datetime.now(UTC).isoformat(),
            license_note=license_note,
            cache_key=cache_key,
            from_cache=False,
        )
        logger.warning(
            "network_external_request_failed",
            extra={
                "provider": provider,
                "cache_hit": False,
                "latency_ms": latency_ms,
                "status_code": last_status,
                "request_count": request_count,
            },
        )
        return NetworkExternalTextResult(
            payload=None,
            data_source=data_source,
            warning=warning,
            from_cache=False,
            request_count=request_count,
            latency_ms=latency_ms,
        )
