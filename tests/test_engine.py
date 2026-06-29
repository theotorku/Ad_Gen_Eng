from __future__ import annotations

import pytest

from ad_engine.assets import attach_image_prompts
from ad_engine.copywriter import generate_variants
from ad_engine.engine import AdGenerationEngine
from ad_engine.planner import build_creative_plan
from ad_engine.providers import build_provider_stack


def test_engine_run_returns_complete_bundle(brief_payload):
    engine = AdGenerationEngine(build_provider_stack())

    bundle = engine.run(brief_payload)

    assert bundle.brief.brand_name == brief_payload["brand_name"]
    assert bundle.creative_plan.messaging_pillars
    assert bundle.variants
    assert bundle.quality_summary.strengths
    assert bundle.landing_section is not None
    assert bundle.generation_jobs
    assert bundle.cost_summary["estimated_image_credits"] == len(bundle.variants)


def test_engine_run_populates_image_prompts(brief_payload):
    engine = AdGenerationEngine(build_provider_stack())

    bundle = engine.run(brief_payload)

    assert all(variant.image_prompt for variant in bundle.variants)
    assert all(
        bundle.brief.brand_name in variant.image_prompt for variant in bundle.variants
    )


def test_engine_run_invalid_brief_raises(brief_payload):
    brief_payload["channels"] = []
    engine = AdGenerationEngine(build_provider_stack())

    with pytest.raises(ValueError):
        engine.run(brief_payload)


def test_attach_image_prompts_uses_visual_style_for_tone(valid_brief):
    plan = build_creative_plan(valid_brief)
    variants = generate_variants(valid_brief, plan)

    valid_brief.tone = "luxury"
    attach_image_prompts(valid_brief, variants)

    assert all("elevated" in variant.image_prompt for variant in variants)
