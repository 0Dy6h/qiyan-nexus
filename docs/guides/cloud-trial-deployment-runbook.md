# 云端单机 + Token 自助 — 小范围试用部署 Runbook

> 用途：把 Qiyan Nexus 部署到**一台云服务器**，让 2-5 位医生/科研 reviewer 用 `X-Access-Token` 自助访问、自己时间走查。
> 运行 profile：**deterministic provider + keyword retrieval + token 门禁 + 隔离 runtime**，**不接入真实 LLM、不外发数据**。
> 对应计划：`docs/plans/2026-06-08-post-mvp-a-roadmap.md` 路径 A 的"小范围试用"；反馈模板 `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`。

---

## 0. 架构（同源反代，零 CORS 改动）

```
reviewer 浏览器 ──HTTPS──> nginx (:443, DOMAIN)
                              ├── /            → Next.js  (127.0.0.1:3000)
                              ├── /api/...      → FastAPI (127.0.0.1:8000)
                              └── /health       → FastAPI (127.0.0.1:8000)
```

前端与后端**同源**（都在 `https://DOMAIN` 下），浏览器→后端是同源请求，**不触发 CORS**，因此**不需要改** `backend/app/main.py` 里硬编码的 `allow_origins`。
> ⚠️ 如果改成前后端分域名（如 `app.DOMAIN` + `api.DOMAIN`），就必须编辑 `app/main.py:95-100` 的 `allow_origins`，否则浏览器调用被 CORS 拦截。本 runbook 用同源方案规避这一步。

---

## 1. 前置

- 一台 Ubuntu 22.04/24.04 云主机（2 vCPU / 2-4GB 足够，单进程低并发）
- 一个解析到该主机的域名 `DOMAIN`（HTTPS 需要）
- 开放 80/443 入站；8000/3000 **仅监听 127.0.0.1**（只经 nginx 暴露）

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv git nginx
# Node 20 + pnpm
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm i -g pnpm
sudo useradd -m -r -s /usr/sbin/nologin qiyan || true
sudo mkdir -p /opt/qiyan && sudo chown qiyan:qiyan /opt/qiyan
sudo -u qiyan git clone https://github.com/0Dy6h/qiyan-nexus.git /opt/qiyan/qiyan-nexus
```

---

## 2. 后端

```bash
cd /opt/qiyan/qiyan-nexus/backend
sudo -u qiyan python3.11 -m venv .venv
sudo -u qiyan .venv/bin/python -m pip install -U pip
sudo -u qiyan .venv/bin/python -m pip install -e ".[dev]"
sudo -u qiyan mkdir -p uploads data/runtime
```

### 2.1 生产环境变量（关键：满足已生效的生产校验）

应用**不读 `.env`**（代码无 `load_dotenv`），所有配置走真实环境变量。用 systemd `EnvironmentFile`：

`/etc/qiyan/backend.env`（`sudo mkdir -p /etc/qiyan`，权限 `640`，属主 `qiyan`）：

```ini
ENVIRONMENT=production
# 逗号分隔的 token 允许清单（每行一个 reviewer 也行，见 §6）
QIYAN_ACCESS_TOKENS=trial-aaa111,trial-bbb222,trial-ccc333
# 生产校验要求"至少一个 LLM key 非空"。试用走 deterministic，不会真的调用，
# 这里放占位串即可满足校验，且因为不设 QIYAN_LLM_PROVIDER 而永不被使用。
QIYAN_OPENCODE_GO_API_KEY=unused-placeholder-deterministic-trial
# 生产校验要求 upload 目录存在且可写 —— 用绝对路径并预先 mkdir+chown
UPLOAD_STORAGE_DIR=/opt/qiyan/qiyan-nexus/backend/uploads
# 推荐 sqlite runtime（比 JSON 略稳）；单进程下足够小范围试用
QIYAN_STATE_BACKEND=sqlite
QIYAN_SQLITE_DB_PATH=/opt/qiyan/qiyan-nexus/backend/data/runtime/qiyan_state.sqlite3
```

**绝对不要设**：`QIYAN_LLM_PROVIDER`（留空=deterministic）、`QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0`（绕过 grounding 安全闸）。

> 这三条生产校验（LLM key 非空 / upload 目录存在 / grounding 阈值 ∈ [0,1]）由 `backend/app/core/config.py` 的 `__post_init__` 在启动时 fail-fast。该校验此前因缩进 bug 静默失效，已于本分支修复（commit `8346ec9`），所以现在**会真的拦你**——按上表配齐即可。

### 2.2 后端 systemd 服务

`/etc/systemd/system/qiyan-api.service`：

```ini
[Unit]
Description=Qiyan Nexus API
After=network.target

[Service]
Type=simple
User=qiyan
WorkingDirectory=/opt/qiyan/qiyan-nexus/backend
EnvironmentFile=/etc/qiyan/backend.env
ExecStart=/opt/qiyan/qiyan-nexus/backend/.venv/bin/fastapi run app/main.py --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

> 单进程（`fastapi run` 默认）。**不要加 `--workers >1`**：runtime state 是文件型（JSON/SQLite），多进程并发写会有 race。小范围试用单进程足够。

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now qiyan-api
sudo systemctl status qiyan-api --no-pager
curl -s http://127.0.0.1:8000/health   # {"status":"ok",...}
```

---

## 3. 前端

`NEXT_PUBLIC_*` 是**构建期**变量（烤进 bundle），必须在 `pnpm build` **之前**设好：

```bash
cd /opt/qiyan/qiyan-nexus/frontend
sudo -u qiyan pnpm install
# 同源：base 指向 DOMAIN 自身；前端会调用 https://DOMAIN/api/... 经 nginx 反代到后端
sudo -u qiyan env \
  NEXT_PUBLIC_API_BASE_URL="https://DOMAIN" \
  NEXT_PUBLIC_QIYAN_ACCESS_TOKEN="trial-aaa111" \
  pnpm build
```

`/etc/systemd/system/qiyan-web.service`：

```ini
[Unit]
Description=Qiyan Nexus Web
After=network.target qiyan-api.service

[Service]
Type=simple
User=qiyan
WorkingDirectory=/opt/qiyan/qiyan-nexus/frontend
ExecStart=/usr/bin/pnpm start -p 3000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now qiyan-web
```

> 前端只能烤进**一个** token（`NEXT_PUBLIC_QIYAN_ACCESS_TOKEN`）。所以浏览器侧所有 reviewer 共用这一个 token；后端 `QIYAN_ACCESS_TOKENS` 可以多 token，但当前前端不会按人切换（见 §6 局限）。

---

## 4. nginx + HTTPS

`/etc/nginx/sites-available/qiyan`：

```nginx
server {
    listen 80;
    server_name DOMAIN;

    client_max_body_size 25m;   # PDF 上传后端限 20MB；留点余量

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /health { proxy_pass http://127.0.0.1:8000; }
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/qiyan /etc/nginx/sites-enabled/qiyan
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d DOMAIN     # 自动加 443 + http->https 跳转
```

---

## 5. 冒烟验证（部署后必跑）

**A. 复用现成 PowerShell 冒烟（推荐，覆盖完整流程）** —— 从你的 Windows 机器对云端 URL 跑：

```powershell
.\scripts\smoke-internal-preview.ps1 -BackendUrl https://DOMAIN -AccessToken "trial-aaa111"
```

**B. 最小 curl 兜底**（任意机器）：

```bash
BASE=https://DOMAIN; TOKEN=trial-aaa111
curl -s $BASE/health                                             # 200 {"status":"ok"}
curl -s -o /dev/null -w "%{http_code}\n" $BASE/api/literature?query=x   # 期望 401（无 token 被门禁拦）
curl -s -H "X-Access-Token: $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"question":"特应性皮炎的常见症状有哪些？","source":"auto","top_k":5}' \
     $BASE/api/rag/answer | python3 -m json.tool
# 验收点：provider_name == "deterministic"；答案含免责声明「非诊断结论、需结合临床。」
```

> 各端点确切路径与 payload 见 `README.md` 的 curl 示例。务必确认 RAG 返回 `provider_name="deterministic"`（证明没误开真实 LLM）且免责声明字节一致。

---

## 6. Token 发放与局限

- 后端 `QIYAN_ACCESS_TOKENS` 支持多 token；门禁逻辑见 `backend/app/core/access_control.py`（`X-Access-Token` 头、`/health` 与 `OPTIONS` 豁免、大小写敏感）。
- **当前前端只发一个 token**，所以"每人一个 token 做 API 归因"在不改代码时**做不到**。务实方案：
  - 全体共用一个试用 token（最简单）；reviewer 身份靠反馈表记录，不靠 token。
  - 后端访问日志（`RequestLoggingMiddleware`）记 `request_id`，不记 token/用户。
- 若以后真要按人归因 → 需要前端加"运行时输入 token"或按人分前端，属代码改动，非本 runbook 范围。

---

## 7. 数据隔离与轮次重置

- runtime 写入 `backend/data/runtime/`（sqlite/JSON），上传 PDF 写入 `backend/uploads/`，均 gitignored、不是生产库。
- 每轮试用前重置：`sudo systemctl stop qiyan-api`，备份或清空 `data/runtime/` 与 `uploads/`，再 `start`。
- 演示 seed 文献带 `record_origin=seed_sample`，**不可**当真实外部数据库文献引用——这点要在试用须知里讲清。

---

## 8. 试用须知里必须写清的边界

1. AI 回答是 **deterministic 检索式**，不是真实大模型；每条结论附免责声明，**不替代诊断**。
2. 网络药理学是 **mock 演示数据**（`/network` 页面顶部有边界 note）。
3. 文献含演示 seed + PubMed 实时同步两类，`记录来源`标签区分。
4. 数据不外发；上传 PDF 仅本机解析预览，扫描件可能回退占位说明。

---

## 9. 拆除

```bash
sudo systemctl disable --now qiyan-web qiyan-api
sudo rm /etc/nginx/sites-enabled/qiyan && sudo systemctl reload nginx
# 如需彻底清理：rm -rf /opt/qiyan，撤销证书 certbot delete --cert-name DOMAIN
```

---

## 已知限制（本 runbook 范围内）

| 项 | 限制 | 影响 |
|---|---|---|
| 并发 | 单进程 + 文件型 runtime state | 多 reviewer 同时上传 PDF 可能 race；小范围低并发可接受 |
| Token 归因 | 前端单 token | 无法按人区分 API 调用，靠反馈表归因 |
| 错误监控 | 无 Sentry/外部上报（安全审查 HIGH-8 推迟项） | 线上前端错误只在浏览器；后端异常进 systemd journal |
| 真实 LLM | 不启用 | 答案质量是 deterministic 基线，非真实模型水平 |

---

**状态**：runbook 就绪，等真人 reviewer 招募（§外部依赖）。配套证据包用 `scripts/collect-internal-preview-evidence.ps1` 本地生成（冻结可信构建 + request-id）。
