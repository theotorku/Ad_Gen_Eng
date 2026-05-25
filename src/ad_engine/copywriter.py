from __future__ import annotations

from .models import AdVariant, CampaignBrief, CreativePlan
from .providers import CopyProvider


CHANNEL_LIMITS = {
    "facebook": 40,
    "instagram": 45,
    "linkedin": 60,
    "google_search": 30,
}


def generate_variants(brief: CampaignBrief, plan: CreativePlan) -> list[AdVariant]:
    variants: list[AdVariant] = []
    angles = _build_angles(brief, plan)

    for channel in brief.channels:
        for angle in angles:
            headline = _headline_for_channel(brief, channel, angle)
            primary_text = _body_for_channel(brief, channel, angle)
            cta = _cta_for_objective(brief.objective, channel)
            variants.append(
                AdVariant(
                    channel=channel,
                    angle=angle,
                    headline=_trim(headline, CHANNEL_LIMITS[channel]),
                    primary_text=primary_text,
                    cta=cta,
                    image_prompt="",
                )
            )

    return variants


def _build_angles(brief: CampaignBrief, plan: CreativePlan) -> list[str]:
    angles = []
    for hook in plan.hooks:
        angles.append(hook)
    while len(angles) < 3:
        angles.append(f"Reach your goal with {brief.product_name}.")
    return angles[:3]


def _headline_for_channel(brief: CampaignBrief, channel: str, angle: str) -> str:
    angle_focus = _angle_focus(angle)
    if channel == "google_search":
        return f"{brief.product_name}: {angle_focus}"
    if channel == "linkedin":
        return f"{brief.product_name} for teams tackling {angle_focus.lower()}"
    if channel == "instagram":
        return f"Make the switch from {angle_focus.lower()}"
    return f"Fix {angle_focus.lower()} with {brief.product_name}"


def _body_for_channel(brief: CampaignBrief, channel: str, angle: str) -> str:
    offer_line = f" {brief.offer}." if brief.offer else ""
    base = (
        f"{angle} {brief.brand_name} gives {brief.target_audience} a better path to "
        f"{brief.objective.lower()} with {brief.value_props[0].lower()}."
    )

    if channel == "google_search":
        return (
            f"{brief.product_name} helps {brief.target_audience} {brief.objective.lower()}."
            f" Built for {brief.value_props[0].lower()}.{offer_line}"
        ).strip()
    if channel == "linkedin":
        return (
            f"{base} Designed for professionals who need clearer outcomes and less waste.{offer_line}"
        ).strip()
    if channel == "instagram":
        return (
            f"{base} Feel the difference in the day-to-day experience, not just the promise.{offer_line}"
        ).strip()
    return (
        f"{base} Start with a solution that feels easier, faster, and more reliable.{offer_line}"
    ).strip()


def _cta_for_objective(objective: str, channel: str) -> str:
    objective_lower = objective.lower()
    if "lead" in objective_lower or "demo" in objective_lower:
        return "Book a Demo"
    if "sale" in objective_lower or "purchase" in objective_lower:
        return "Shop Now"
    if channel == "google_search":
        return "Learn More"
    return "Get Started"


def _trim(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    candidate = text[:limit].rstrip()
    last_space = candidate.rfind(" ")
    if last_space >= max(1, limit // 2):
        return candidate[:last_space].rstrip()
    return candidate


def _angle_focus(angle: str) -> str:
    lowered = angle.lower().strip(".")
    replacements = [
        ("leave behind ", ""),
        (" with a simpler approach", ""),
        ("get results through ", ""),
    ]
    for source, target in replacements:
        lowered = lowered.replace(source, target)
    return lowered.capitalize()


class RuleBasedCopyProvider(CopyProvider):
    provider_name = "rule_based"

    def generate_variants(self, brief: CampaignBrief, plan: CreativePlan) -> list[AdVariant]:
        return generate_variants(brief, plan)
