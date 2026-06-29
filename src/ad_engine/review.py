from __future__ import annotations

from .copywriter import CHANNEL_LIMITS
from .models import AdVariant, CampaignBrief, QualitySummary


def review_variants(brief: CampaignBrief, variants: list[AdVariant]) -> QualitySummary:
    seen_headlines: set[str] = set()
    risks: list[str] = []

    for variant in variants:
        score = 100
        if len(variant.headline) > CHANNEL_LIMITS[variant.channel]:
            variant.review_notes.append("Headline exceeds the recommended length for this channel.")
            variant.suggested_fixes.append("Shorten the headline to fit the channel limit.")
            score -= 20

        if brief.offer and brief.offer.lower() not in variant.primary_text.lower():
            variant.review_notes.append("Offer exists in brief but is not clearly stated in body copy.")
            variant.suggested_fixes.append("Work the offer into the body copy without making it feel tacked on.")
            score -= 15

        if variant.headline in seen_headlines:
            variant.review_notes.append("Headline is repeated across variants.")
            variant.suggested_fixes.append("Rewrite the headline with a distinct hook.")
            score -= 15
        seen_headlines.add(variant.headline)
        variant.review_score = max(0, score)

        risks.extend(variant.review_notes)

    strengths = [
        f"Generated {len(variants)} variants across {len(brief.channels)} channels.",
        "Each variant includes aligned copy, CTA, and image prompt.",
        "Output is structured for a future API or UI layer.",
    ]

    deduped_risks = list(dict.fromkeys(risks))
    if not deduped_risks:
        deduped_risks = ["No obvious rule-based issues detected in the MVP review pass."]

    scores = {
        "average_variant_score": round(
            sum(variant.review_score or 0 for variant in variants) / len(variants)
        )
        if variants
        else 0,
        "variant_count": len(variants),
    }
    suggested_fixes = list(
        dict.fromkeys(fix for variant in variants for fix in variant.suggested_fixes)
    )

    return QualitySummary(
        strengths=strengths,
        risks=deduped_risks,
        scores=scores,
        suggested_fixes=suggested_fixes,
    )
