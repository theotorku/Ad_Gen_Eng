from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from .models import AdVariant, CampaignBrief, CreativePlan


class PlanningProvider(Protocol):
    provider_name: str

    def build_creative_plan(self, brief: CampaignBrief) -> CreativePlan:
        ...


class CopyProvider(Protocol):
    provider_name: str

    def generate_variants(self, brief: CampaignBrief, plan: CreativePlan) -> list[AdVariant]:
        ...


class ImageProvider(Protocol):
    provider_name: str

    def attach_image_prompts(self, brief: CampaignBrief, variants: list[AdVariant]) -> None:
        ...


@dataclass(slots=True)
class ProviderSettings:
    planning_provider: str = "rule_based"
    copy_provider: str = "rule_based"
    image_provider: str = "prompt_template"

    @classmethod
    def from_env(cls) -> "ProviderSettings":
        return cls(
            planning_provider=os.getenv("AD_ENGINE_PLANNING_PROVIDER", "rule_based").strip() or "rule_based",
            copy_provider=os.getenv("AD_ENGINE_COPY_PROVIDER", "rule_based").strip() or "rule_based",
            image_provider=os.getenv("AD_ENGINE_IMAGE_PROVIDER", "prompt_template").strip() or "prompt_template",
        )


@dataclass(slots=True)
class ProviderStack:
    planning: PlanningProvider
    copy: CopyProvider
    image: ImageProvider

    def describe(self) -> dict[str, str]:
        return {
            "planning_provider": self.planning.provider_name,
            "copy_provider": self.copy.provider_name,
            "image_provider": self.image.provider_name,
        }


def build_provider_stack(settings: ProviderSettings | None = None) -> ProviderStack:
    from .assets import OpenAIImagesProvider, PromptTemplateImageProvider
    from .copywriter import RuleBasedCopyProvider
    from .planner import RuleBasedPlanningProvider

    resolved = settings or ProviderSettings.from_env()

    planning_registry: dict[str, type[PlanningProvider]] = {
        "rule_based": RuleBasedPlanningProvider,
    }
    copy_registry: dict[str, type[CopyProvider]] = {
        "rule_based": RuleBasedCopyProvider,
    }
    image_registry: dict[str, type[ImageProvider]] = {
        "prompt_template": PromptTemplateImageProvider,
        "openai_images": OpenAIImagesProvider,
    }

    return ProviderStack(
        planning=_build_provider("planning", resolved.planning_provider, planning_registry),
        copy=_build_provider("copy", resolved.copy_provider, copy_registry),
        image=_build_provider("image", resolved.image_provider, image_registry),
    )


def _build_provider(kind: str, name: str, registry: dict[str, type[object]]) -> object:
    provider_class = registry.get(name)
    if provider_class is None:
        supported = ", ".join(sorted(registry))
        raise ValueError(f"Unknown {kind} provider '{name}'. Supported providers: {supported}")
    return provider_class()
