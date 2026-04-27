from __future__ import annotations

from .models import CampaignBrief, CreativePlan
from .providers import PlanningProvider


CHANNEL_NOTES = {
    "facebook": "Write for fast clarity, emotional relevance, and a visible CTA.",
    "instagram": "Lead with vivid emotion and lifestyle framing that can pair with a strong visual.",
    "linkedin": "Keep the tone professional, outcome-driven, and credible.",
    "google_search": "Stay concise, direct, and intent-matched.",
}


def build_creative_plan(brief: CampaignBrief) -> CreativePlan:
    hooks = _build_hooks(brief)
    pillars = brief.value_props[:3]
    strategy_summary = (
        f"Position {brief.product_name} as the practical answer for {brief.target_audience} "
        f"who want to {brief.objective.lower()} without dealing with {brief.pain_points[0].lower() if brief.pain_points else 'friction'}."
    )
    audience_promise = (
        f"{brief.brand_name} helps {brief.target_audience} get a better outcome through "
        f"{brief.value_props[0].lower()}."
    )
    channel_notes = {channel: CHANNEL_NOTES[channel] for channel in brief.channels}

    return CreativePlan(
        strategy_summary=strategy_summary,
        audience_promise=audience_promise,
        hooks=hooks,
        messaging_pillars=pillars,
        channel_notes=channel_notes,
    )


def _build_hooks(brief: CampaignBrief) -> list[str]:
    hooks: list[str] = []

    for pain_point in brief.pain_points[:2]:
        hooks.append(f"Leave behind {pain_point.lower()} with a simpler approach.")
    for value_prop in brief.value_props[:2]:
        hooks.append(f"Get results through {value_prop.lower()}.")

    if brief.offer:
        hooks.append(f"Act now to claim {brief.offer.lower()}.")

    if not hooks:
        hooks.append(f"Choose a smarter way to {brief.objective.lower()}.")

    return hooks[:3]


class RuleBasedPlanningProvider(PlanningProvider):
    provider_name = "rule_based"

    def build_creative_plan(self, brief: CampaignBrief) -> CreativePlan:
        return build_creative_plan(brief)
