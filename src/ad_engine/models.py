from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


SUPPORTED_CHANNELS = {"facebook", "instagram", "linkedin", "google_search"}

MAX_TEXT_FIELD_LENGTH = 500
MAX_OFFER_LENGTH = 1000
MAX_LIST_ITEM_LENGTH = 500
MAX_LIST_ITEMS = 20

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE_RUN_RE = re.compile(r"\s+")


@dataclass(slots=True)
class CampaignBrief:
    brand_name: str
    product_name: str
    objective: str
    target_audience: str
    pain_points: list[str]
    value_props: list[str]
    offer: str | None = None
    tone: str = "confident"
    channels: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CampaignBrief":
        brief = cls(
            brand_name=_clean_text(str(payload.get("brand_name", ""))),
            product_name=_clean_text(str(payload.get("product_name", ""))),
            objective=_clean_text(str(payload.get("objective", ""))),
            target_audience=_clean_text(str(payload.get("target_audience", ""))),
            pain_points=_normalize_list(payload.get("pain_points")),
            value_props=_normalize_list(payload.get("value_props")),
            offer=_normalize_optional_text(payload.get("offer")),
            tone=_normalize_optional_text(payload.get("tone")) or "confident",
            channels=_normalize_list(payload.get("channels")),
            constraints=_normalize_list(payload.get("constraints")),
        )
        brief.validate()
        return brief

    def validate(self) -> None:
        required_fields = {
            "brand_name": self.brand_name,
            "product_name": self.product_name,
            "objective": self.objective,
            "target_audience": self.target_audience,
        }
        missing = [name for name, value in required_fields.items() if not value]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required brief fields: {joined}")

        if not self.value_props:
            raise ValueError("At least one value proposition is required.")
        if not self.channels:
            raise ValueError("At least one channel is required.")

        invalid_channels = [channel for channel in self.channels if channel not in SUPPORTED_CHANNELS]
        if invalid_channels:
            joined = ", ".join(invalid_channels)
            raise ValueError(f"Unsupported channels: {joined}")

        for name, value in required_fields.items():
            if len(value) > MAX_TEXT_FIELD_LENGTH:
                raise ValueError(
                    f"Field '{name}' exceeds maximum length of {MAX_TEXT_FIELD_LENGTH} characters."
                )

        if self.offer is not None and len(self.offer) > MAX_OFFER_LENGTH:
            raise ValueError(
                f"Field 'offer' exceeds maximum length of {MAX_OFFER_LENGTH} characters."
            )
        if self.tone and len(self.tone) > MAX_TEXT_FIELD_LENGTH:
            raise ValueError(
                f"Field 'tone' exceeds maximum length of {MAX_TEXT_FIELD_LENGTH} characters."
            )

        for list_name, items in (
            ("pain_points", self.pain_points),
            ("value_props", self.value_props),
            ("constraints", self.constraints),
        ):
            if len(items) > MAX_LIST_ITEMS:
                raise ValueError(
                    f"Field '{list_name}' exceeds maximum of {MAX_LIST_ITEMS} items."
                )
            for item in items:
                if len(item) > MAX_LIST_ITEM_LENGTH:
                    raise ValueError(
                        f"Items in '{list_name}' must be {MAX_LIST_ITEM_LENGTH} characters or fewer."
                    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CreativePlan:
    strategy_summary: str
    audience_promise: str
    hooks: list[str]
    messaging_pillars: list[str]
    channel_notes: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GeneratedAsset:
    path: str
    mime_type: str
    provider: str
    prompt: str
    revised_prompt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AdVariant:
    channel: str
    angle: str
    headline: str
    primary_text: str
    cta: str
    image_prompt: str
    generated_asset: GeneratedAsset | None = None
    review_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QualitySummary:
    strengths: list[str]
    risks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AdBundle:
    brief: CampaignBrief
    creative_plan: CreativePlan
    variants: list[AdVariant]
    quality_summary: QualitySummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief": self.brief.to_dict(),
            "creative_plan": self.creative_plan.to_dict(),
            "variants": [variant.to_dict() for variant in self.variants],
            "quality_summary": self.quality_summary.to_dict(),
        }


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    else:
        items = list(value)
    cleaned = [_clean_text(str(item)) for item in items]
    return [item for item in cleaned if item]


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = _clean_text(str(value))
    return normalized or None


def _clean_text(value: str) -> str:
    stripped = _CONTROL_CHARS_RE.sub("", value)
    collapsed = _WHITESPACE_RUN_RE.sub(" ", stripped)
    return collapsed.strip()
