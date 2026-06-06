"""Tests for performance metrics."""

from app.core.metrics import (
    LatencyStats,
    PerformanceMetrics,
    get_all_endpoint_stats,
    get_endpoint_stats,
    record_request_latency,
    reset_metrics,
)


def test_latency_stats_avg():
    stats = LatencyStats(
        count=3,
        total_ms=300.0,
        min_ms=50.0,
        max_ms=150.0,
        p50_samples=[50.0, 100.0, 150.0],
    )
    assert stats.avg_ms == 100.0


def test_latency_stats_avg_zero_count():
    stats = LatencyStats(
        count=0,
        total_ms=0.0,
        min_ms=float("inf"),
        max_ms=0.0,
        p50_samples=[],
    )
    assert stats.avg_ms == 0.0


def test_latency_stats_p50():
    stats = LatencyStats(
        count=5,
        total_ms=500.0,
        min_ms=50.0,
        max_ms=200.0,
        p50_samples=[50.0, 75.0, 100.0, 150.0, 200.0],
    )
    assert stats.p50_ms == 100.0


def test_latency_stats_p95():
    samples = [float(i) for i in range(1, 101)]  # 1 to 100
    stats = LatencyStats(
        count=100,
        total_ms=sum(samples),
        min_ms=1.0,
        max_ms=100.0,
        p50_samples=samples,
    )
    # P95 of 100 samples: index 95 (0-indexed) = value 96
    assert stats.p95_ms == 96.0


def test_latency_stats_p99():
    samples = [float(i) for i in range(1, 101)]  # 1 to 100
    stats = LatencyStats(
        count=100,
        total_ms=sum(samples),
        min_ms=1.0,
        max_ms=100.0,
        p50_samples=samples,
    )
    # P99 of 100 samples: index 99 (0-indexed) = value 100
    assert stats.p99_ms == 100.0


def test_performance_metrics_record():
    metrics = PerformanceMetrics()
    metrics.record("/api/test", 100.0)
    metrics.record("/api/test", 200.0)

    stats = metrics.get_stats("/api/test")
    assert stats is not None
    assert stats.count == 2
    assert stats.total_ms == 300.0
    assert stats.min_ms == 100.0
    assert stats.max_ms == 200.0
    assert stats.avg_ms == 150.0


def test_performance_metrics_multiple_endpoints():
    metrics = PerformanceMetrics()
    metrics.record("/api/endpoint1", 100.0)
    metrics.record("/api/endpoint2", 200.0)

    stats1 = metrics.get_stats("/api/endpoint1")
    stats2 = metrics.get_stats("/api/endpoint2")

    assert stats1 is not None
    assert stats1.count == 1
    assert stats1.avg_ms == 100.0

    assert stats2 is not None
    assert stats2.count == 1
    assert stats2.avg_ms == 200.0


def test_performance_metrics_rolling_window():
    metrics = PerformanceMetrics(max_samples=3)
    metrics.record("/api/test", 10.0)
    metrics.record("/api/test", 20.0)
    metrics.record("/api/test", 30.0)
    metrics.record("/api/test", 40.0)  # Should evict 10.0

    stats = metrics.get_stats("/api/test")
    assert stats is not None
    assert len(stats.p50_samples) == 3
    assert 10.0 not in stats.p50_samples
    assert 40.0 in stats.p50_samples


def test_performance_metrics_get_nonexistent():
    metrics = PerformanceMetrics()
    stats = metrics.get_stats("/api/nonexistent")
    assert stats is None


def test_performance_metrics_get_all():
    metrics = PerformanceMetrics()
    metrics.record("/api/endpoint1", 100.0)
    metrics.record("/api/endpoint2", 200.0)

    all_stats = metrics.get_all_stats()
    assert len(all_stats) == 2
    assert "/api/endpoint1" in all_stats
    assert "/api/endpoint2" in all_stats


def test_performance_metrics_reset():
    metrics = PerformanceMetrics()
    metrics.record("/api/test", 100.0)
    metrics.reset()

    stats = metrics.get_stats("/api/test")
    assert stats is None


def test_global_record_request_latency():
    reset_metrics()  # Clean slate
    record_request_latency("/api/global", 123.45)

    stats = get_endpoint_stats("/api/global")
    assert stats is not None
    assert stats.count == 1
    assert stats.avg_ms == 123.45


def test_global_get_all_endpoint_stats():
    reset_metrics()
    record_request_latency("/api/endpoint1", 100.0)
    record_request_latency("/api/endpoint2", 200.0)

    all_stats = get_all_endpoint_stats()
    assert len(all_stats) == 2
    assert "/api/endpoint1" in all_stats
    assert "/api/endpoint2" in all_stats
