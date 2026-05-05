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

Required environment variable:

```text
VITE_API_BASE_URL
```

Optional workspace selector:

```text
VITE_ORGANIZATION_ID
```

The frontend should be deployed as a static site and pointed at the backend URL for the same environment.

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
- dashboard loads successfully
- create campaign works
- save notes works
- approve campaign works

## Rollout Plan

### Phase 1: Demo Hosting

Use:

- backend on Render or Railway
- frontend on Vercel or Netlify
- SQLite only if there is a single app instance and limited internal use

This is the fastest way to get a shareable MVP online.

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

- `main.py serve` defaults to `127.0.0.1:8000`, but deployed environments should set explicit host and port behavior through the platform runtime.
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
