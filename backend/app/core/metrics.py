"""Performance metrics collection for API endpoints."""

import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Dict, List


@dataclass
class LatencyStats:
    """Latency statistics for an endpoint."""

    count: int
    total_ms: float
    min_ms: float
    max_ms: float
    p50_samples: List[float]  # Rolling window for percentile calculation

    @property
    def avg_ms(self) -> float:
        """Calculate average latency."""
        return self.total_ms / self.count if self.count > 0 else 0.0

    @property
    def p50_ms(self) -> float:
        """Calculate P50 (median) latency from samples."""
        if not self.p50_samples:
            return 0.0
        sorted_samples = sorted(self.p50_samples)
        mid = len(sorted_samples) // 2
        return sorted_samples[mid]

    @property
    def p95_ms(self) -> float:
        """Calculate P95 latency from samples."""
        if not self.p50_samples:
            return 0.0
        sorted_samples = sorted(self.p50_samples)
        idx = int(len(sorted_samples) * 0.95)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    @property
    def p99_ms(self) -> float:
        """Calculate P99 latency from samples."""
        if not self.p50_samples:
            return 0.0
        sorted_samples = sorted(self.p50_samples)
        idx = int(len(sorted_samples) * 0.99)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]


class PerformanceMetrics:
    """Thread-safe performance metrics collector."""

    def __init__(self, max_samples: int = 1000):
        """Initialize metrics collector.

        Args:
            max_samples: Maximum number of samples to keep for percentile calculation.
        """
        self._lock = Lock()
        self._metrics: Dict[str, LatencyStats] = defaultdict(
            lambda: LatencyStats(
                count=0,
                total_ms=0.0,
                min_ms=float("inf"),
                max_ms=0.0,
                p50_samples=[],
            )
        )
        self._max_samples = max_samples

    def record(self, endpoint: str, elapsed_ms: float) -> None:
        """Record a request latency for an endpoint.

        Args:
            endpoint: Endpoint path (e.g., "/api/rag/answer")
            elapsed_ms: Request latency in milliseconds
        """
        with self._lock:
            stats = self._metrics[endpoint]
            stats.count += 1
            stats.total_ms += elapsed_ms
            stats.min_ms = min(stats.min_ms, elapsed_ms)
            stats.max_ms = max(stats.max_ms, elapsed_ms)

            # Keep rolling window of samples for percentile calculation
            stats.p50_samples.append(elapsed_ms)
            if len(stats.p50_samples) > self._max_samples:
                # Remove oldest sample when window is full
                stats.p50_samples.pop(0)

    def get_stats(self, endpoint: str) -> LatencyStats | None:
        """Get statistics for a specific endpoint.

        Args:
            endpoint: Endpoint path

        Returns:
            LatencyStats if endpoint has data, None otherwise
        """
        with self._lock:
            if endpoint not in self._metrics:
                return None
            stats = self._metrics[endpoint]
            # Return a copy to avoid mutation outside lock
            return LatencyStats(
                count=stats.count,
                total_ms=stats.total_ms,
                min_ms=stats.min_ms,
                max_ms=stats.max_ms,
                p50_samples=stats.p50_samples.copy(),
            )

    def get_all_stats(self) -> Dict[str, LatencyStats]:
        """Get statistics for all endpoints.

        Returns:
            Dictionary mapping endpoint paths to their statistics
        """
        with self._lock:
            return {
                endpoint: LatencyStats(
                    count=stats.count,
                    total_ms=stats.total_ms,
                    min_ms=stats.min_ms,
                    max_ms=stats.max_ms,
                    p50_samples=stats.p50_samples.copy(),
                )
                for endpoint, stats in self._metrics.items()
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()


# Global metrics instance
_metrics = PerformanceMetrics()


def record_request_latency(endpoint: str, elapsed_ms: float) -> None:
    """Record request latency for an endpoint.

    Args:
        endpoint: Endpoint path
        elapsed_ms: Request latency in milliseconds
    """
    _metrics.record(endpoint, elapsed_ms)


def get_endpoint_stats(endpoint: str) -> LatencyStats | None:
    """Get performance statistics for a specific endpoint.

    Args:
        endpoint: Endpoint path

    Returns:
        LatencyStats if endpoint has data, None otherwise
    """
    return _metrics.get_stats(endpoint)


def get_all_endpoint_stats() -> Dict[str, LatencyStats]:
    """Get performance statistics for all endpoints.

    Returns:
        Dictionary mapping endpoint paths to their statistics
    """
    return _metrics.get_all_stats()


def reset_metrics() -> None:
    """Reset all performance metrics."""
    _metrics.reset()
