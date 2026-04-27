from __future__ import annotations

from .models import AdBundle, CampaignBrief
from .providers import ProviderStack, build_provider_stack
from .review import review_variants


class AdGenerationEngine:
    def __init__(self, providers: ProviderStack | None = None) -> None:
        self.providers = providers or build_provider_stack()

    def run(self, payload: dict) -> AdBundle:
        brief = CampaignBrief.from_dict(payload)
        plan = self.providers.planning.build_creative_plan(brief)
        variants = self.providers.copy.generate_variants(brief, plan)
        self.providers.image.attach_image_prompts(brief, variants)
        quality_summary = review_variants(brief, variants)
        return AdBundle(
            brief=brief,
            creative_plan=plan,
            variants=variants,
            quality_summary=quality_summary,
        )
