"""Metrics API endpoints."""

from fastapi import APIRouter

from app.core.metrics import get_all_endpoint_stats, get_endpoint_stats

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/performance")
def get_performance_metrics() -> dict[str, dict[str, float | int]]:
    """Get performance metrics for all endpoints.

    Returns:
        Dictionary mapping endpoint paths to their statistics:
        - count: Total number of requests
        - avg_ms: Average latency in milliseconds
        - min_ms: Minimum latency in milliseconds
        - max_ms: Maximum latency in milliseconds
        - p50_ms: P50 (median) latency in milliseconds
        - p95_ms: P95 latency in milliseconds
        - p99_ms: P99 latency in milliseconds
    """
    all_stats = get_all_endpoint_stats()
    return {
        endpoint: {
            "count": stats.count,
            "avg_ms": round(stats.avg_ms, 2),
            "min_ms": round(stats.min_ms, 2),
            "max_ms": round(stats.max_ms, 2),
            "p50_ms": round(stats.p50_ms, 2),
            "p95_ms": round(stats.p95_ms, 2),
            "p99_ms": round(stats.p99_ms, 2),
        }
        for endpoint, stats in all_stats.items()
    }


@router.get("/performance/{endpoint:path}")
def get_endpoint_performance(endpoint: str) -> dict[str, float | int] | None:
    """Get performance metrics for a specific endpoint.

    Args:
        endpoint: Endpoint path (e.g., "api/rag/answer")

    Returns:
        Performance statistics or None if endpoint has no data
    """
    # Add leading slash if not present
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    stats = get_endpoint_stats(endpoint)
    if stats is None:
        return None

    return {
        "count": stats.count,
        "avg_ms": round(stats.avg_ms, 2),
        "min_ms": round(stats.min_ms, 2),
        "max_ms": round(stats.max_ms, 2),
        "p50_ms": round(stats.p50_ms, 2),
        "p95_ms": round(stats.p95_ms, 2),
        "p99_ms": round(stats.p99_ms, 2),
    }
