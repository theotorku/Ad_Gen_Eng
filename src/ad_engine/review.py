from __future__ import annotations

from .copywriter import CHANNEL_LIMITS
from .models import AdVariant, CampaignBrief, QualitySummary


def review_variants(brief: CampaignBrief, variants: list[AdVariant]) -> QualitySummary:
    seen_headlines: set[str] = set()
    risks: list[str] = []

    for variant in variants:
        if len(variant.headline) > CHANNEL_LIMITS[variant.channel]:
            variant.review_notes.append("Headline exceeds the recommended length for this channel.")

        if brief.offer and brief.offer.lower() not in variant.primary_text.lower():
            variant.review_notes.append("Offer exists in brief but is not clearly stated in body copy.")

        if variant.headline in seen_headlines:
            variant.review_notes.append("Headline is repeated across variants.")
        seen_headlines.add(variant.headline)

        risks.extend(variant.review_notes)

    strengths = [
        f"Generated {len(variants)} variants across {len(brief.channels)} channels.",
        "Each variant includes aligned copy, CTA, and image prompt.",
        "Output is structured for a future API or UI layer.",
    ]

    deduped_risks = list(dict.fromkeys(risks))
    if not deduped_risks:
        deduped_risks = ["No obvious rule-based issues detected in the MVP review pass."]

    return QualitySummary(strengths=strengths, risks=deduped_risks)
