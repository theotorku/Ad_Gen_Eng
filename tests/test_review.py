from __future__ import annotations

from ad_engine.copywriter import generate_variants
from ad_engine.models import AdVariant
from ad_engine.planner import build_creative_plan
from ad_engine.review import review_variants


def test_clean_variants_produce_no_risks(valid_brief):
    plan = build_creative_plan(valid_brief)
    variants = generate_variants(valid_brief, plan)

    summary = review_variants(valid_brief, variants)

    assert any("Generated" in strength for strength in summary.strengths)
    assert summary.risks == [
        "No obvious rule-based issues detected in the MVP review pass."
    ]


def test_overlong_headline_is_flagged(valid_brief):
    variant = AdVariant(
        channel="google_search",
        angle="x",
        headline="x" * 200,
        primary_text="any body copy",
        cta="Learn More",
        image_prompt="",
    )

    summary = review_variants(valid_brief, [variant])

    assert any("Headline exceeds" in note for note in variant.review_notes)
    assert any("Headline exceeds" in risk for risk in summary.risks)


def test_missing_offer_in_body_is_flagged(valid_brief):
    variant = AdVariant(
        channel="facebook",
        angle="x",
        headline="short",
        primary_text="copy without the special phrase",
        cta="Get Started",
        image_prompt="",
    )

    summary = review_variants(valid_brief, [variant])

    assert any("Offer exists" in note for note in variant.review_notes)
    assert any("Offer exists" in risk for risk in summary.risks)


def test_duplicate_headlines_are_flagged(valid_brief):
    a = AdVariant(
        channel="facebook",
        angle="a",
        headline="Same Headline",
        primary_text=valid_brief.offer.lower() if valid_brief.offer else "x",
        cta="Get Started",
        image_prompt="",
    )
    b = AdVariant(
        channel="linkedin",
        angle="b",
        headline="Same Headline",
        primary_text=valid_brief.offer.lower() if valid_brief.offer else "x",
        cta="Get Started",
        image_prompt="",
    )

    review_variants(valid_brief, [a, b])

    assert any("repeated" in note for note in b.review_notes)
    assert not any("repeated" in note for note in a.review_notes)


def test_risks_are_deduplicated(valid_brief):
    overlong = "x" * 200
    a = AdVariant(
        channel="facebook",
        angle="a",
        headline=overlong,
        primary_text="x",
        cta="Get Started",
        image_prompt="",
    )
    b = AdVariant(
        channel="linkedin",
        angle="b",
        headline=overlong,
        primary_text="x",
        cta="Get Started",
        image_prompt="",
    )

    summary = review_variants(valid_brief, [a, b])

    headline_risks = [risk for risk in summary.risks if "Headline exceeds" in risk]
    assert len(headline_risks) == 1
