# Ad Generation Engine

This repo contains a dependency-light MVP for generating structured ad bundles from a campaign brief.

## Documentation

- [system_overview](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/system_overview>)
- [docs/user-guide.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/user-guide.md>)
- [docs/architecture.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/architecture.md>)
- [docs/api.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/api.md>)
- [docs/development.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/development.md>)
- [docs/deployment.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/deployment.md>)
- [docs/investor-playbook.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/investor-playbook.md>)

## What it does

- validates a campaign brief
- creates a creative strategy plan
- generates channel-specific ad variants
- attaches image prompts
- runs a lightweight review pass

## Run it

Use the built-in sample brief:

```powershell
python main.py
```

Use your own brief:

```powershell
python main.py sample_brief.json
```

Run the API server:

```powershell
python main.py serve
```

The server runs the canonical FastAPI app through Uvicorn. API work lives in
[src/ad_engine/fastapi_app.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/fastapi_app.py>).

Use a custom host or port when needed:

```powershell
python main.py serve 127.0.0.1 8011
```

The backend automatically loads local settings from [\.env](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/.env>) when present.

Use [\.env.example](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/.env.example>) as the tracked template for local configuration.

Run the API server with SQLite persistence:

```powershell
$env:AD_ENGINE_DB_BACKEND = 'sqlite'
$env:AD_ENGINE_SQLITE_PATH = '.\\data\\ad_engine.db'
python main.py serve
```

Run the dashboard:

```powershell
npm install
npm run dev
```

If `5173` is already in use, start Vite on a different port:

```powershell
npm run dev -- --host 127.0.0.1 --port 4174
```

## Project shape

- [system_overview](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/system_overview>)
- [main.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/main.py>)
- [src/ad_engine](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine>)
- [web/src](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/web/src>)

## API

- `GET /health`: confirm the service is running
- `POST /bundles`: submit a brief and create a stored bundle
- `GET /bundles/{id}`: retrieve the generated bundle payload for a campaign
- `GET /campaigns`: list campaigns in memory
- `GET /campaigns/{id}`: fetch campaign details, status, and bundle
- `PATCH /campaigns/{id}`: update campaign status, notes, or metadata
- `PATCH /campaigns/{id}/variants/{index}`: edit generated variant copy and prompt text
- `POST /campaigns/{id}/variants/{index}/generate-image`: generate or retry one variant image
- `POST /campaigns/{id}/approve`: mark a campaign approved
- `GET /campaigns/{id}/export.txt`: export a campaign as plain text

`GET /health` also reports the active database backend.

Create a bundle:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/bundles -ContentType 'application/json' -InFile 'sample_brief.json'
```

Fetch a bundle:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/bundles/<bundle-id>
```

List campaigns:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/campaigns
```

Update a campaign:

```powershell
Invoke-RestMethod -Method Patch -Uri http://127.0.0.1:8000/campaigns/<campaign-id> -ContentType 'application/json' -Body '{"approval_notes":"Needs final stakeholder review","metadata":{"owner":"Theo"}}'
```

Approve a campaign:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/campaigns/<campaign-id>/approve -ContentType 'application/json' -Body '{"approval_notes":"Approved for launch"}'
```

Edit a generated variant:

```powershell
Invoke-RestMethod -Method Patch -Uri http://127.0.0.1:8000/campaigns/<campaign-id>/variants/0 -ContentType 'application/json' -Body '{"headline":"Updated launch headline","cta":"Book now"}'
```

## Providers

The engine now resolves generation through pluggable planning, copy, and image providers.

- `AD_ENGINE_PLANNING_PROVIDER=rule_based`
- `AD_ENGINE_COPY_PROVIDER=rule_based`
- `AD_ENGINE_IMAGE_PROVIDER=prompt_template`
- `AD_ENGINE_IMAGE_PROVIDER=openai_images`

These defaults preserve the current local behavior while moving the engine onto provider interfaces. New LLM and image backends can be added by implementing the provider protocols in [src/ad_engine/providers.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/providers.py>) and registering them in `build_provider_stack()`.

`openai_images` now uses the OpenAI Images API and saves generated files under `data/generated_assets` by default. Configure it with:

- `OPENAI_API_KEY`
- `OPENAI_IMAGE_MODEL=gpt-image-2`
- `OPENAI_IMAGE_SIZE=1024x1024`
- `OPENAI_IMAGE_QUALITY=medium`
- `OPENAI_IMAGE_BACKGROUND=auto`
- `OPENAI_IMAGE_OUTPUT_FORMAT=png`
- `OPENAI_IMAGE_OUTPUT_DIR=./data/generated_assets`
- `OPENAI_IMAGE_GENERATE_DURING_CREATE=false`

Campaign creation stays prompt-only by default, even when `AD_ENGINE_IMAGE_PROVIDER=openai_images`.
Use the dashboard's per-variant image button, or call `POST /campaigns/{id}/variants/{index}/generate-image`,
to generate selected images. Set `OPENAI_IMAGE_GENERATE_DURING_CREATE=true` only when you intentionally want
campaign creation to block on every variant image.

Example:

```powershell
$env:AD_ENGINE_IMAGE_PROVIDER = 'openai_images'
$env:OPENAI_API_KEY = 'your-api-key'
$env:OPENAI_IMAGE_MODEL = 'gpt-image-2'
python main.py serve
```

Use `AD_ENGINE_IMAGE_PROVIDER=prompt_template` when you want local prompt generation without paid image calls.

## Frontend

The React dashboard is a lightweight SaaS MVP shell with:

- campaign creation form
- campaign list view
- campaign detail, copy editing, export, and approval workspace

Set a custom API base URL when needed:

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
npm run dev
```

This matters any time the backend is not running on the default `8000` port. For example:

```powershell
python main.py serve 127.0.0.1 8011
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8011'
npm run dev -- --host 127.0.0.1 --port 4174
```

Vite also reads `VITE_` variables from the repo `.env` file by default.

If the dashboard shows `Campaign workspace is offline` or `Failed to fetch`, verify that:

- the API server is actually running on the port in `VITE_API_BASE_URL`
- the Vite dev server did not move to a different port because `5173` was already occupied
- your browser is pointed at the Vite URL printed in the terminal

## Persistence

Campaign storage now supports two backends:

- `memory`: process-local storage, cleared on restart
- `sqlite`: durable local storage in a SQLite database
- `postgres`: shared production-style storage using `psycopg`

Environment variables:

- `AD_ENGINE_DB_BACKEND=memory|sqlite|postgres`
- `AD_ENGINE_SQLITE_PATH=.\data\ad_engine.db`
- `AD_ENGINE_POSTGRES_DSN=postgresql://...`

Campaign records include `organization_id`. API clients can scope requests with
the `X-Organization-ID` header; the dashboard sends `VITE_ORGANIZATION_ID` and
defaults to `default` for local single-workspace development.

For staging or production, enable the API-key guard:

```powershell
$env:AD_ENGINE_REQUIRE_API_KEY = 'true'
$env:AD_ENGINE_API_KEYS = 'secret-key:workspace-a'
$env:VITE_API_KEY = 'secret-key'
$env:VITE_ORGANIZATION_ID = 'workspace-a'
```

## Good next steps

1. Add campaign filtering, deletion, and audit history.
2. Add concrete remote LLM and image provider implementations behind the new provider interfaces.
3. Store real generated image assets and references alongside campaign bundles.
