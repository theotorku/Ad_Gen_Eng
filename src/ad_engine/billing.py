from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

# Usage metric keys (also the column values stored by the usage counter).
METRIC_IMAGES = "images"
METRIC_CAMPAIGNS = "campaigns"

# Feature slugs. These must match the feature slugs configured in Clerk Billing
# so the plan-derived entitlements here stay aligned with the dashboard.
FEATURE_IMAGE_GENERATION = "image_generation"
FEATURE_API_ACCESS = "api_access"


@dataclass(frozen=True, slots=True)
class PlanLimits:
    # `None` means unlimited (fair use) for that metric.
    images_per_month: int | None
    campaigns_per_month: int | None
    features: frozenset[str]


# Single source of truth for what each plan includes. Plan slugs MUST match the
# plan slugs configured in Clerk Billing (the `pla` claim on the session token).
# Mirrors the published pricing: Starter $49 / Pro $99 / Agency $249.
PLAN_LIMITS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        images_per_month=0,
        campaigns_per_month=3,
        features=frozenset(),
    ),
    "starter": PlanLimits(
        images_per_month=30,
        campaigns_per_month=25,
        features=frozenset({FEATURE_IMAGE_GENERATION}),
    ),
    "pro": PlanLimits(
        images_per_month=150,
        campaigns_per_month=100,
        features=frozenset({FEATURE_IMAGE_GENERATION}),
    ),
    "agency": PlanLimits(
        images_per_month=600,
        campaigns_per_month=None,
        features=frozenset({FEATURE_IMAGE_GENERATION, FEATURE_API_ACCESS}),
    ),
}


@dataclass(frozen=True, slots=True)
class BillingSettings:
    # Ships dark: enforcement is off until Clerk Billing is live and this is set.
    enforce_limits: bool = False
    # Plan applied when the token carries no plan claim (e.g. trial not started,
    # or non-Clerk auth). Defaults to the most restrictive plan.
    default_plan: str = "free"

    @classmethod
    def from_env(cls) -> "BillingSettings":
        return cls(
            enforce_limits=_env_flag("AD_ENGINE_ENFORCE_PLAN_LIMITS"),
            default_plan=(os.getenv("AD_ENGINE_DEFAULT_PLAN", "free").strip() or "free"),
        )


def resolve_plan_limits(plan: str | None, *, default_plan: str = "free") -> PlanLimits:
    if plan and plan in PLAN_LIMITS:
        return PLAN_LIMITS[plan]
    return PLAN_LIMITS.get(default_plan) or PLAN_LIMITS["free"]


def metric_allowance(limits: PlanLimits, metric: str) -> int | None:
    if metric == METRIC_IMAGES:
        return limits.images_per_month
    if metric == METRIC_CAMPAIGNS:
        return limits.campaigns_per_month
    raise ValueError(f"Unknown usage metric '{metric}'.")


def usage_period(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return moment.strftime("%Y-%m")


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
