from __future__ import annotations

import pytest

from ad_engine.models import CampaignBrief


def test_from_dict_returns_normalized_brief(brief_payload):
    brief = CampaignBrief.from_dict(brief_payload)

    assert brief.brand_name == "Northstar AI"
    assert brief.tone == "confident"
    assert brief.channels == ["linkedin", "facebook", "google_search"]
    assert brief.value_props[0] == "faster ad iteration"


def test_blank_tone_falls_back_to_default(brief_payload):
    brief_payload["tone"] = "   "

    brief = CampaignBrief.from_dict(brief_payload)

    assert brief.tone == "confident"


def test_string_list_fields_are_split_into_single_item(brief_payload):
    brief_payload["pain_points"] = "single pain point"

    brief = CampaignBrief.from_dict(brief_payload)

    assert brief.pain_points == ["single pain point"]


@pytest.mark.parametrize("value", [123, {"linkedin": True}])
def test_invalid_list_field_shape_raises_value_error(brief_payload, value):
    brief_payload["value_props"] = value

    with pytest.raises(ValueError, match="strings or arrays"):
        CampaignBrief.from_dict(brief_payload)


@pytest.mark.parametrize(
    "field",
    ["brand_name", "product_name", "objective", "target_audience"],
)
def test_missing_required_text_field_raises(brief_payload, field):
    brief_payload[field] = ""

    with pytest.raises(ValueError, match="Missing required brief fields"):
        CampaignBrief.from_dict(brief_payload)


def test_missing_value_props_raises(brief_payload):
    brief_payload["value_props"] = []

    with pytest.raises(ValueError, match="value proposition"):
        CampaignBrief.from_dict(brief_payload)


def test_missing_channels_raises(brief_payload):
    brief_payload["channels"] = []

    with pytest.raises(ValueError, match="channel"):
        CampaignBrief.from_dict(brief_payload)


def test_unsupported_channel_raises(brief_payload):
    brief_payload["channels"] = ["facebook", "tiktok"]

    with pytest.raises(ValueError, match="Unsupported channels"):
        CampaignBrief.from_dict(brief_payload)


def test_to_dict_round_trip(valid_brief):
    payload = valid_brief.to_dict()

    rebuilt = CampaignBrief.from_dict(payload)

    assert rebuilt.to_dict() == payload
