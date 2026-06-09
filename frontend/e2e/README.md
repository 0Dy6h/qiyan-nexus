# Playwright E2E

Browser E2E coverage for Qiyan Nexus internal preview. Current specs cover the literature/RAG main path, PDF upload + eval + network mock preview flow, network graph keyboard accessibility, and literature data-source switching.

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

Token profile smoke:

```powershell
cd frontend
$env:QIYAN_E2E_ACCESS_TOKEN="qiyan-e2e-token"
pnpm e2e
Remove-Item Env:\QIYAN_E2E_ACCESS_TOKEN
```

Repo-level equivalent:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E -E2ETokenProfile
```

`playwright.config.ts` `webServer` starts:
- backend: `node ./e2e/start-backend.mjs`, which prefers `../backend/.uv-test-venv` and falls back to `.venv` / `python`; it runs uvicorn on `127.0.0.1:8000` with isolated temp runtime paths. Open mode sets `QIYAN_ACCESS_TOKENS=''`; token mode maps `QIYAN_E2E_ACCESS_TOKEN` to `QIYAN_ACCESS_TOKENS`.
- frontend: `pnpm dev` on port 3000. Token mode also maps `QIYAN_E2E_ACCESS_TOKEN` to `NEXT_PUBLIC_QIYAN_ACCESS_TOKEN`.

If a dev server is already running on 3000 / 8000, open-mode local runs can reuse it. Token-mode runs disable server reuse so Playwright does not accidentally test against an already-running open-mode server.

## Scope

This directory is intentionally NOT covered by `pnpm test` (which is the `node:test`+`tsx` suite) or `pnpm typecheck` exclusions — Playwright's own runner picks up `*.spec.ts` here. tsc still type-checks the files because the root tsconfig includes `**/*.ts`.

When adding specs, prefer:
- `getByRole` over CSS / XPath
- regex names that survive minor copy churn (`/查看详情/`, not `"查看详情 →"`)
- isolated runtime state via env vars (do NOT seed via direct file writes)
