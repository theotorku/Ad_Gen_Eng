from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ad_engine.billing import (
    FEATURE_API_ACCESS,
    FEATURE_IMAGE_GENERATION,
    METRIC_CAMPAIGNS,
    METRIC_IMAGES,
    BillingSettings,
    metric_allowance,
    resolve_plan_limits,
    usage_period,
)


def test_resolve_known_plan_returns_its_limits():
    limits = resolve_plan_limits("pro")

    assert limits.images_per_month == 150
    assert limits.campaigns_per_month == 100
    assert FEATURE_IMAGE_GENERATION in limits.features


def test_resolve_unknown_plan_falls_back_to_default():
    limits = resolve_plan_limits("enterprise-typo", default_plan="free")

    assert limits.images_per_month == 0
    assert FEATURE_IMAGE_GENERATION not in limits.features


def test_resolve_missing_plan_falls_back_to_default():
    assert resolve_plan_limits(None, default_plan="starter").images_per_month == 30


def test_agency_plan_is_unlimited_campaigns_and_has_api():
    limits = resolve_plan_limits("agency")

    assert limits.campaigns_per_month is None
    assert FEATURE_API_ACCESS in limits.features
    assert metric_allowance(limits, METRIC_CAMPAIGNS) is None
    assert metric_allowance(limits, METRIC_IMAGES) == 600


def test_metric_allowance_rejects_unknown_metric():
    with pytest.raises(ValueError):
        metric_allowance(resolve_plan_limits("pro"), "seats")


def test_usage_period_is_calendar_month():
    assert usage_period(datetime(2026, 3, 9, tzinfo=timezone.utc)) == "2026-03"


def test_billing_settings_default_off():
    settings = BillingSettings()

    assert settings.enforce_limits is False
    assert settings.default_plan == "free"
