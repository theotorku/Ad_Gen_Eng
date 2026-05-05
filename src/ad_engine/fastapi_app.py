from __future__ import annotations

import os
from http import HTTPStatus
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from .api import DEFAULT_CORS_ORIGINS, DEFAULT_ORGANIZATION_ID
from .assets import get_generated_asset_root
from .engine import AdGenerationEngine
from .providers import build_provider_stack
from .store import CampaignStore, StoreSettings, build_campaign_store


class CampaignUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    approval_notes: str | None = None
    metadata: dict[str, Any] | None = None


class CampaignApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_notes: str | None = None


def create_app(
    *,
    engine: AdGenerationEngine | None = None,
    store: CampaignStore | None = None,
) -> FastAPI:
    app = FastAPI(title="Ad Generation Engine API", version="0.2.0")
    app.state.engine = engine or AdGenerationEngine(build_provider_stack())
    app.state.store = store or build_campaign_store(StoreSettings.from_env())

    origins, allow_any = _load_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_any else list(origins),
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-Organization-ID"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "providers": app.state.engine.providers.describe(),
            "db_backend": app.state.store.backend_name,
        }

    @app.get("/bundles")
    def bundles_help() -> dict[str, str]:
        return {
            "message": "Submit a POST request to /bundles to generate a new ad bundle.",
        }

    @app.post("/bundles", status_code=HTTPStatus.CREATED)
    async def create_bundle(
        request: Request,
        x_organization_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        payload = await _read_json_object(request)
        try:
            bundle = app.state.engine.run(payload)
            stored = app.state.store.create(
                bundle,
                metadata=_campaign_metadata_from_brief(payload),
                organization_id=_organization_id(x_organization_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc

        return stored.to_dict()

    @app.get("/bundles/{campaign_id}")
    def get_bundle(
        campaign_id: str,
        x_organization_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        stored = app.state.store.get(
            campaign_id, organization_id=_organization_id(x_organization_id)
        )
        if stored is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Bundle '{campaign_id}' was not found.",
            )
        return stored.bundle.to_dict()

    @app.get("/campaigns")
    def list_campaigns(
        x_organization_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        campaigns = [
            campaign.to_dict()
            for campaign in app.state.store.list(
                organization_id=_organization_id(x_organization_id)
            )
        ]
        return {"campaigns": campaigns, "count": len(campaigns)}

    @app.get("/campaigns/{campaign_id}")
    def get_campaign(
        campaign_id: str,
        x_organization_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        stored = app.state.store.get(
            campaign_id, organization_id=_organization_id(x_organization_id)
        )
        if stored is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Campaign '{campaign_id}' was not found.",
            )
        return stored.to_dict()

    @app.patch("/campaigns/{campaign_id}")
    def update_campaign(
        campaign_id: str,
        payload: CampaignUpdateRequest,
        x_organization_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            stored = app.state.store.update(
                campaign_id,
                organization_id=_organization_id(x_organization_id),
                status=payload.status,
                approval_notes=payload.approval_notes,
                metadata=payload.metadata,
            )
        except ValueError as exc:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc

        if stored is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Campaign '{campaign_id}' was not found.",
            )
        return stored.to_dict()

    @app.post("/campaigns/{campaign_id}/approve")
    def approve_campaign(
        campaign_id: str,
        payload: CampaignApprovalRequest | None = None,
        x_organization_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        stored = app.state.store.approve(
            campaign_id,
            approval_notes=payload.approval_notes if payload else None,
            organization_id=_organization_id(x_organization_id),
        )
        if stored is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Campaign '{campaign_id}' was not found.",
            )
        return stored.to_dict()

    @app.get("/generated-assets/{filename:path}")
    def generated_asset(filename: str) -> FileResponse:
        asset_root = get_generated_asset_root().resolve()
        asset_path = (asset_root / filename.strip()).resolve()
        if asset_root not in asset_path.parents and asset_path != asset_root:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Invalid asset path.")
        if not asset_path.exists() or not asset_path.is_file():
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Generated asset not found.",
            )
        return FileResponse(asset_path)

    return app


def run_fastapi_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port)


async def _read_json_object(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Request body must be valid JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Request body must be a JSON object.",
        )
    return payload


def _campaign_metadata_from_brief(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "brand_name": str(payload.get("brand_name", "")).strip(),
        "product_name": str(payload.get("product_name", "")).strip(),
        "objective": str(payload.get("objective", "")).strip(),
        "channels": payload.get("channels", []),
    }


def _organization_id(value: str | None) -> str:
    normalized = (value or DEFAULT_ORGANIZATION_ID).strip()
    return normalized or DEFAULT_ORGANIZATION_ID


def _load_cors_origins() -> tuple[frozenset[str], bool]:
    raw = os.getenv("AD_ENGINE_CORS_ORIGINS")
    if raw is None:
        return frozenset(DEFAULT_CORS_ORIGINS), False
    entries = [item.strip() for item in raw.split(",") if item.strip()]
    if "*" in entries:
        return frozenset(), True
    return frozenset(entries), False
