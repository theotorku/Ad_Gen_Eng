# Development Guide

## Local Setup

Install Python development dependencies before running the API or tests:

```powershell
pip install -r requirements-dev.txt
```

Common commands:

```powershell
python main.py
python main.py sample_brief.json
python main.py serve
python main.py serve 127.0.0.1 8011
$env:AD_ENGINE_DB_BACKEND = 'sqlite'; python main.py serve
$env:AD_ENGINE_DB_BACKEND = 'postgres'; $env:AD_ENGINE_POSTGRES_DSN = 'postgresql://user:pass@localhost:5432/ad_engine'; python main.py serve
$env:AD_ENGINE_REQUIRE_API_KEY = 'true'; $env:AD_ENGINE_API_KEYS = 'local-secret:default'; python main.py serve
python -m compileall src main.py
npm run dev
npm run dev -- --host 127.0.0.1 --port 4174
npm run build
```

## Working Model

There are two main development surfaces:

- generation pipeline work in `src/ad_engine`
- API work in `src/ad_engine/api.py` and `src/ad_engine/store.py`
- dashboard work in `web/src`

When changing generation behavior, the usual path is:

1. update domain models if the payload shape changes
2. update or add providers
3. run the CLI with `sample_brief.json`
4. verify review output still makes sense

When changing the API, the usual path is:

1. start the server with `python main.py serve`
2. exercise endpoints with `Invoke-RestMethod`
3. include `X-Organization-ID` when testing workspace isolation
4. include `X-API-Key` when `AD_ENGINE_REQUIRE_API_KEY=true`
5. verify the in-memory campaign lifecycle

If `8000` is already occupied by another local service, start the API on an alternate port and use that same port in any frontend `VITE_API_BASE_URL` override.

When changing persistence behavior, the usual path is:

1. run once with `AD_ENGINE_DB_BACKEND=memory`
2. run once with `AD_ENGINE_DB_BACKEND=sqlite`
3. create a campaign under two different `X-Organization-ID` values and confirm isolation
4. create a campaign, restart the API, and confirm it is still listed

When changing the dashboard, the usual path is:

1. start the API with `python main.py serve`
2. start Vite with `npm run dev`
3. verify flows in the browser against a live campaign

Two practical notes from local browser verification:

- Vite may choose a different port if `5173` is already in use, so use the URL printed in the terminal instead of assuming `5173`.
- If the dashboard loads but the workspace is offline, check that `VITE_API_BASE_URL` matches the backend port that is actually serving this repo.

## Adding a New Provider

1. Implement one of the provider protocols in [providers.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/providers.py>).
2. Add the implementation to the appropriate registry in `build_provider_stack()`.
3. Select it with an environment variable.
4. Verify with `GET /health` that the expected provider is active.

Example environment setup in PowerShell:

```powershell
$env:AD_ENGINE_COPY_PROVIDER = 'rule_based'
python main.py serve
```

OpenAI image provider selection:

```powershell
$env:AD_ENGINE_IMAGE_PROVIDER = 'openai_images'
$env:OPENAI_API_KEY = 'your-api-key'
$env:OPENAI_IMAGE_MODEL = 'gpt-image-2'
$env:OPENAI_IMAGE_OUTPUT_DIR = '.\data\generated_assets'
python main.py serve
```

By default, `openai_images` attaches prompts during campaign creation and generates real images only through the per-variant endpoint/UI. Use `prompt_template` when you only want local, no-cost prompt generation. Set `OPENAI_IMAGE_GENERATE_DURING_CREATE=true` only when intentionally testing bulk image generation during campaign creation.

## Testing Strategy

Current verification is lightweight and manual:

- `compileall` for syntax sanity
- CLI execution for pipeline verification
- local API calls for route verification
- browser-based flow verification for create, save notes, and approve
- FastAPI route tests for organization-scoped campaign access

Good next testing additions:

- unit tests for `CampaignBrief` validation
- provider-level tests for deterministic outputs
- Postgres integration tests against a disposable database
- frontend interaction tests for creation, selection, and approval flows

## Documentation Map

- [README.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/README.md>): quick start
- [system_overview](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/system_overview>): original MVP scope and intent
- [docs/architecture.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/architecture.md>): internals and module layout
- [docs/api.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/api.md>): endpoint behavior
- [docs/development.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/development.md>): local workflow and extension notes
- [docs/deployment.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/deployment.md>): hosting and rollout strategy
- [docs/investor-playbook.md](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/docs/investor-playbook.md>): investor narrative, GTM, and diligence framing
