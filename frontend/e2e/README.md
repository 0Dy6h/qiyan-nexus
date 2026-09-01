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

Repo-level equivalent:

```powershell
.\scripts\verify-local.ps1 -IncludeE2E
```

`playwright.config.ts` `webServer` starts:
- backend: `node ./e2e/start-backend.mjs`, which prefers `../backend/.uv-test-venv` and falls back to `.venv` / `python`; it runs uvicorn on `127.0.0.1:8000` with isolated temp runtime paths and explicitly sets `QIYAN_ACCESS_TOKENS=''`.
- frontend: `pnpm dev` on port 3000 with only the non-secret `NEXT_PUBLIC_API_BASE_URL` override.

If a dev server is already running on 3000 / 8000, local runs can reuse it outside CI. Browser E2E is intentionally open-mode: the frontend never receives a backend token. Backend token middleware remains covered by backend tests and direct API smoke; cloud Basic Auth is an nginx deployment boundary and must be validated against the deployed proxy.

## Scope

This directory is intentionally NOT covered by `pnpm test` (which is the `node:test`+`tsx` suite) or `pnpm typecheck` exclusions — Playwright's own runner picks up `*.spec.ts` here. tsc still type-checks the files because the root tsconfig includes `**/*.ts`.

When adding specs, prefer:
- `getByRole` over CSS / XPath
- regex names that survive minor copy churn (`/查看详情/`, not `"查看详情 →"`)
- isolated runtime state via env vars (do NOT seed via direct file writes)
