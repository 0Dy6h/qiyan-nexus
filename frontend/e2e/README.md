# Playwright E2E (A4)

Baseline E2E for Qiyan Nexus. One main-path spec covering `/literature → 详情 → /rag → 问答 → citation`, plus the load-bearing disclaimer.

## First-time setup (per machine)

```bash
cd frontend
pnpm install                              # picks up @playwright/test devDep
pnpm exec playwright install chromium     # ~115MB; lands in ~/.cache/ms-playwright
sudo pnpm exec playwright install-deps    # system libs: libnspr4, libnss3, libxss1, libasound2, ...
```

The `install-deps` step requires root. In WSL / Linux dev environments without sudo, install the libs manually:

```bash
sudo apt-get install -y libnspr4 libnss3 libxss1 libasound2 libxshmfence1 libgbm1
```

In CI, prefer `pnpm exec playwright install --with-deps chromium` inside an image that already has apt + sudo.

## Run

```bash
cd frontend
pnpm e2e
```

`playwright.config.ts` `webServer` starts:
- backend: `cd ../backend && .venv/bin/fastapi dev app/main.py --port 8000` with `LITERATURE_RUNTIME_STATE_PATH=/tmp/qiyan-e2e-runtime.json`, `UPLOAD_STORAGE_DIR=/tmp/qiyan-e2e-uploads`, `QIYAN_ACCESS_TOKENS=''` (open mode, isolated runtime state)
- frontend: `pnpm dev` on port 3000

If a dev server is already running on 3000 / 8000, `reuseExistingServer: !process.env.CI` skips relaunching it locally; CI always starts fresh.

## Scope

This directory is intentionally NOT covered by `pnpm test` (which is the `node:test`+`tsx` suite) or `pnpm typecheck` exclusions — Playwright's own runner picks up `*.spec.ts` here. tsc still type-checks the files because the root tsconfig includes `**/*.ts`.

When adding specs, prefer:
- `getByRole` over CSS / XPath
- regex names that survive minor copy churn (`/查看详情/`, not `"查看详情 →"`)
- isolated runtime state via env vars (do NOT seed via direct file writes)
