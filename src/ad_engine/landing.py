from __future__ import annotations

from html import escape

from .models import AdVariant, CampaignBrief, LandingSection


def build_landing_section(brief: CampaignBrief, variants: list[AdVariant]) -> LandingSection:
    primary_variant = variants[0] if variants else None
    headline = primary_variant.headline if primary_variant else f"{brief.product_name} for {brief.target_audience}"
    cta = primary_variant.cta if primary_variant else "Get Started"
    proof_points = _proof_points(brief)
    subheadline = (
        f"{brief.brand_name} helps {brief.target_audience} {brief.objective.lower()} "
        f"with {brief.value_props[0].lower()}."
    )
    html_snippet = _html_snippet(headline, subheadline, proof_points, cta)
    return LandingSection(
        headline=headline,
        subheadline=subheadline,
        proof_points=proof_points,
        cta=cta,
        html_snippet=html_snippet,
    )


def _proof_points(brief: CampaignBrief) -> list[str]:
    if brief.proof_points:
        return brief.proof_points[:3]
    points = brief.value_props[:3]
    if brief.service_areas:
        points.append(f"Localized for {', '.join(brief.service_areas[:3])}")
    if brief.offer:
        points.append(brief.offer)
    return points[:3]


def _html_snippet(
    headline: str,
    subheadline: str,
    proof_points: list[str],
    cta: str,
) -> str:
    items = "\n".join(f"    <li>{escape(point)}</li>" for point in proof_points)
    return "\n".join(
        [
            '<section class="campaign-landing-section">',
            f"  <h2>{escape(headline)}</h2>",
            f"  <p>{escape(subheadline)}</p>",
            "  <ul>",
            items,
            "  </ul>",
            f"  <a href=\"#contact\">{escape(cta)}</a>",
            "</section>",
        ]
    )
