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
from .billing import (
    FEATURE_IMAGE_GENERATION,
    METRIC_CAMPAIGNS,
    METRIC_IMAGES,
    BillingSettings,
    metric_allowance,
    resolve_plan_limits,
    usage_period,
)
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
    billing_settings: BillingSettings | None = None,
) -> FastAPI:
    app = FastAPI(title="Ad Generation Engine API", version="0.2.0")
    app.state.engine = engine or AdGenerationEngine(build_provider_stack())
    app.state.store = store or build_campaign_store(StoreSettings.from_env())
    app.state.auth_settings = AuthSettings.from_env()
    app.state.billing_settings = billing_settings or BillingSettings.from_env()

    origins, allow_any, origin_regex = _load_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_any else list(origins),
        allow_origin_regex=origin_regex,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Organization-ID", "X-API-Key"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "providers": app.state.engine.providers.describe(),
            "db_backend": app.state.store.backend_name,
            "auth_required": app.state.auth_settings.require_api_key,
            "clerk_auth_required": app.state.auth_settings.require_clerk_auth,
            "plan_limits_enforced": app.state.billing_settings.enforce_limits,
        }

    @app.get("/usage")
    def usage(
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
        settings = app.state.billing_settings
        limits = resolve_plan_limits(auth.plan, default_plan=settings.default_plan)
        period = usage_period()
        return {
            "plan": auth.plan or settings.default_plan,
            "period": period,
            "enforced": settings.enforce_limits,
            "usage": {
                METRIC_IMAGES: app.state.store.get_usage(
                    auth.organization_id, period, METRIC_IMAGES
                ),
                METRIC_CAMPAIGNS: app.state.store.get_usage(
                    auth.organization_id, period, METRIC_CAMPAIGNS
                ),
            },
            "limits": {
                METRIC_IMAGES: limits.images_per_month,
                METRIC_CAMPAIGNS: limits.campaigns_per_month,
            },
            "features": sorted(limits.features),
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
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
        _enforce_plan_limit(app, auth, METRIC_CAMPAIGNS)
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

        app.state.store.increment_usage(
            auth.organization_id, usage_period(), METRIC_CAMPAIGNS
        )
        return stored.to_dict()

    @app.get("/bundles/{campaign_id}")
    def get_bundle(
        campaign_id: str,
        x_organization_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
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
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
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
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
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
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
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
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
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
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
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
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
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

        _enforce_feature(app, auth, FEATURE_IMAGE_GENERATION)
        _enforce_plan_limit(app, auth, METRIC_IMAGES)

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
            app.state.store.increment_usage(
                auth.organization_id, usage_period(), METRIC_IMAGES
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
        authorization: str | None = Header(default=None),
    ) -> PlainTextResponse:
        auth = _auth_context(app, x_api_key, authorization, x_organization_id)
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
        authorization: str | None = Header(default=None),
    ) -> FileResponse:
        _auth_context(app, x_api_key, authorization, x_organization_id)
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
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _auth_context(app, x_api_key, authorization, x_organization_id)
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
        authorization: str | None = Header(default=None),
    ) -> FileResponse:
        _auth_context(app, x_api_key, authorization, x_organization_id)
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
    authorization: str | None,
    organization_id: str | None,
) -> AuthContext:
    try:
        return resolve_auth_context(
            settings=app.state.auth_settings,
            api_key=api_key,
            authorization=authorization,
            requested_organization_id=organization_id,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED, detail=str(exc)) from exc


def _enforce_plan_limit(app: FastAPI, auth: AuthContext, metric: str) -> None:
    settings = app.state.billing_settings
    if not settings.enforce_limits:
        return
    limits = resolve_plan_limits(auth.plan, default_plan=settings.default_plan)
    allowance = metric_allowance(limits, metric)
    if allowance is None:
        return  # Unlimited (fair use).
    used = app.state.store.get_usage(auth.organization_id, usage_period(), metric)
    if used >= allowance:
        plan = auth.plan or settings.default_plan
        raise HTTPException(
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            detail=(
                f"Monthly {metric} limit reached for the {plan} plan "
                f"({allowance}). Upgrade your workspace plan to generate more."
            ),
        )


def _enforce_feature(app: FastAPI, auth: AuthContext, feature: str) -> None:
    settings = app.state.billing_settings
    if not settings.enforce_limits:
        return
    limits = resolve_plan_limits(auth.plan, default_plan=settings.default_plan)
    if feature not in limits.features:
        plan = auth.plan or settings.default_plan
        raise HTTPException(
            status_code=HTTPStatus.PAYMENT_REQUIRED,
            detail=(
                f"The {feature.replace('_', ' ')} feature is not included in the "
                f"{plan} plan. Upgrade your workspace plan to enable it."
            ),
        )


def _load_cors_origins() -> tuple[frozenset[str], bool, str | None]:
    regex = os.getenv("AD_ENGINE_CORS_ORIGIN_REGEX") or None
    raw = os.getenv("AD_ENGINE_CORS_ORIGINS")
    if raw is None:
        return frozenset(DEFAULT_CORS_ORIGINS), False, regex
    entries = [item.strip() for item in raw.split(",") if item.strip()]
    if "*" in entries:
        return frozenset(), True, regex
    return frozenset(entries), False, regex


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

    landing = bundle.get("landing_section")
    if landing:
        lines.extend(
            [
                "",
                "Landing section",
                f"Headline: {landing['headline']}",
                f"Subheadline: {landing['subheadline']}",
                f"CTA: {landing['cta']}",
                "Proof points:",
                *[f"- {point}" for point in landing["proof_points"]],
                "",
                landing["html_snippet"],
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
