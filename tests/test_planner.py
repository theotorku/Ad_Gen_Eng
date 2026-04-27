from __future__ import annotations

from ad_engine.planner import CHANNEL_NOTES, build_creative_plan


def test_creative_plan_uses_brief_inputs(valid_brief):
    plan = build_creative_plan(valid_brief)

    assert valid_brief.product_name in plan.strategy_summary
    assert valid_brief.target_audience in plan.strategy_summary
    assert valid_brief.brand_name in plan.audience_promise


def test_messaging_pillars_capped_at_three(valid_brief):
    plan = build_creative_plan(valid_brief)

    assert len(plan.messaging_pillars) <= 3
    assert plan.messaging_pillars == valid_brief.value_props[:3]


def test_channel_notes_match_selected_channels(valid_brief):
    plan = build_creative_plan(valid_brief)

    assert set(plan.channel_notes) == set(valid_brief.channels)
    for channel, note in plan.channel_notes.items():
        assert note == CHANNEL_NOTES[channel]


def test_hooks_capped_at_three(valid_brief):
    plan = build_creative_plan(valid_brief)

    assert 1 <= len(plan.hooks) <= 3


def test_offer_promotes_to_hook_when_room_remains(brief_payload):
    from ad_engine.models import CampaignBrief

    brief_payload["pain_points"] = ["slow setup"]
    brief_payload["value_props"] = ["faster iteration"]
    brief = CampaignBrief.from_dict(brief_payload)

    plan = build_creative_plan(brief)

    joined = " ".join(plan.hooks).lower()
    assert brief.offer is not None
    assert brief.offer.lower() in joined


def test_plan_falls_back_when_pain_points_missing(brief_payload):
    from ad_engine.models import CampaignBrief

    brief_payload["pain_points"] = []
    brief = CampaignBrief.from_dict(brief_payload)

    plan = build_creative_plan(brief)

    assert "friction" in plan.strategy_summary
