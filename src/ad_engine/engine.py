from __future__ import annotations

from uuid import uuid4

from .landing import build_landing_section
from .models import AdBundle, CampaignBrief, GenerationJob
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
        landing_section = build_landing_section(brief, variants)
        generation_jobs = [
            GenerationJob(
                job_id=f"job_{uuid4().hex[:12]}",
                kind="image_generation",
                status="available",
                provider=self.providers.image.provider_name,
                estimated_credits=len(variants),
                target="all_variants",
            )
        ]
        return AdBundle(
            brief=brief,
            creative_plan=plan,
            variants=variants,
            quality_summary=quality_summary,
            landing_section=landing_section,
            generation_jobs=generation_jobs,
            cost_summary={
                "estimated_image_credits": len(variants),
                "image_model": getattr(self.providers.image, "model", None),
            },
        )
