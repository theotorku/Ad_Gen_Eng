from __future__ import annotations

from fastapi.testclient import TestClient

from ad_engine.billing import BillingSettings
from ad_engine.engine import AdGenerationEngine
from ad_engine.fastapi_app import create_app
from ad_engine.models import GeneratedAsset
from ad_engine.providers import build_provider_stack
from ad_engine.store import InMemoryCampaignStore


class _FakeImages:
    provider_name = "fake_images"

    def attach_image_prompts(self, brief, variants):
        for variant in variants:
            variant.image_prompt = "Fake prompt."

    def generate_variant_image(self, brief, variant, *, index=1):
        return GeneratedAsset(
            path="/generated-assets/fake.png",
            mime_type="image/png",
            provider="openai_images",
            prompt=variant.image_prompt,
        )


def _enforced_client(image_provider=None, default_plan="free") -> TestClient:
    providers = build_provider_stack()
    if image_provider is not None:
        providers.image = image_provider
    app = create_app(
        engine=AdGenerationEngine(providers),
        store=InMemoryCampaignStore(),
        billing_settings=BillingSettings(enforce_limits=True, default_plan=default_plan),
    )
    return TestClient(app)


def _client(image_provider=None) -> TestClient:
    providers = build_provider_stack()
    if image_provider is not None:
        providers.image = image_provider
    app = create_app(
        engine=AdGenerationEngine(providers),
        store=InMemoryCampaignStore(),
    )
    return TestClient(app)


def test_fastapi_health_reports_store_backend():
    client = _client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["db_backend"] == "memory"


def test_fastapi_campaigns_are_scoped_by_organization(brief_payload):
    client = _client()

    alpha = client.post(
        "/bundles",
        json=brief_payload,
        headers={"X-Organization-ID": "alpha"},
    )
    beta = client.post(
        "/bundles",
        json=brief_payload,
        headers={"X-Organization-ID": "beta"},
    )

    assert alpha.status_code == 201
    assert beta.status_code == 201
    alpha_id = alpha.json()["id"]

    alpha_list = client.get("/campaigns", headers={"X-Organization-ID": "alpha"})
    beta_fetch = client.get(
        f"/campaigns/{alpha_id}", headers={"X-Organization-ID": "beta"}
    )

    assert [item["id"] for item in alpha_list.json()["campaigns"]] == [alpha_id]
    assert beta_fetch.status_code == 404


def test_fastapi_rejects_invalid_brief(brief_payload):
    client = _client()
    brief_payload.pop("brand_name")

    response = client.post("/bundles", json=brief_payload)

    assert response.status_code == 400
    assert "brand_name" in response.json()["detail"]


def test_fastapi_updates_variant_copy(brief_payload):
    client = _client()
    created = client.post("/bundles", json=brief_payload)
    campaign_id = created.json()["id"]

    response = client.patch(
        f"/campaigns/{campaign_id}/variants/0",
        json={"headline": "Edited headline", "cta": "Start now"},
    )

    assert response.status_code == 200
    variant = response.json()["bundle"]["variants"][0]
    assert variant["headline"] == "Edited headline"
    assert variant["cta"] == "Start now"


def test_fastapi_exports_campaign_text(brief_payload):
    client = _client()
    created = client.post("/bundles", json=brief_payload)
    campaign_id = created.json()["id"]

    response = client.get(f"/campaigns/{campaign_id}/export.txt")

    assert response.status_code == 200
    assert "Campaign: Northstar AI" in response.text
    assert "Variants" in response.text


def test_fastapi_generates_one_variant_image(monkeypatch, brief_payload):
    class FakeOpenAIImagesProvider:
        provider_name = "fake_images"

        def attach_image_prompts(self, brief, variants):
            for variant in variants:
                variant.image_prompt = "Fake prompt."

        def generate_variant_image(self, brief, variant, *, index=1):
            return GeneratedAsset(
                path="/generated-assets/fake.png",
                mime_type="image/png",
                provider="openai_images",
                prompt=variant.image_prompt,
            )

    client = _client(image_provider=FakeOpenAIImagesProvider())
    created = client.post("/bundles", json=brief_payload)
    campaign_id = created.json()["id"]

    response = client.post(f"/campaigns/{campaign_id}/variants/0/generate-image")

    assert response.status_code == 200
    variant = response.json()["bundle"]["variants"][0]
    assert variant["image_status"] == "generated"
    assert variant["generated_asset"]["path"] == "/generated-assets/fake.png"


def test_fastapi_records_variant_image_failure(monkeypatch, brief_payload):
    class FakeOpenAIImagesProvider:
        provider_name = "fake_images"

        def attach_image_prompts(self, brief, variants):
            for variant in variants:
                variant.image_prompt = "Fake prompt."

        def generate_variant_image(self, brief, variant, *, index=1):
            raise ValueError("Provider timed out.")

    client = _client(image_provider=FakeOpenAIImagesProvider())
    created = client.post("/bundles", json=brief_payload)
    campaign_id = created.json()["id"]

    response = client.post(f"/campaigns/{campaign_id}/variants/0/generate-image")

    assert response.status_code == 200
    variant = response.json()["bundle"]["variants"][0]
    assert variant["image_status"] == "failed"
    assert variant["generated_asset"] is None
    assert variant["image_error"] == "Provider timed out."


def test_fastapi_rejects_image_generation_when_provider_is_prompt_only(brief_payload):
    client = _client()
    created = client.post("/bundles", json=brief_payload)
    campaign_id = created.json()["id"]

    response = client.post(f"/campaigns/{campaign_id}/variants/0/generate-image")

    assert response.status_code == 400
    assert "openai_images" in response.json()["detail"]


def test_fastapi_records_unexpected_image_generation_error(brief_payload):
    class ExplodingImageProvider:
        provider_name = "exploding_images"

        def attach_image_prompts(self, brief, variants):
            for variant in variants:
                variant.image_prompt = "Fake prompt."

        def generate_variant_image(self, brief, variant, *, index=1):
            raise RuntimeError("socket vanished")

    client = _client(image_provider=ExplodingImageProvider())
    created = client.post("/bundles", json=brief_payload)
    campaign_id = created.json()["id"]

    response = client.post(f"/campaigns/{campaign_id}/variants/0/generate-image")
    fetched = client.get(f"/campaigns/{campaign_id}")

    assert response.status_code == 500
    variant = fetched.json()["bundle"]["variants"][0]
    assert variant["image_status"] == "failed"
    assert variant["image_error"] == "Unexpected image generation error."


def test_fastapi_required_auth_maps_key_to_workspace(monkeypatch, brief_payload):
    monkeypatch.setenv("AD_ENGINE_REQUIRE_API_KEY", "true")
    monkeypatch.setenv("AD_ENGINE_API_KEYS", "alpha-secret:alpha")
    client = _client()

    missing = client.get("/campaigns", headers={"X-Organization-ID": "alpha"})
    created = client.post(
        "/bundles",
        json=brief_payload,
        headers={"X-API-Key": "alpha-secret"},
    )
    listed = client.get("/campaigns", headers={"X-API-Key": "alpha-secret"})

    assert missing.status_code == 401
    assert created.status_code == 201
    assert created.json()["organization_id"] == "alpha"
    assert listed.json()["count"] == 1


def test_fastapi_required_clerk_auth_maps_token_to_workspace(monkeypatch, brief_payload):
    import ad_engine.auth as auth_module

    monkeypatch.setenv("AD_ENGINE_REQUIRE_CLERK_AUTH", "true")
    monkeypatch.setenv("CLERK_ISSUER", "https://accounts.example.com")
    monkeypatch.setattr(
        auth_module,
        "_decode_clerk_token",
        lambda settings, token: {"sub": "user_123", "org_id": "alpha"},
    )
    client = _client()

    missing = client.get("/campaigns", headers={"X-Organization-ID": "alpha"})
    created = client.post(
        "/bundles",
        json=brief_payload,
        headers={
            "Authorization": "Bearer test-token",
            "X-Organization-ID": "alpha",
        },
    )
    listed = client.get(
        "/campaigns",
        headers={
            "Authorization": "Bearer test-token",
            "X-Organization-ID": "alpha",
        },
    )

    assert missing.status_code == 401
    assert created.status_code == 201
    assert created.json()["organization_id"] == "alpha"
    assert listed.json()["count"] == 1


def test_usage_endpoint_tracks_counts_when_enforcement_off(brief_payload):
    # Usage is always tracked; enforcement only gates. With the default client
    # (enforcement off) the counter still advances so data exists at cutover.
    client = _client()
    client.post("/bundles", json=brief_payload)

    usage = client.get("/usage").json()

    assert usage["enforced"] is False
    assert usage["plan"] == "free"
    assert usage["usage"]["campaigns"] == 1
    assert usage["limits"]["campaigns"] == 3


def test_free_plan_blocks_image_generation_feature(brief_payload):
    client = _enforced_client(image_provider=_FakeImages(), default_plan="free")
    campaign_id = client.post("/bundles", json=brief_payload).json()["id"]

    response = client.post(f"/campaigns/{campaign_id}/variants/0/generate-image")

    assert response.status_code == 402
    assert "image generation" in response.json()["detail"].lower()


def test_free_plan_caps_campaign_creation(brief_payload):
    client = _enforced_client(default_plan="free")

    for _ in range(3):
        assert client.post("/bundles", json=brief_payload).status_code == 201
    blocked = client.post("/bundles", json=brief_payload)

    assert blocked.status_code == 402
    assert "campaigns" in blocked.json()["detail"].lower()


def test_pro_plan_allows_image_generation_and_tracks_usage(monkeypatch, brief_payload):
    import ad_engine.auth as auth_module

    monkeypatch.setenv("AD_ENGINE_REQUIRE_CLERK_AUTH", "true")
    monkeypatch.setenv("CLERK_ISSUER", "https://accounts.example.com")
    monkeypatch.setattr(
        auth_module,
        "_decode_clerk_token",
        lambda settings, token: {
            "sub": "user_1",
            "org_id": "alpha",
            "pla": "o:pro",
            "fea": "o:image_generation",
        },
    )
    client = _enforced_client(image_provider=_FakeImages())
    headers = {"Authorization": "Bearer t"}

    campaign_id = client.post("/bundles", json=brief_payload, headers=headers).json()["id"]
    generated = client.post(
        f"/campaigns/{campaign_id}/variants/0/generate-image", headers=headers
    )
    usage = client.get("/usage", headers=headers).json()

    assert generated.status_code == 200
    assert usage["plan"] == "pro"
    assert usage["limits"]["images"] == 150
    assert usage["usage"]["images"] == 1
    assert usage["usage"]["campaigns"] == 1
