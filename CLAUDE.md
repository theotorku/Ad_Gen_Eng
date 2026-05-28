# CLAUDE.md

Guidance for working in this repository.

## What this is

Ad Generation Engine — turns a campaign brief into channel-specific ad copy and
optional generated images. Two surfaces in one repo:

- **Backend**: FastAPI app in `src/ad_engine/`, CLI/server entry `main.py`.
- **Frontend**: React + Vite dashboard in `web/src/` (entry `web/src/main.tsx`),
  with root-level `index.html` and Vite/TS config.

## Repo layout

| Path | Contents |
|---|---|
| `src/ad_engine/` | Backend: `fastapi_app.py`, engine, providers, store, auth, assets, config |
| `main.py` | Backend CLI — `python main.py serve` runs FastAPI via Uvicorn |
| `web/src/` | Frontend source (`App.tsx`, `api.ts`, `components/`, `types.ts`, `constants.ts`) |
| `tests/` | Backend pytest suite |
| `web/src/**/*.test.tsx` | Frontend vitest suite |
| `e2e/` | Playwright end-to-end tests |
| `docs/` | Deployment, architecture, API, dev guides |

## Commands

Run frontend commands from the repo root (Vite/vitest configs live there).

```bash
# Frontend
npm run dev          # vite dev server (5173)
npm run build        # tsc -b && vite build -> dist/
npm run test:run     # vitest run (CI uses this)
npm run typecheck    # tsc --noEmit -p tsconfig.app.json
npm run test:e2e     # playwright

# Backend
python main.py serve            # local API on 127.0.0.1:8000
python -m pytest tests/         # backend tests
pip install -r requirements-dev.txt   # test deps (includes httpx for starlette TestClient)
```

Backend tests use starlette's `TestClient`, which **requires `httpx`** — it must
stay in `requirements-dev.txt` or CI collection fails.

## CI (`.github/workflows/ci.yml`)

Runs on push and PR to `main`. Two jobs, **both must pass**:

- **Backend (pytest)** — installs `requirements-dev.txt`, runs `pytest tests/ -v`.
- **Frontend (typecheck + vitest)** — `npm ci`, typecheck, `test:run`, `build`.

## Deployment

Push to `main` auto-deploys both surfaces — **no manual deploy commands needed.**

| Surface | Platform | Trigger | Notes |
|---|---|---|---|
| Frontend | Vercel (`ad-gen-eng-kfso`) | push to `main` | Vite preset, `vercel.json`, output `dist/` |
| Backend | Railway (`ad-generation-engine`) | push to `main`, **gated on CI** | Dockerfile + `railway.json`, healthcheck `/health` |

Both projects are GitHub-connected to `theotorku/Ad_Gen_Eng`. Railway is set to
**"Wait for CI"**, so a red CI check holds the backend deploy in `WAITING` and it
won't promote until checks pass.

Live URLs:

- Production frontend: `https://www.proplanadengine.com` (also `ad-gen-eng-kfso.vercel.app`)
- Backend API: `https://ad-generation-engine-production.up.railway.app`

Manual deploy fallback (rarely needed): `railway up --detach`. Vercel previews are
behind Vercel deployment protection (require Vercel login to open).

See `docs/deployment.md` for the full runbook, env vars, and persistence strategy.

## Key gotchas

- **CORS**: backend allowlist is `AD_ENGINE_CORS_ORIGINS` (exact match) plus optional
  `AD_ENGINE_CORS_ORIGIN_REGEX` (passed to starlette `allow_origin_regex`) — the regex
  exists to match hashed Vercel preview subdomains. See `_load_cors_origins` in
  `src/ad_engine/fastapi_app.py`.
- **Authenticated assets**: `GET /generated-assets/{file}` and `/brand-logos/{file}`
  require the `X-API-Key` header, so a plain `<img src>` gets 401/ORB-blocked. The UI
  fetches with auth and wraps in `URL.createObjectURL` (`fetchAssetBlobUrl` in
  `web/src/api.ts`). Any new image surface must use this pattern and revoke the blob URL.
- **`VITE_*` vars are inlined at build time** — changing them requires a frontend rebuild/redeploy.
- **Clerk auth**: production instance serves from custom domain `clerk.proplanadengine.com`,
  which needs five CNAME records in Cloudflare DNS (`clerk`, `accounts`, `clkmail`,
  `clk._domainkey`, `clk2._domainkey` → `*.clerk.services`). Keep them **DNS-only (unproxied)**
  and **do not enable "Flatten all CNAMEs"** in Cloudflare — flattening subdomain CNAMEs
  breaks Clerk's domain verification.
