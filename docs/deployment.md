# Deployment Guide

## Overview

This project deploys cleanly as two separate surfaces:

- a Python backend API
- a static React frontend built with Vite

For local work, SQLite is a good default. For any shared, staged, or production environment, treat the backend, database, and asset storage as independent concerns.

## Recommended Topology

Use this baseline layout:

- frontend: static hosting on Vercel, Netlify, Cloudflare Pages, or Azure Static Web Apps
- backend: containerized web service on Render, Railway, Fly.io, Azure App Service, or a similar host
- database: managed Postgres for shared environments
- generated assets: object storage such as S3, R2, or Azure Blob Storage

Keep SQLite only for local development and short-lived demos.

## Deployment Targets

### Frontend

Build command:

```powershell
npm run build
```

Output directory:

```text
dist
```

Required environment variables:

```text
VITE_API_BASE_URL
VITE_API_KEY
```

Optional workspace selector:

```text
VITE_ORGANIZATION_ID
```

`VITE_*` variables are inlined into the static bundle at build time, so any change requires a fresh build and redeploy. The frontend should be deployed as a static site and pointed at the backend URL for the same environment.

### Backend

The current local server entrypoint is:

```powershell
python main.py serve
```

That starts the FastAPI app through Uvicorn. For production, wrap the backend in a proper container image or use the platform's Python web-service runtime.

Minimum runtime needs:

- Python runtime compatible with the repo
- dependencies from `requirements.txt`
- access to environment variables
- writable temp or asset directory only if local asset storage is still enabled
- network access to any external providers you enable

## Environment Strategy

Create at least three environments:

- `dev`: local and individual testing
- `staging`: pre-release verification with production-like settings
- `prod`: live environment

Each environment should have its own:

- backend URL
- frontend URL
- database
- secrets
- generated asset bucket or storage location

Do not share SQLite files across environments.

## Configuration

### Backend Variables

Common backend settings:

- `AD_ENGINE_DB_BACKEND`
- `AD_ENGINE_SQLITE_PATH`
- `AD_ENGINE_POSTGRES_DSN`
- `AD_ENGINE_POSTGRES_POOL_SIZE`
- `AD_ENGINE_REQUIRE_API_KEY`
- `AD_ENGINE_API_KEYS`
- `AD_ENGINE_PLANNING_PROVIDER`
- `AD_ENGINE_COPY_PROVIDER`
- `AD_ENGINE_IMAGE_PROVIDER`
- `OPENAI_API_KEY`
- `OPENAI_IMAGE_MODEL`, defaulting to `gpt-image-2`
- `OPENAI_IMAGE_SIZE`
- `OPENAI_IMAGE_QUALITY`
- `OPENAI_IMAGE_BACKGROUND`
- `OPENAI_IMAGE_OUTPUT_FORMAT`
- `OPENAI_IMAGE_OUTPUT_DIR`
- `OPENAI_IMAGE_GENERATE_DURING_CREATE`

Suggested environment defaults:

- local: `AD_ENGINE_DB_BACKEND=sqlite`
- local without image costs: `AD_ENGINE_IMAGE_PROVIDER=prompt_template`
- local with generated images: `AD_ENGINE_IMAGE_PROVIDER=openai_images` and `OPENAI_IMAGE_MODEL=gpt-image-2`
- SaaS-safe image flow: keep `OPENAI_IMAGE_GENERATE_DURING_CREATE=false` and generate selected images per variant
- staging: `AD_ENGINE_DB_BACKEND=postgres` with a managed database
- production: `AD_ENGINE_DB_BACKEND=postgres`; avoid SQLite and local asset-only storage
- staging/prod auth: `AD_ENGINE_REQUIRE_API_KEY=true` and `AD_ENGINE_API_KEYS=key:organization_id`

### Frontend Variables

The main frontend variable is:

- `VITE_API_BASE_URL`
- `VITE_ORGANIZATION_ID`
- `VITE_API_KEY`

Examples:

```text
http://127.0.0.1:8000
https://staging-api.example.com
https://api.example.com
```

The frontend and backend must be paired correctly by environment. If they are not, the dashboard will appear online but fail during fetches or show the workspace as offline.

## Persistence Strategy

### Local and Demo

Use SQLite:

```text
AD_ENGINE_DB_BACKEND=sqlite
AD_ENGINE_SQLITE_PATH=./data/ad_engine.db
```

This is simple and works well for one-machine development and demo flows.

### Shared and Production

Use a managed relational database, ideally Postgres.

Why:

- shared access across app instances
- safer backups and restore paths
- easier horizontal scaling
- better operational visibility

The store abstraction includes a Postgres backend selected with:

```text
AD_ENGINE_DB_BACKEND=postgres
AD_ENGINE_POSTGRES_DSN=postgresql://...
```

Install the `psycopg[binary]` dependency in the backend runtime.

## Asset Strategy

When `openai_images` is enabled, generated assets are currently written to local disk.

Campaign creation should stay prompt-only in shared environments. Generate selected
variant images through the per-variant endpoint/UI so one campaign does not block
on many image requests or spend on every draft variant. `OPENAI_IMAGE_GENERATE_DURING_CREATE=true`
is available for demos, but should stay off for SaaS usage.

That is fine for local development. It is not a strong production strategy because:

- container filesystems may be ephemeral
- multiple instances will not share files
- scaling and retention become harder

Recommended production path:

1. generate the asset
2. upload it to object storage
3. store only the asset URL or object key in the campaign record
4. serve it through signed URLs or a stable public asset path

Also account for OpenAI Images API cost, rate limits, and latency in staging and production. One campaign can generate multiple variants, and each variant may create a separate image.

## Security and Secrets

Keep these rules in place from the start:

- never commit real secrets to `.env.example`
- store real secrets only in host-managed secret stores or environment settings
- use separate keys for staging and production
- rotate provider keys if they were ever committed to source control

Sensitive settings include:

- `OPENAI_API_KEY`
- future database credentials
- future storage credentials

## CORS and Network Policy

The local API is permissive to keep development simple.

For deployed environments:

- restrict allowed frontend origins to the actual frontend domains
- keep staging and production origins separate
- avoid wildcard CORS once the app is externally reachable
- require API keys until a full user identity provider is connected

## Build and Release Flow

Recommended CI pipeline:

1. install dependencies
2. run backend syntax verification
3. run backend sample generation
4. run frontend build
5. deploy backend
6. verify backend health
7. deploy frontend
8. run a smoke test against the deployed app

Suggested commands:

```powershell
python -m compileall src main.py
python main.py sample_brief.json
npm run build
```

Recommended smoke checks:

- `GET /health` returns `status: ok`
- dashboard loads successfully (including `/favicon.ico`)
- create campaign works
- generate image works and the variant card renders the image (blob URL)
- save notes works
- approve campaign works and the action button disables

## Rollout Plan

### Phase 1: Demo Hosting

Use:

- backend on Render or Railway
- frontend on Vercel or Netlify
- SQLite only if there is a single app instance and limited internal use

This is the fastest way to get a shareable MVP online.

#### Phase 1 Runbook (Railway + Vercel)

The repo ships with concrete config for this stack:

- `Dockerfile` and `.dockerignore`: backend image
- `railway.json`: Railway build, healthcheck, single-instance deploy
- `vercel.json`: Vite framework preset for the dashboard
- `public/favicon.ico`: static asset shipped to the Vercel build output

Live Phase 1 environment:

- backend: `https://ad-generation-engine-production.up.railway.app`
- frontend: `https://ad-gen-eng-kfso.vercel.app`

Backend (Railway):

1. Create a new Railway project from this GitHub repo. Railway picks up `railway.json` and uses the Dockerfile.
2. Attach a volume mounted at `/app/data`. SQLite and generated assets live here. The Dockerfile entrypoint `chown`s `/app/data` to the non-root `app` user on every boot so the volume is writable on first attach.
3. Set service variables:
   - `AD_ENGINE_CORS_ORIGINS` = the Vercel frontend URL (no trailing slash, no wildcards once the frontend domain is known)
   - `AD_ENGINE_REQUIRE_API_KEY` = `true`
   - `AD_ENGINE_API_KEYS` = `<random-key>:default` (the `:default` suffix scopes the key to the `default` organization)
   - `AD_ENGINE_DB_PATH` = `/app/data/ad_engine.db`
   - `AD_ENGINE_ASSET_DIR` = `/app/data/generated_assets`
   - `AD_ENGINE_IMAGE_PROVIDER` = `openai_images` (optional)
   - `OPENAI_API_KEY` only if `AD_ENGINE_IMAGE_PROVIDER=openai_images`
4. Generate a public domain for the service. Note the URL.
5. Deploy. The `/health` endpoint must return 200 before Railway routes traffic.

Frontend (Vercel):

1. Import the same GitHub repo. Vercel reads `vercel.json` and uses the Vite preset.
2. Set project environment variables:
   - `VITE_API_BASE_URL` = the Railway service URL from above
   - `VITE_API_KEY` = **only the raw key, without the `:default` org suffix.** This is the value the dashboard sends in the `X-API-Key` header; the backend looks the org up from the key.
   - `VITE_ORGANIZATION_ID` = `default`
3. Deploy. Vite inlines `VITE_*` vars at build time, so changing them requires a redeploy without build cache.

Authenticated assets:

- `GET /generated-assets/{filename}` requires the `X-API-Key` header. Browsers will not attach custom headers to `<img src=...>` requests, so a plain `<img>` against this endpoint returns 401 and is then blocked by Chrome's Opaque Response Blocking (`ERR_BLOCKED_BY_ORB`).
- The dashboard works around this in `web/src/components/VariantCard.tsx`: it calls `fetchAssetBlobUrl` from `web/src/api.ts`, which `fetch`es the asset with the auth header, wraps the response in `URL.createObjectURL`, and revokes the object URL on unmount. Any future surface that displays generated images must use the same pattern unless `/generated-assets` is moved behind signed URLs or object storage.

Phase 1 smoke test (run after each redeploy):

1. `GET https://<backend>/health` returns `status: ok`.
2. From the deployed frontend, submit a brief and confirm 9 variants are returned.
3. Click "Generate image" on a variant. The card should switch from `prompt only` to `generated` and the image should render (blob URL, not 401).
4. Approve the campaign. The primary action should relabel to `Approved` and disable.
5. Refresh the page. The campaign, variants, and image should all persist (volume-backed SQLite + asset directory).

Phase 1 constraints (accept these or move to Phase 2):

- one backend replica only (SQLite cannot serve multiple instances)
- generated assets live on the Railway volume, not object storage
- a volume detach or service rebuild without volume reattachment loses data
- API keys are baked into the Vite bundle at build time; rotating `AD_ENGINE_API_KEYS` requires updating `VITE_API_KEY` and redeploying the frontend

### Phase 2: Shared Internal Environment

Add:

- managed Postgres
- restricted CORS
- staging environment
- persistent asset storage if image generation is enabled

This phase is the right time to formalize environment-specific secrets and logs.

### Phase 3: Production Readiness

Add:

- request and error monitoring
- structured logs
- rate limiting on generation routes
- authentication and authorization
- backup and restore procedures
- asset retention policy
- background jobs for slow image generation requests

## Platform Recommendation

If you want the lowest-friction first deployment:

- frontend: Vercel
- backend: Render or Railway
- database: Neon Postgres
- assets: S3 or Cloudflare R2

That stack is enough for a practical MVP without heavy operations work.

## Repo-Specific Notes

- `main.py serve` defaults to `127.0.0.1:8000` for local dev. When `PORT` is set in the environment (Railway, Render, Fly), the server binds to `0.0.0.0` automatically. `HOST` can override the bind address explicitly.
- The frontend can be served on any Vite or static-host port as long as `VITE_API_BASE_URL` points to the matching backend.
- If a local or shared machine already uses `8000` or `5173`, use alternate ports and keep the frontend/backend pair aligned.

## Pre-Launch Checklist

- secrets removed from tracked templates
- backend deployed and reachable
- frontend deployed and pointed at the correct backend
- database selected for the target environment
- asset storage decision made
- smoke test completed
- logs and failure visibility confirmed
