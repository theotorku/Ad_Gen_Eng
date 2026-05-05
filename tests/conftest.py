from __future__ import annotations

import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def local_tmp_path(request):
    base = ROOT / "data" / ".tmp" / "pytest"
    base.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(char if char.isalnum() else "-" for char in request.node.name)
    path = base / f"{safe_name}-{uuid4().hex[:8]}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def brief_payload() -> dict:
    return {
        "brand_name": "Northstar AI",
        "product_name": "CampaignPilot",
        "objective": "Generate more qualified demo requests",
        "target_audience": "B2B marketing teams at growth-stage SaaS companies",
        "pain_points": [
            "slow campaign production cycles",
            "generic creative that underperforms",
        ],
        "value_props": [
            "faster ad iteration",
            "clearer campaign strategy",
            "less manual copy drafting",
        ],
        "offer": "Book a free strategy walkthrough",
        "tone": "confident",
        "channels": ["linkedin", "facebook", "google_search"],
        "constraints": ["Avoid exaggerated performance claims"],
    }


@pytest.fixture
def valid_brief(brief_payload):
    from ad_engine.models import CampaignBrief

    return CampaignBrief.from_dict(brief_payload)
