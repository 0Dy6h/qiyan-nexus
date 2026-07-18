# 云端单机 + Basic Auth — 小范围试用部署 Runbook

> 用途：把 Qiyan Nexus 部署到**一台云服务器**，让 2-5 位医生/科研 reviewer 通过各自的 nginx Basic Auth 账号访问。
> 运行 profile：**deterministic provider + keyword retrieval + 全站 Basic Auth + 后端内部 token + 独立实例 runtime**，**不接入真实 LLM、不外发数据**。这里的 runtime 隔离是“与 seed/其他部署轮次分开”，不是逐 reviewer PDF 隔离。
> 对应计划：`docs/plans/2026-06-08-post-mvp-a-roadmap.md` 路径 A 的"小范围试用"；反馈模板 `docs/evaluations/2026-06-06-small-scale-trial-feedback.md`。

---

## 0. 架构（同源反代，零 CORS 改动）

```
reviewer 浏览器 ──HTTPS + Basic Auth──> nginx (:443, DOMAIN)
                                         ├── /       → Next.js  (127.0.0.1:3000)
                                         ├── /api/   → 注入后端内部 token → FastAPI (127.0.0.1:8000)
                                         └── /health → FastAPI (127.0.0.1:8000)
```

前端与后端**同源**（都在 `https://DOMAIN` 下），浏览器→后端是同源请求，**不触发 CORS**，因此**不需要改** `backend/app/main.py` 里硬编码的 `allow_origins`。Basic Auth 在 nginx 全站执行；浏览器永远不持有后端 `X-Access-Token`，该 header 只由 nginx 在 `/api/` 反代时覆盖注入。
> ⚠️ 如果改成前后端分域名（如 `app.DOMAIN` + `api.DOMAIN`），就必须编辑 `app/main.py:95-100` 的 `allow_origins`，否则浏览器调用被 CORS 拦截。本 runbook 用同源方案规避这一步。

---

## 1. 前置

- 一台 Ubuntu 22.04/24.04 云主机（2 vCPU / 2-4GB 足够，单进程低并发）
- 一个解析到该主机的域名 `DOMAIN`（HTTPS 需要）
- 开放 80/443 入站；8000/3000 **仅监听 127.0.0.1**（只经 nginx 暴露）

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv git nginx apache2-utils fail2ban
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

`/etc/qiyan/backend.env`（`sudo mkdir -p /etc/qiyan`，最终权限 `640`、属主 `root:qiyan`）：

```ini
ENVIRONMENT=production
# 单个高熵、仅后端与 nginx 知道的内部 token；reviewer 不应获得该值
QIYAN_ACCESS_TOKENS=BACKEND_ONLY_TOKEN
# deterministic 试用不需要任何 LLM key；只有显式选择 live provider 时才配置对应 key
QIYAN_LLM_PROVIDER=deterministic
# 生产校验要求 upload 目录存在且可写 —— 用绝对路径并预先 mkdir+chown
UPLOAD_STORAGE_DIR=/opt/qiyan/qiyan-nexus/backend/uploads
# 推荐 sqlite runtime（比 JSON 略稳）；单进程下足够小范围试用
QIYAN_STATE_BACKEND=sqlite
QIYAN_SQLITE_DB_PATH=/opt/qiyan/qiyan-nexus/backend/data/runtime/qiyan_state.sqlite3
# 仅在启用 /api/network/disease-import/verify 时配置；manifest 由 operator 生成并保持只读
NETWORK_OPEN_TARGETS_MANIFEST_PATH=/etc/qiyan/open-targets-artifact-manifest.json
NETWORK_RAW_ARTIFACT_DIR=/opt/qiyan/qiyan-nexus/backend/data/runtime/network_raw_artifacts
```

若启用 raw-artifact 入口，先创建 runtime 目录并安装 manifest：

```bash
sudo install -d -o qiyan -g qiyan -m 750 /opt/qiyan/qiyan-nexus/backend/data/runtime/network_raw_artifacts
sudo install -o root -g qiyan -m 640 /path/to/operator-reviewed-manifest.json /etc/qiyan/open-targets-artifact-manifest.json
```

manifest 必须按服务端计算的 raw-byte SHA-256 索引，不能由浏览器生成或上传。若云端试用不开放该入口，删除上述两个环境变量并在 reviewer 说明中标记 raw-artifact 上传不可用；默认 mock `/api/network/analyze` 不受影响。

**绝对不要做**：未完成真实 provider 的密钥管理与数据外发审查时，不得把 `QIYAN_LLM_PROVIDER` 改为 `opencode_go` 或 `anthropic`；不得设置 `QIYAN_GROUNDING_SEMANTIC_THRESHOLD=0` 绕过 grounding 安全闸。内部试用应保留上面的显式 `QIYAN_LLM_PROVIDER=deterministic`。

> 生产启动会 fail-fast 检查：访问控制已启用、upload 目录存在、grounding 阈值 ∈ [0,1]；只有 `QIYAN_LLM_PROVIDER=opencode_go|anthropic` 时才要求对应真实 API key。不要用占位 key 绕过配置校验。

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

`NEXT_PUBLIC_*` 是**构建期公开变量**，只能放 API base 等非秘密配置。禁止把任何访问凭证写入这类变量：

```bash
cd /opt/qiyan/qiyan-nexus/frontend
sudo -u qiyan pnpm install
# 同源：base 指向 DOMAIN 自身；前端会调用 https://DOMAIN/api/... 经 nginx 反代到后端
sudo -u qiyan env \
  NEXT_PUBLIC_API_BASE_URL="https://DOMAIN" \
  pnpm build
```

Next.js Server Component（当前 `/literature/[id]`）需要绕过公网 Basic Auth 直连本机 FastAPI。把非公开 runtime 配置放入 `/etc/qiyan/frontend.env`；文件名虽叫 frontend，但只由 Next.js 服务端进程读取，不是浏览器环境：

```ini
QIYAN_INTERNAL_API_BASE_URL=http://127.0.0.1:8000
QIYAN_INTERNAL_API_TOKEN=BACKEND_ONLY_TOKEN
```

```bash
sudo chown root:qiyan /etc/qiyan/frontend.env
sudo chmod 640 /etc/qiyan/frontend.env
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
EnvironmentFile=/etc/qiyan/frontend.env
ExecStart=/usr/bin/pnpm exec next start -H 127.0.0.1 -p 3000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now qiyan-web
```

> 后端内部 token 只允许存在于 Next.js **服务端进程的非公开 runtime environment**；不得进入 `NEXT_PUBLIC_*`、bundle、HTML、浏览器请求或 reviewer 文档。§4 生成 token 后会立即对 `.next/static` 做反向检查。

---

## 4. nginx + HTTPS

先生成一次后端内部 token，并把**同一个值**写入 `/etc/qiyan/backend.env` 的 `QIYAN_ACCESS_TOKENS`。随后创建仅 root 可读的 nginx http-context 配置；该文件同时定义 token map 与带 reviewer 用户名/request-id 的审计日志格式：

```bash
umask 077
BACKEND_TOKEN_FILE="$(mktemp)"
trap 'rm -f "$BACKEND_TOKEN_FILE"' EXIT
openssl rand -hex 32 > "$BACKEND_TOKEN_FILE"

# token 只通过 0600 临时文件进入 root helper 的 stdin/file I/O，
# 不展开到 sed、grep、python 或 sudo 的 argv。
sudo python3 - "$BACKEND_TOKEN_FILE" <<'PY'
from pathlib import Path
import re
import sys

token = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
if re.fullmatch(r"[0-9a-f]{64}", token) is None:
    raise SystemExit("invalid generated backend token")

def replace_setting(path: str, key: str) -> None:
    target = Path(path)
    source = target.read_text(encoding="utf-8")
    updated, count = re.subn(
        rf"^{re.escape(key)}=.*$",
        f"{key}={token}",
        source,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise SystemExit(f"missing {key} in {path}")
    target.write_text(updated, encoding="utf-8")

replace_setting("/etc/qiyan/backend.env", "QIYAN_ACCESS_TOKENS")
replace_setting("/etc/qiyan/frontend.env", "QIYAN_INTERNAL_API_TOKEN")

Path("/etc/nginx/conf.d/qiyan-backend-token.conf").write_text(
    f'''map $host $qiyan_backend_token {{
    default "{token}";
}}
log_format qiyan_trial 'remote=$remote_addr user=$remote_user request="$request_method $uri" '
                       'status=$status request_id=$upstream_http_x_request_id '
                       'bytes=$body_bytes_sent elapsed=$request_time';
''',
    encoding="utf-8",
)
PY
sudo chown root:qiyan /etc/qiyan/backend.env
sudo chmod 640 /etc/qiyan/backend.env
sudo chown root:qiyan /etc/qiyan/frontend.env
sudo chmod 640 /etc/qiyan/frontend.env
sudo chown root:root /etc/nginx/conf.d/qiyan-backend-token.conf
sudo chmod 600 /etc/nginx/conf.d/qiyan-backend-token.conf
if sudo -u qiyan grep -R -F -f "$BACKEND_TOKEN_FILE" /opt/qiyan/qiyan-nexus/frontend/.next/static; then
    echo "ERROR: backend token leaked into the frontend bundle" >&2
    exit 1
fi
rm -f "$BACKEND_TOKEN_FILE"
trap - EXIT
```

为每位 reviewer 创建独立账号。使用 `-B` 强制 bcrypt；密码由密码管理器生成，至少 20 个随机字符，并通过独立安全渠道发放。只有第一条命令使用 `-c`；后续账号不要带 `-c`，否则会覆盖已有文件：

```bash
REVIEWER_ID=reviewer-a
[[ "$REVIEWER_ID" =~ ^[a-z0-9][a-z0-9._-]{0,63}$ ]] || { echo "invalid reviewer id" >&2; exit 1; }
sudo htpasswd -B -c /etc/nginx/qiyan-reviewers.htpasswd "$REVIEWER_ID"
REVIEWER_ID=reviewer-b
[[ "$REVIEWER_ID" =~ ^[a-z0-9][a-z0-9._-]{0,63}$ ]] || { echo "invalid reviewer id" >&2; exit 1; }
sudo htpasswd -B /etc/nginx/qiyan-reviewers.htpasswd "$REVIEWER_ID"
REVIEWER_ID=reviewer-c
[[ "$REVIEWER_ID" =~ ^[a-z0-9][a-z0-9._-]{0,63}$ ]] || { echo "invalid reviewer id" >&2; exit 1; }
sudo htpasswd -B /etc/nginx/qiyan-reviewers.htpasswd "$REVIEWER_ID"
sudo chown root:www-data /etc/nginx/qiyan-reviewers.htpasswd
sudo chmod 640 /etc/nginx/qiyan-reviewers.htpasswd
```

先用临时 HTTP-only 站点签发 webroot 证书，再启用最终 HTTPS 站点。这样 Certbot 的 renewal 配置会持久化为 webroot，不需要续期时抢占 nginx 的 80 端口：

```bash
sudo apt install -y certbot
sudo mkdir -p /var/www/qiyan-acme
sudo sh -c 'cat > /etc/nginx/sites-available/qiyan-bootstrap' <<'EOF'
server {
    listen 80;
    server_name DOMAIN;
    access_log /var/log/nginx/qiyan-trial-access.log qiyan_trial;
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/qiyan-acme;
    }
    location / { return 404; }
}
EOF
sudo ln -s /etc/nginx/sites-available/qiyan-bootstrap /etc/nginx/sites-enabled/qiyan-bootstrap
sudo nginx -t && sudo systemctl reload nginx
sudo certbot certonly --webroot -w /var/www/qiyan-acme -d DOMAIN
sudo rm /etc/nginx/sites-enabled/qiyan-bootstrap
```

`/etc/nginx/sites-available/qiyan`：

```nginx
server {
    listen 80;
    server_name DOMAIN;
    access_log /var/log/nginx/qiyan-trial-access.log qiyan_trial;

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/qiyan-acme;
    }
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name DOMAIN;

    ssl_certificate /etc/letsencrypt/live/DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN/privkey.pem;

    client_max_body_size 25m;   # PDF 上传后端限 20MB；留点余量
    auth_basic "Qiyan Nexus reviewer trial";
    auth_basic_user_file /etc/nginx/qiyan-reviewers.htpasswd;
    access_log /var/log/nginx/qiyan-trial-access.log qiyan_trial;

    location = /api { return 308 /api/; }
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        # 覆盖客户端同名 header：token 只来自 root-only nginx 配置，
        # reviewer identity 只来自通过 Basic Auth 后的 $remote_user。
        proxy_set_header X-Access-Token $qiyan_backend_token;
        proxy_set_header X-Qiyan-Reviewer $remote_user;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Authorization "";
    }
    location / {
        proxy_pass http://127.0.0.1:3000;
        # 供后续 Server Component 在服务端保留 reviewer 上下文；浏览器
        # 不能自行选择 owner，Next 也不得把该值写入公开环境变量。
        proxy_set_header X-Qiyan-Reviewer $remote_user;
        proxy_set_header Authorization "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/qiyan /etc/nginx/sites-enabled/qiyan
sudo nginx -t && sudo systemctl reload nginx
sudo certbot renew --dry-run
```

`qiyan-trial` access log 故意只记录 method + URI path，不记录 query string；避免搜索词、课题名称或误输入的敏感信息被复制进该审计日志。nginx error log 在异常请求或 upstream 故障时仍可能包含带 query 的 request context，因此敏感输入应使用 POST body，并按主机安全策略限制 error log 权限与保留期。限制 trial access log 读取权限并保留 14 天：

```bash
sudo touch /var/log/nginx/qiyan-trial-access.log
sudo chown www-data:adm /var/log/nginx/qiyan-trial-access.log
sudo chmod 640 /var/log/nginx/qiyan-trial-access.log
sudo sh -c 'cat > /etc/logrotate.d/qiyan-trial' <<'EOF'
/var/log/nginx/qiyan-trial-access.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        /usr/sbin/nginx -s reopen >/dev/null 2>&1 || true
    endscript
}
EOF
sudo logrotate -d /etc/logrotate.d/qiyan-trial
```

为 Basic Auth 失败启用 fail2ban，避免公网无限密码猜测：

```bash
sudo sh -c 'cat > /etc/fail2ban/filter.d/qiyan-basic-auth.conf' <<'EOF'
[Definition]
failregex = ^remote=<HOST> .* status=401 .*$
ignoreregex =
EOF

sudo sh -c 'cat > /etc/fail2ban/jail.d/qiyan-basic-auth.local' <<'EOF'
[qiyan-basic-auth]
enabled = true
filter = qiyan-basic-auth
logpath = /var/log/nginx/qiyan-trial-access.log
port = http,https
maxretry = 5
findtime = 10m
bantime = 1h
EOF

sudo systemctl enable --now fail2ban
sudo fail2ban-regex /var/log/nginx/qiyan-trial-access.log /etc/fail2ban/filter.d/qiyan-basic-auth.conf
sudo fail2ban-client status qiyan-basic-auth
```

重载后重启后端，使两侧使用同一个新 token：

```bash
sudo nginx -t
sudo systemctl restart qiyan-api qiyan-web
sudo systemctl reload nginx
ss -ltnp | grep -E '127\.0\.0\.1:(3000|8000)'
```

验收时必须确认 3000/8000 只监听 `127.0.0.1`，且从外部网络无法直连 `DOMAIN:3000` / `DOMAIN:8000`；否则可绕过 nginx Basic Auth。

---

## 5. 冒烟验证（部署后必跑）

现有 `smoke-internal-preview.ps1 -AccessToken` 面向**直接后端 API**，不负责 nginx Basic Auth；云端边界应使用 reviewer 账号验证：

```bash
set -euo pipefail
BASE=https://DOMAIN
SMOKE_DIR="$(mktemp -d)"
trap 'rm -rf "$SMOKE_DIR"' EXIT

assert_status() {
  local expected="$1"
  shift
  local actual
  actual="$(curl -sS -o "$SMOKE_DIR/response" -w "%{http_code}" "$@")"
  if [[ "$actual" != "$expected" ]]; then
    echo "expected HTTP $expected, got $actual: curl $*" >&2
    cat "$SMOKE_DIR/response" >&2
    exit 1
  fi
}

assert_status 401 "$BASE/"
assert_status 200 --user reviewer-a "$BASE/health"

RAG_STATUS="$(curl -sS --user reviewer-a \
  -o "$SMOKE_DIR/rag.json" -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -d '{"question":"特应性皮炎的常见症状有哪些？","source":"all","top_k":5}' \
  "$BASE/api/rag/answer")"
[[ "$RAG_STATUS" == "200" ]] || { cat "$SMOKE_DIR/rag.json" >&2; exit 1; }
python3 - "$SMOKE_DIR/rag.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
assert payload["provider_name"] == "deterministic"
assert "非诊断结论、需结合临床。" in payload["answer"]
PY

# reviewer-a 创建 task。只写用户名，curl 会从终端安全提示输入密码，
# 不要把 Basic Auth 密码写入 shell history 或命令行参数。
CREATE_STATUS="$(curl -sS --user reviewer-a \
  -o "$SMOKE_DIR/create.json" -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -d '{"query":"黄芪","analysis_type":"herb","research_protocol":{"disease":"atopic_dermatitis","phenotype":"特应性皮炎伴2型炎症与皮肤屏障异常","species":"Homo sapiens","evidence_policy":"direct_human_first","query_date":"2026-07-11"}}' \
  "$BASE/api/network/analyze")"
[[ "$CREATE_STATUS" == "202" ]] || { cat "$SMOKE_DIR/create.json" >&2; exit 1; }
TASK_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["task_id"])' "$SMOKE_DIR/create.json")"
[[ -n "$TASK_ID" ]] || { echo "network task id is empty" >&2; exit 1; }

# nginx 必须覆盖客户端伪造的 reviewer header；reviewer-a 仍以自己的 owner 身份访问。
assert_status 200 --user reviewer-a -H "X-Qiyan-Reviewer: reviewer-b" \
  "$BASE/api/network/result/$TASK_ID"

# reviewer-b 对 reviewer-a 的 task/result/report 都必须得到 404。
assert_status 404 --user reviewer-b "$BASE/api/network/result/$TASK_ID"
assert_status 404 --user reviewer-b "$BASE/api/network/result/$TASK_ID/report"

# reviewer-a 再轮询并导出，验证 owner 自己的完整链路。
assert_status 200 --user reviewer-a "$BASE/api/network/result/$TASK_ID"
assert_status 200 --user reviewer-a "$BASE/api/network/result/$TASK_ID/report"
```

> 各端点确切路径与 payload 见 `README.md` 的 curl 示例。务必确认 RAG 返回 `provider_name="deterministic"`（证明没误开真实 LLM）且免责声明字节一致。

---

## 6. 身份与 token 边界

- 每位 reviewer 只获得自己的 Basic Auth 用户名/密码；不要共享账号。撤销单人访问：`sudo htpasswd -D /etc/nginx/qiyan-reviewers.htpasswd reviewer-a && sudo nginx -s reload`。
- reviewer 用户名必须已经是 canonical 小写 slug（`a-z`、数字、`.`、`_`、`-`，最多 64 字符），例如 `reviewer-a`；后端不会把大写账号静默折叠成小写。该用户名会成为私有 runtime 对象的稳定 `owner_id`；重命名账号前必须先迁移其对象。
- `/var/log/nginx/qiyan-trial-access.log` 记录 `$remote_user`、method、URI path 与后端 `X-Request-ID`，用于把操作归因到 reviewer；该 qiyan-trial access log 不记录 query string、`Authorization` 或内部 token。日志权限为 0640，并按日轮转、最多保留 14 份；这不等于 nginx error log 永远不含 query。
- `QIYAN_ACCESS_TOKENS` 现在是 nginx→FastAPI 的**共享内部防线**，不是 reviewer 身份。它只存在于 root/operator 配置。轮换时必须同时更新 backend env、frontend env 与 nginx map，然后依次执行 `sudo nginx -t`、`sudo systemctl restart qiyan-api qiyan-web`、`sudo systemctl reload nginx`；三处值未同步前不得恢复 reviewer 流量。
- nginx 必须在 `/api/` 覆盖 `X-Qiyan-Reviewer` 为 `$remote_user`；FastAPI 只在共享内部 token 已通过、且 8000 保持 loopback 的信任链上接受该身份。客户端 body、query 参数或浏览器自带同名 header 都不能决定 owner。
- 后端 middleware 继续支持脚本或本机直连 API 的 `X-Access-Token`，但公网 8000 必须只监听 `127.0.0.1`，reviewer 不得绕过 nginx。
- Basic Auth 必须只在 HTTPS 上使用。当前 network task 已基于该身份做 owner 隔离；若试用范围扩大、需要 MFA/SSO 或更复杂角色权限，应迁移到身份感知代理或正式会话认证。

---

## 7. 数据隔离与轮次重置

- runtime 写入 `backend/data/runtime/`（sqlite/JSON），上传 PDF 写入 `backend/uploads/`，均 gitignored、不是生产库。
- network task 已按 reviewer `owner_id` 隔离：非 owner 查询 result/report 返回 404，且不会推进任务状态；旧 runtime 中没有 owner 的 task 不会自动归给任何 reviewer。
- PDF、文献 PDF metadata、解析结果与 uploaded PDF RAG chunk 仍共享同一 runtime 命名空间。在这条完整保密链落地前，只能上传**所有参与 reviewer 均有权查看**的公开或已授权材料；禁止上传患者资料、个人信息、保密材料或仅单人获授权的版权 PDF。若无法接受共享可见性，应为每位 reviewer 部署独立实例或暂停 PDF 上传。
- 每轮试用前重置：`sudo systemctl stop qiyan-api`，备份或清空 `data/runtime/` 与 `uploads/`，再 `start`。
- 演示 seed 文献带 `record_origin=seed_sample`，**不可**当真实外部数据库文献引用——这点要在试用须知里讲清。

---

## 8. 试用须知里必须写清的边界

1. AI 回答是 **deterministic 检索式**，不是真实大模型；每条结论附免责声明，**不替代诊断**。
2. 网络药理学是 **mock 演示数据**（`/network` 页面顶部有边界 note）。
3. 文献含演示 seed + PubMed 实时同步两类，`记录来源`标签区分。
4. 数据不外发；上传 PDF 仅本机解析预览，扫描件可能回退占位说明。network task 已逐 reviewer 隔离，但 PDF、解析预览和 uploaded PDF RAG 证据仍共享可见性，只能使用全体均获授权的材料。

---

## 9. 拆除

```bash
sudo systemctl disable --now qiyan-web qiyan-api
sudo rm -f /etc/nginx/sites-enabled/qiyan /etc/nginx/sites-available/qiyan
sudo rm -f /etc/nginx/qiyan-reviewers.htpasswd /etc/nginx/conf.d/qiyan-backend-token.conf
sudo rm -f /etc/qiyan/backend.env /etc/qiyan/frontend.env
sudo rmdir /etc/qiyan 2>/dev/null || true

sudo rm -f /etc/systemd/system/qiyan-api.service /etc/systemd/system/qiyan-web.service
sudo systemctl daemon-reload

sudo rm -f /etc/fail2ban/filter.d/qiyan-basic-auth.conf
sudo rm -f /etc/fail2ban/jail.d/qiyan-basic-auth.local
sudo systemctl restart fail2ban

sudo rm -f /etc/logrotate.d/qiyan-trial /var/log/nginx/qiyan-trial-access.log*

# 先删除所有站点/token 配置，再做最终语法检查与 reload，确保运行中的 nginx
# 不再保留旧 map/token。若 nginx -t 失败，不要跳过修复后再次 reload。
sudo nginx -t && sudo systemctl reload nginx

# 如需彻底清理：sudo rm -rf /opt/qiyan；撤销证书：sudo certbot delete --cert-name DOMAIN
```

---

## 已知限制（本 runbook 范围内）

| 项 | 限制 | 影响 |
|---|---|---|
| 并发 | SQLite repository 已用进程内 `RLock` 串行共享 connection；仍不支持多 worker | 保持单进程；扩容前迁移到经并发验证的数据库连接模型 |
| 身份系统 | nginx Basic Auth，无 MFA/SSO | 仅适合 HTTPS 下的 2-5 人限时试用；每人独立账号并定期撤销 |
| 对象级隔离 | network task 已按 reviewer 隔离；PDF、文献 PDF metadata、解析结果与 uploaded PDF RAG chunk 仍共享 | PDF 只允许全体均可查看的材料；敏感试用需独立实例或先完成 PDF 独立对象模型 |
| 错误监控 | 无 Sentry/外部上报（安全审查 HIGH-8 推迟项） | 线上前端错误只在浏览器；后端异常进 systemd journal |
| 真实 LLM | 不启用 | 答案质量是 deterministic 基线，非真实模型水平 |

---

**状态**：runbook 就绪，等真人 reviewer 招募（§外部依赖）。配套证据包用 `scripts/collect-internal-preview-evidence.ps1` 本地生成（冻结可信构建 + request-id）。
