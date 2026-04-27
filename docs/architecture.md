# Architecture

## Overview

The Ad Generation Engine is a small Python service that turns a structured campaign brief into a generated ad bundle. The project is intentionally lightweight and uses the standard library only, which keeps the MVP easy to run and easy to change.

The system currently supports two ways to use it:

- CLI generation through [main.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/main.py>)
- HTTP access through the API server in [src/ad_engine/api.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/api.py>)

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
- [store.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/store.py>): in-memory campaign persistence
- [api.py](</c:/Users/TheoTorku/OneDrive/Desktop/march 2026/Ad_Generation Engine/src/ad_engine/api.py>): REST API routes and request handling

## Provider Model

The engine is designed around three provider roles:

- Planning provider: transforms a brief into a strategy plan
- Copy provider: turns the plan into channel-ready ad variants
- Image provider: adds image generation prompts to each variant

The current defaults are local implementations:

- `rule_based` planning
- `rule_based` copy
- `prompt_template` image prompts

Registered image provider options currently include:

- `prompt_template`
- `openai_images`

When `openai_images` is active, the provider calls the OpenAI Images API, saves generated image files locally, and attaches a generated asset reference to each ad variant. Those files are then served by the API through `/generated-assets/...`.

Provider selection is controlled with environment variables:

- `AD_ENGINE_PLANNING_PROVIDER`
- `AD_ENGINE_COPY_PROVIDER`
- `AD_ENGINE_IMAGE_PROVIDER`

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

The current store is process-local and in-memory. A server restart clears all campaigns. The store exists mainly to support the API lifecycle endpoints and provide a simple seam for future persistence work.

The persistence layer now supports two backends behind a shared campaign store interface:

- `memory` for fast local experimentation
- `sqlite` for durable local SaaS MVP storage

The SQLite store keeps a few searchable columns at the table level and stores the full campaign record as JSON. That keeps the schema small while letting the bundle shape evolve without frequent migrations.

Likely future storage replacements:

- Postgres for multi-user usage
- object storage or file-backed snapshots for generated exports

## Design Notes

- The engine stays deterministic by default so local testing is predictable.
- API routes are intentionally small and synchronous.
- The project is organized so model-backed providers can be added without rewriting orchestration or route logic.
