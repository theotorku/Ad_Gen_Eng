# Architecture

## Overview

The Ad Generation Engine is a small Python service that turns a structured campaign brief into a generated ad bundle. The core generation engine is dependency-light, while the API surface now uses FastAPI/Uvicorn so the project has a production-shaped path toward SaaS hosting.

The system currently supports two ways to use it:

- CLI generation through [main.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/main.py>)
- HTTP access through the FastAPI app in [src/ad_engine/fastapi_app.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/fastapi_app.py>)

## Request Flow

1. A campaign brief is submitted through the CLI or `POST /bundles`.
2. [CampaignBrief](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/models.py>) validates and normalizes the payload.
3. [AdGenerationEngine](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/engine.py>) resolves the active provider stack.
4. The planning provider creates a `CreativePlan`.
5. The copy provider generates `AdVariant` records.
6. The image provider enriches each variant with an image prompt.
7. The review pass adds quality notes and produces a `QualitySummary`.
8. The API store wraps the bundle in a campaign record and exposes it for later retrieval.

## Core Modules

- [models.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/models.py>): domain models, serialization, validation helpers
- [engine.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/engine.py>): orchestration layer
- [providers.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/providers.py>): provider interfaces, provider settings, registry wiring
- [planner.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/planner.py>): default planning provider
- [copywriter.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/copywriter.py>): default copy provider
- [assets.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/assets.py>): default image prompt provider
- [review.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/review.py>): quality checks
- [store.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/store.py>): memory, SQLite, and optional Postgres campaign persistence
- [fastapi_app.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/fastapi_app.py>): canonical FastAPI routes and app factory
- [config.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/config.py>): shared service defaults

## Provider Model

The engine is designed around three provider roles:

- Planning provider: transforms a brief into a strategy plan
- Copy provider: turns the plan into channel-ready ad variants
- Image provider: adds image generation prompts to each variant

The current defaults are local implementations:

- `rule_based` planning
- `rule_based` copy
- `prompt_template` image prompts

Registered text provider options currently include:

- `rule_based`
- `openai_responses`

Registered image provider options currently include:

- `prompt_template`
- `openai_images`

When `openai_responses` is active for planning and/or copy, the provider calls
the OpenAI Responses API and requests schema-constrained JSON matching the
engine's domain models. The rule-based path remains the deterministic default
for local development and tests.

When `openai_images` is active, campaign creation still attaches image prompts by default. Real images are generated per variant through the API/dashboard using GPT Image 2, then saved locally with a generated asset reference on the variant. Those files are served by the API through `/generated-assets/...`. Bulk image generation during campaign creation is available only when `OPENAI_IMAGE_GENERATE_DURING_CREATE=true`.

Provider selection is controlled with environment variables:

- `AD_ENGINE_PLANNING_PROVIDER`
- `AD_ENGINE_COPY_PROVIDER`
- `AD_ENGINE_IMAGE_PROVIDER`

OpenAI image generation is configured with:

- `OPENAI_API_KEY`
- `OPENAI_IMAGE_MODEL` defaults to `gpt-image-2`
- `OPENAI_IMAGE_SIZE`
- `OPENAI_IMAGE_QUALITY`
- `OPENAI_IMAGE_BACKGROUND`
- `OPENAI_IMAGE_OUTPUT_FORMAT`
- `OPENAI_IMAGE_OUTPUT_DIR`
- `OPENAI_IMAGE_GENERATE_DURING_CREATE`

OpenAI text generation is configured with:

- `OPENAI_API_KEY`
- `OPENAI_TEXT_MODEL` defaults to `gpt-5.1`
- `OPENAI_TEXT_TIMEOUT_SECONDS`

New providers should implement the relevant protocol in [providers.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/providers.py>) and then be registered in `build_provider_stack()`.

## Data Model

The main domain objects are:

- `CampaignBrief`: normalized input payload
- `CreativePlan`: strategy summary and messaging structure
- `AdVariant`: one channel-specific creative variant
- `QualitySummary`: strengths and risks from the review pass
- `AdBundle`: the full generation result
- `StoredCampaign`: API record that adds status and metadata around an `AdBundle`

## Persistence Model

The persistence layer supports three backends behind a shared campaign store interface:

- `memory` for fast local experimentation
- `sqlite` for durable local SaaS MVP storage
- `postgres` for shared SaaS environments, enabled with `AD_ENGINE_POSTGRES_DSN` and the optional `psycopg[binary]` dependency

Each campaign record carries an `organization_id`. API callers scope reads and writes with the `X-Organization-ID` header; omitted headers resolve to the `default` local organization. This is not full authentication yet, but it creates the storage boundary needed for the next auth/workspace milestone.

FastAPI also supports an environment-gated API-key layer. When `AD_ENGINE_REQUIRE_API_KEY=true`, requests must send `X-API-Key`; keys are configured as `key:organization_id` pairs in `AD_ENGINE_API_KEYS`, and the resolved organization becomes the storage scope for the request. This is a staging/prod guardrail, not a replacement for a future user identity provider.

The SQLite and Postgres stores keep a few searchable columns at the table level and store the full campaign record as JSON. That keeps the schema small while letting the bundle shape evolve without frequent migrations.

## Design Notes

- The engine stays deterministic by default so local testing is predictable.
- API routes are intentionally small and synchronous for now; image generation should move behind background jobs before broad SaaS usage.
- The project is organized so model-backed providers can be added without rewriting orchestration or route logic.
