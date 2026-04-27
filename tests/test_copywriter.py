from __future__ import annotations

from ad_engine.copywriter import CHANNEL_LIMITS, generate_variants
from ad_engine.planner import build_creative_plan


def _build(valid_brief):
    plan = build_creative_plan(valid_brief)
    return plan, generate_variants(valid_brief, plan)


def test_variant_count_is_channels_times_three(valid_brief):
    _, variants = _build(valid_brief)

    assert len(variants) == len(valid_brief.channels) * 3


def test_each_variant_covers_all_channels(valid_brief):
    _, variants = _build(valid_brief)

    seen_channels = {variant.channel for variant in variants}
    assert seen_channels == set(valid_brief.channels)


def test_headlines_respect_channel_limit(valid_brief):
    _, variants = _build(valid_brief)

    for variant in variants:
        assert len(variant.headline) <= CHANNEL_LIMITS[variant.channel], (
            f"{variant.channel}: {variant.headline!r}"
        )


def test_truncated_headlines_use_ellipsis(valid_brief):
    _, variants = _build(valid_brief)

    for variant in variants:
        if variant.headline.endswith("..."):
            assert len(variant.headline) <= CHANNEL_LIMITS[variant.channel]


def test_lead_objective_uses_book_a_demo_cta(valid_brief):
    _, variants = _build(valid_brief)

    for variant in variants:
        assert variant.cta == "Book a Demo"


def test_offer_appears_in_body_copy(valid_brief):
    _, variants = _build(valid_brief)

    assert valid_brief.offer is not None
    expected = valid_brief.offer.lower()
    for variant in variants:
        assert expected in variant.primary_text.lower()


def test_image_prompt_starts_empty_before_image_provider(valid_brief):
    _, variants = _build(valid_brief)

    assert all(variant.image_prompt == "" for variant in variants)
