# 2026-07-10 对抗性加固第一阶段 Handoff

> **Superseded in part**：本文件记录第一阶段当时状态。network task 的“无 owner/ACL”缺口已由同日 `2026-07-10-adversarial-hardening-phase-2-network-ownership.md` 关闭；PDF/literature/uploaded chunk/RAG 隔离缺口仍有效。最新结论以 `2026-07-11-adversarial-hardening-closeout.md` 为准。

## Goal

按第一性原则处理完整对抗性审查中的最高优先级风险：公开浏览器 token、已知前端依赖漏洞、SQLite 共享连接并发损坏、未知网络查询伪造机制链、RAG 导出可由客户端伪造，以及 production 校验依赖占位 LLM key。

## Completed

- 前端访问边界：删除 `NEXT_PUBLIC_QIYAN_ACCESS_TOKEN` 路径；浏览器会剥离调用方提供的 `X-Access-Token`。云端改为 HTTPS + 每 reviewer 独立 nginx Basic Auth；nginx 从 root-only 配置向 FastAPI 注入共享内部 token并记录 `$remote_user` / `X-Request-ID`。
- Server Component 内部通道：`QIYAN_INTERNAL_API_BASE_URL` + `QIYAN_INTERNAL_API_TOKEN` 仅由 Next.js 服务端使用，`/literature/[id]` 不经过公网 Basic Auth；构建扫描确认 token 未进入 `.next/static`。
- 依赖安全：Next.js `16.2.4 → 16.2.6`；pnpm override 将 PostCSS 固定为 `8.5.10`；`pnpm audit --prod` 为 0 vulnerabilities。
- SQLite 并发：literature/chunk/network-task 三个 repository 的共享 connection 数据库调用全部由 `RLock` 串行化；network poll 的读取、状态转换、写回通过 repository `advance()` 原子推进；每个 backend 新增 8 workers × 20 writes 的并发回归测试，并覆盖同一 task 的并发 poll。
- 网络结果诚实性：未知方剂/药材返回空 `chains`，不再把查询字符串贴到无关 seed 机制链上；API contract test 锁定完成态空结果。
- RAG 导出完整性：`/api/rag/answer` 返回进程内 HMAC `integrity_token`；Markdown/DOCX export endpoint 对客户端提交的 canonical 原始 JSON 验签，字段缺失、已有字段修改或顶层/嵌套未知字段均返回 409。
- Production 配置：要求 `QIYAN_ACCESS_TOKENS`；deterministic 模式不再要求占位 LLM key，只有显式 `opencode_go` / `anthropic` 才要求对应真实 key。
- 独立复审收口：Next production server 显式绑定 `127.0.0.1:3000`，避免绕过 nginx；Certbot 改为真实 webroot renewal 并要求 `renew --dry-run`；Basic Auth 使用 bcrypt 强随机密码并由 fail2ban 限制 401 暴力猜测；`ENVIRONMENT=prod|production` 会统一进入 production 校验，未知环境 fail closed；SQLite PubMed 批量 upsert 失败时在锁内 rollback，失败批次保持原子性；server-side internal token 仅向 `QIYAN_INTERNAL_API_BASE_URL` 同源目标发送。

## Verification

- Backend：ruff format/check、mypy 全绿；`615 passed, 1 skipped`。
- Frontend：`227 passed`；typecheck/build 全绿；Next.js `16.2.6`。
- Playwright：`4 passed`。
- Supply chain：`pnpm audit --prod` → 0 vulnerabilities。
- 独立全差异复审提出的 RAG payload 归一化绕过、network task read-modify-write 竞态及 runbook provider 指令矛盾均已关闭。

## Remaining high-priority risks

1. 当时 PDF、文献 metadata、network task 均无逐 reviewer owner/ACL；其中 network task 后续已在 Phase 2 关闭。PDF、文献 metadata、uploaded chunk 与 RAG retrieval 仍共享 runtime；云端多人试用只能使用全体均有权查看的材料。
2. RAG export HMAC 当前是单进程、进程内密钥；重启会使旧 payload 失效，多 worker 不支持。下一阶段应评估持久化 `answer_id` + immutable answer record。
3. 尚未落地入站限流、上传/任务/外部 API 配额、metrics 路由模板归一化和 schema 长度上限。
4. PDF 仍只校验 MIME，不校验 magic/完整解析，且缺少删除、配额和孤儿文件回收。
5. Python 依赖仍无 lock，GitHub Actions 仍使用可移动 major tag。

## Recommended next slices

1. 对象级隔离：reviewer identity → owner_id → PDF/task/literature metadata 授权，或先提供每 reviewer 独立实例模式。
2. 资源治理：入站 rate limit、storage/task quota、外部 PubMed/network/LLM 全局限速。
3. DoS 边界：将 metrics key 归一为 route template；为 question/query/top_k/export payload/file name 设置上限；补 streaming request-body limit。
4. 文件安全：PDF magic/parse validation、checksum、删除与保留策略。
5. 供应链：提交 Python lock、production-only dependency profile、Actions SHA pin。

## Working tree notes

- 未提交。
- `.mcp.json` / `components.json` 是审查前已存在的 untracked local shim，本阶段未修改，不应随功能改动提交。
