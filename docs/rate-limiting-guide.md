# Rate Limiting 速率限制指南

## 当前状态

项目已添加 `slowapi>=0.1.9` 依赖，但**当前未启用**速率限制。

## 为什么未启用？

1. **开发阶段** — 当前处于 MVP 阶段，主要用户是内部医生和研究人员
2. **测试兼容性** — slowapi 装饰器需要 `Request` 参数，与 `TestClient` 不兼容
3. **访问控制优先** — 已有 `X-Access-Token` 门禁，限制了访问范围

## 何时启用？

在以下情况下启用速率限制：

1. **生产部署** — 向更广泛用户群开放
2. **API 滥用** — 监控日志发现异常高频请求
3. **成本控制** — 需要限制 LLM API 调用频率

## 如何启用？

### 方式 1：使用 SlowAPI 装饰器（推荐）

```python
# app/api/rag.py
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/answer")
@limiter.limit("10/minute")  # type: ignore[untyped-decorator]
def answer_question_endpoint(
    request_obj: Request,  # 必需参数
    request: RagAnswerRequest = Body(),
) -> RagAnswerResponse:
    return answer_question(request.question, source=request.source, top_k=request.top_k)
```

**注意**：需要在测试中 mock 或跳过速率限制。

### 方式 2：使用 SlowAPI 中间件（全局）

```python
# app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/hour"],  # 全局默认限制
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

### 方式 3：基于 Redis 的分布式限流（多实例部署）

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
import redis

redis_client = redis.Redis(host="localhost", port=6379, db=0)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{redis_client.connection_pool.connection_kwargs['host']}:{redis_client.connection_pool.connection_kwargs['port']}",
)
```

## 推荐限流策略

| 端点 | 限制 | 理由 |
|------|------|------|
| `/api/rag/answer` | 10/minute | 防止 LLM API 成本爆炸 |
| `/api/uploads/pdf` | 5/minute | 防止存储滥用 |
| `/api/uploads/pdf/auto-parse` | 10/minute | PDF 解析计算密集 |
| `/api/network/analyze` | 5/minute | 网络药理学分析计算密集 |
| `/api/literature/search` | 30/minute | 读操作，可更宽松 |
| `/health` | 无限制 | 监控端点 |

## 测试注意事项

启用速率限制后，需要：

1. **集成测试**：使用独立的 limiter 实例或 mock
2. **E2E 测试**：考虑添加 `X-Test-Mode` 头绕过限流
3. **压力测试**：验证 429 响应和重试机制

## 监控

启用后监控指标：

- `rate_limit_exceeded_count` — 被拒绝的请求数
- `rate_limit_by_endpoint` — 各端点命中率
- `rate_limit_by_ip` — 高频 IP 列表

## 参考

- SlowAPI 文档：https://slowapi.readthedocs.io/
- FastAPI 速率限制：https://fastapi.tiangolo.com/advanced/middleware/
