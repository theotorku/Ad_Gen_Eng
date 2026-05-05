from __future__ import annotations

from fastapi.testclient import TestClient

from ad_engine.engine import AdGenerationEngine
from ad_engine.fastapi_app import create_app
from ad_engine.providers import build_provider_stack
from ad_engine.store import InMemoryCampaignStore


def _client() -> TestClient:
    app = create_app(
        engine=AdGenerationEngine(build_provider_stack()),
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
