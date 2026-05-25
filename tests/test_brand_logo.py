from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from ad_engine.assets import (
    BRAND_LOGO_MAX_BYTES,
    BrandLogoValidationError,
    composite_brand_logo,
    resolve_brand_logo_path,
    save_brand_logo,
)
from ad_engine.engine import AdGenerationEngine
from ad_engine.fastapi_app import create_app
from ad_engine.models import CampaignBrief
from ad_engine.providers import build_provider_stack
from ad_engine.store import InMemoryCampaignStore


def _png_bytes(size: tuple[int, int] = (32, 32), color: tuple[int, int, int, int] = (255, 0, 0, 255)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def client(monkeypatch, local_tmp_path) -> TestClient:
    monkeypatch.setenv("BRAND_LOGO_DIR", str(local_tmp_path / "brand_logos"))
    app = create_app(
        engine=AdGenerationEngine(build_provider_stack()),
        store=InMemoryCampaignStore(),
    )
    return TestClient(app)


def test_upload_rejects_disallowed_mime(client):
    response = client.post(
        "/assets/brand-logos",
        files={"file": ("logo.gif", _png_bytes(), "image/gif")},
    )
    assert response.status_code == 400
    assert "PNG" in response.json()["detail"]


def test_upload_rejects_oversize(client):
    payload = b"x" * (BRAND_LOGO_MAX_BYTES + 1024)
    response = client.post(
        "/assets/brand-logos",
        files={"file": ("logo.png", payload, "image/png")},
    )
    assert response.status_code == 413


def test_upload_rejects_corrupt_bytes(client):
    response = client.post(
        "/assets/brand-logos",
        files={"file": ("logo.png", b"not an image", "image/png")},
    )
    assert response.status_code == 400
    assert "decoded" in response.json()["detail"]


def test_upload_persists_png_and_serves_it_back(client):
    payload = _png_bytes()
    response = client.post(
        "/assets/brand-logos",
        files={"file": ("logo.png", payload, "image/png")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["path"].startswith("/brand-logos/")
    assert body["mime_type"] == "image/png"
    assert body["size"] == len(payload)

    served = client.get(body["path"])
    assert served.status_code == 200
    assert served.content == payload


def test_brand_logo_get_rejects_traversal(client):
    response = client.get("/brand-logos/..%2Fetc%2Fpasswd")
    assert response.status_code in {400, 404}


def test_save_brand_logo_writes_to_root(monkeypatch, local_tmp_path):
    monkeypatch.setenv("BRAND_LOGO_DIR", str(local_tmp_path))
    public_path, mime_type = save_brand_logo(_png_bytes(), "image/png")
    assert mime_type == "image/png"
    filename = public_path.rsplit("/", 1)[-1]
    assert (local_tmp_path / filename).is_file()


def test_save_brand_logo_rejects_empty(monkeypatch, local_tmp_path):
    monkeypatch.setenv("BRAND_LOGO_DIR", str(local_tmp_path))
    with pytest.raises(BrandLogoValidationError):
        save_brand_logo(b"", "image/png")


def test_resolve_brand_logo_path_blocks_traversal(monkeypatch, local_tmp_path):
    monkeypatch.setenv("BRAND_LOGO_DIR", str(local_tmp_path))
    assert resolve_brand_logo_path("/brand-logos/../passwd") is None
    assert resolve_brand_logo_path("/something-else/foo.png") is None
    assert resolve_brand_logo_path(None) is None


def test_composite_brand_logo_paints_bottom_right(local_tmp_path: Path):
    base_path = local_tmp_path / "base.png"
    logo_path = local_tmp_path / "logo.png"
    Image.new("RGBA", (400, 300), (255, 255, 255, 255)).save(base_path)
    Image.new("RGBA", (100, 100), (0, 0, 255, 255)).save(logo_path)

    composite_brand_logo(base_path, logo_path)

    with Image.open(base_path) as result:
        result_rgba = result.convert("RGBA")
        # 12% of long-edge (400) -> 48px logo, 3% margin -> 12px, so the logo
        # spans roughly (340..388, 240..288). Sample a pixel comfortably inside.
        sampled = result_rgba.getpixel((360, 260))
        background = result_rgba.getpixel((5, 5))
    assert sampled[2] > 200  # blue channel dominates after compositing
    assert sampled[0] < 50
    assert background == (255, 255, 255, 255)


def test_campaign_brief_round_trips_brand_logo(brief_payload):
    brief_payload = {**brief_payload, "brand_logo": "/brand-logos/abc123.png"}
    brief = CampaignBrief.from_dict(brief_payload)
    assert brief.brand_logo == "/brand-logos/abc123.png"
    assert brief.to_dict()["brand_logo"] == "/brand-logos/abc123.png"


def test_campaign_brief_rejects_bad_brand_logo(brief_payload):
    bad_payload = {**brief_payload, "brand_logo": "/uploads/evil.png"}
    with pytest.raises(ValueError):
        CampaignBrief.from_dict(bad_payload)

    traversal_payload = {**brief_payload,
                         "brand_logo": "/brand-logos/../evil.png"}
    with pytest.raises(ValueError):
        CampaignBrief.from_dict(traversal_payload)

    bad_ext_payload = {**brief_payload, "brand_logo": "/brand-logos/logo.gif"}
    with pytest.raises(ValueError):
        CampaignBrief.from_dict(bad_ext_payload)
