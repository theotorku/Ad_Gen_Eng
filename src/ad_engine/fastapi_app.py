from __future__ import annotations

import os
from http import HTTPStatus
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict

from .assets import (
    BRAND_LOGO_MAX_BYTES,
    BrandLogoValidationError,
    get_brand_logo_root,
    get_generated_asset_root,
    save_brand_logo,
)
from .auth import AuthContext, AuthSettings, AuthenticationError, resolve_auth_context
from .config import DEFAULT_CORS_ORIGINS
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


class VariantUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str | None = None
    primary_text: str | None = None
    cta: str | None = None
    image_prompt: str | None = None


def create_app(
    *,
    engine: AdGenerationEngine | None = None,
    store: CampaignStore | None = None,
) -> FastAPI:
    app = FastAPI(title="Ad Generation Engine API", version="0.2.0")
    app.state.engine = engine or AdGenerationEngine(build_provider_stack())
    app.state.store = store or build_campaign_store(StoreSettings.from_env())
    app.state.auth_settings = AuthSettings.from_env()

    origins, allow_any = _load_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_any else list(origins),
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-Organization-ID", "X-API-Key"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "providers": app.state.engine.providers.describe(),
            "db_backend": app.state.store.backend_name,
            "auth_required": app.state.auth_settings.require_api_key,
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
        x_api_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, x_organization_id)
        payload = await _read_json_object(request)
        try:
            bundle = app.state.engine.run(payload)
            stored = app.state.store.create(
                bundle,
                metadata=_campaign_metadata_from_brief(payload),
                organization_id=auth.organization_id,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc

        return stored.to_dict()

    @app.get("/bundles/{campaign_id}")
    def get_bundle(
        campaign_id: str,
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, x_organization_id)
        stored = app.state.store.get(
            campaign_id, organization_id=auth.organization_id
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
        x_api_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, x_organization_id)
        campaigns = [
            campaign.to_dict()
            for campaign in app.state.store.list(
                organization_id=auth.organization_id
            )
        ]
        return {"campaigns": campaigns, "count": len(campaigns)}

    @app.get("/campaigns/{campaign_id}")
    def get_campaign(
        campaign_id: str,
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, x_organization_id)
        stored = app.state.store.get(
            campaign_id, organization_id=auth.organization_id
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
        x_api_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, x_organization_id)
        try:
            stored = app.state.store.update(
                campaign_id,
                organization_id=auth.organization_id,
                status=payload.status,
                approval_notes=payload.approval_notes,
                metadata=payload.metadata,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc

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
        x_api_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, x_organization_id)
        stored = app.state.store.approve(
            campaign_id,
            approval_notes=payload.approval_notes if payload else None,
            organization_id=auth.organization_id,
        )
        if stored is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Campaign '{campaign_id}' was not found.",
            )
        return stored.to_dict()

    @app.patch("/campaigns/{campaign_id}/variants/{variant_index}")
    def update_variant(
        campaign_id: str,
        variant_index: int,
        payload: VariantUpdateRequest,
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, x_organization_id)
        try:
            stored = app.state.store.update_variant(
                campaign_id,
                variant_index,
                organization_id=auth.organization_id,
                headline=payload.headline,
                primary_text=payload.primary_text,
                cta=payload.cta,
                image_prompt=payload.image_prompt,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc

        if stored is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Campaign '{campaign_id}' was not found.",
            )
        return stored.to_dict()

    @app.post("/campaigns/{campaign_id}/variants/{variant_index}/generate-image")
    def generate_variant_image(
        campaign_id: str,
        variant_index: int,
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, x_organization_id)
        stored = app.state.store.get(
            campaign_id, organization_id=auth.organization_id
        )
        if stored is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Campaign '{campaign_id}' was not found.",
            )
        if variant_index < 0 or variant_index >= len(stored.bundle.variants):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Variant index is out of range.",
            )

        image_provider = app.state.engine.providers.image
        generate_variant_image = getattr(
            image_provider, "generate_variant_image", None)
        if generate_variant_image is None:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Image generation requires AD_ENGINE_IMAGE_PROVIDER=openai_images.",
            )

        app.state.store.update_variant_image(
            campaign_id,
            variant_index,
            organization_id=auth.organization_id,
            image_status="generating",
        )

        variant = stored.bundle.variants[variant_index]
        try:
            asset = generate_variant_image(
                stored.bundle.brief,
                variant,
                index=variant_index + 1,
            )
            updated = app.state.store.update_variant_image(
                campaign_id,
                variant_index,
                organization_id=auth.organization_id,
                image_status="generated",
                generated_asset=asset,
            )
        except ValueError as exc:
            updated = app.state.store.update_variant_image(
                campaign_id,
                variant_index,
                organization_id=auth.organization_id,
                image_status="failed",
                image_error=str(exc),
            )
        except Exception as exc:
            app.state.store.update_variant_image(
                campaign_id,
                variant_index,
                organization_id=auth.organization_id,
                image_status="failed",
                image_error="Unexpected image generation error.",
            )
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Unexpected image generation error.",
            ) from exc

        if updated is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Campaign '{campaign_id}' was not found.",
            )
        return updated.to_dict()

    @app.get("/campaigns/{campaign_id}/export.txt")
    def export_campaign_text(
        campaign_id: str,
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> PlainTextResponse:
        auth = _auth_context(app, x_api_key, x_organization_id)
        stored = app.state.store.get(
            campaign_id, organization_id=auth.organization_id
        )
        if stored is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Campaign '{campaign_id}' was not found.",
            )

        filename = f"{_safe_filename(stored.bundle.brief.brand_name)}-campaign.txt"
        return PlainTextResponse(
            _campaign_export_text(stored.to_dict()),
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/generated-assets/{filename:path}")
    def generated_asset(
        filename: str,
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> FileResponse:
        _auth_context(app, x_api_key, x_organization_id)
        asset_root = get_generated_asset_root().resolve()
        asset_path = (asset_root / filename.strip()).resolve()
        if not asset_path.is_relative_to(asset_root):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail="Invalid asset path.")
        if not asset_path.exists() or not asset_path.is_file():
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Generated asset not found.",
            )
        return FileResponse(asset_path)

    @app.post("/assets/brand-logos", status_code=HTTPStatus.CREATED)
    async def upload_brand_logo(
        file: UploadFile = File(...),
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _auth_context(app, x_api_key, x_organization_id)
        content = await file.read(BRAND_LOGO_MAX_BYTES + 1)
        if len(content) > BRAND_LOGO_MAX_BYTES:
            raise HTTPException(
                status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                detail="Brand logo must be 2 MB or smaller.",
            )
        try:
            public_path, mime_type = save_brand_logo(
                content, file.content_type)
        except BrandLogoValidationError as exc:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc
        return {"path": public_path, "mime_type": mime_type, "size": len(content)}

    @app.get("/brand-logos/{filename:path}")
    def brand_logo_asset(
        filename: str,
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> FileResponse:
        _auth_context(app, x_api_key, x_organization_id)
        asset_root = get_brand_logo_root().resolve()
        asset_path = (asset_root / filename.strip()).resolve()
        if not asset_path.is_relative_to(asset_root):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail="Invalid asset path.")
        if not asset_path.exists() or not asset_path.is_file():
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Brand logo not found.",
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


def _auth_context(
    app: FastAPI,
    api_key: str | None,
    organization_id: str | None,
) -> AuthContext:
    try:
        return resolve_auth_context(
            settings=app.state.auth_settings,
            api_key=api_key,
            requested_organization_id=organization_id,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED, detail=str(exc)) from exc


def _load_cors_origins() -> tuple[frozenset[str], bool]:
    raw = os.getenv("AD_ENGINE_CORS_ORIGINS")
    if raw is None:
        return frozenset(DEFAULT_CORS_ORIGINS), False
    entries = [item.strip() for item in raw.split(",") if item.strip()]
    if "*" in entries:
        return frozenset(), True
    return frozenset(entries), False


def _campaign_export_text(campaign: dict[str, Any]) -> str:
    bundle = campaign["bundle"]
    brief = bundle["brief"]
    plan = bundle["creative_plan"]
    lines = [
        f"Campaign: {brief['brand_name']}",
        f"Product: {brief['product_name']}",
        f"Objective: {brief['objective']}",
        f"Status: {campaign['status']}",
        "",
        "Strategy",
        plan["strategy_summary"],
        plan["audience_promise"],
        "",
        "Messaging pillars",
        *[f"- {pillar}" for pillar in plan["messaging_pillars"]],
        "",
        "Variants",
    ]

    for index, variant in enumerate(bundle["variants"], start=1):
        lines.extend(
            [
                "",
                f"{index}. {variant['channel']} / {variant['angle']}",
                f"Headline: {variant['headline']}",
                f"Primary text: {variant['primary_text']}",
                f"CTA: {variant['cta']}",
                f"Image prompt: {variant['image_prompt']}",
            ]
        )

    if campaign.get("approval_notes"):
        lines.extend(["", "Approval notes", campaign["approval_notes"]])

    return "\n".join(lines).strip() + "\n"


def _safe_filename(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum()
                      else "-" for char in value)
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed or "campaign"
