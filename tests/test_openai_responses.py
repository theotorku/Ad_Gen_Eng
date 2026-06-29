from __future__ import annotations

import pytest

from ad_engine.openai_responses import (
    OpenAIResponsesCopyProvider,
    OpenAIResponsesPlanningProvider,
)


class FakeResponsesClient:
    def __init__(self, payload):
        self.payload = payload

    def json_response(self, **kwargs):
        return self.payload


def test_openai_responses_planning_provider_maps_structured_output(valid_brief):
    provider = OpenAIResponsesPlanningProvider(
        FakeResponsesClient(
            {
                "strategy_summary": "Win on local trust and fast service.",
                "audience_promise": "Reliable help without slow vendor cycles.",
                "hooks": ["Local proof", "Fast turnaround", "Clear offer"],
                "messaging_pillars": ["Trust", "Speed", "Clarity"],
                "channel_notes": {
                    channel: f"Use {channel} fit."
                    for channel in valid_brief.channels
                },
            }
        )
    )

    plan = provider.build_creative_plan(valid_brief)

    assert plan.strategy_summary == "Win on local trust and fast service."
    assert plan.messaging_pillars == ["Trust", "Speed", "Clarity"]
    assert set(plan.channel_notes) == set(valid_brief.channels)


def test_openai_responses_copy_provider_maps_structured_output(valid_brief):
    provider = OpenAIResponsesCopyProvider(
        FakeResponsesClient(
            {
                "variants": [
                    {
                        "channel": valid_brief.channels[0],
                        "angle": "Local trust",
                        "headline": "Book trusted help",
                        "primary_text": "A clearer path for local teams.",
                        "cta": "Book Now",
                        "image_prompt": "A realistic local service ad.",
                    }
                ]
            }
        )
    )

    variants = provider.generate_variants(
        valid_brief,
        plan=type("Plan", (), {"to_dict": lambda self: {}})(),
    )

    assert variants[0].channel == valid_brief.channels[0]
    assert variants[0].image_prompt == "A realistic local service ad."


def test_openai_responses_copy_provider_rejects_unrequested_channel(valid_brief):
    provider = OpenAIResponsesCopyProvider(
        FakeResponsesClient(
            {
                "variants": [
                    {
                        "channel": "tiktok",
                        "angle": "Local trust",
                        "headline": "Book trusted help",
                        "primary_text": "A clearer path for local teams.",
                        "cta": "Book Now",
                        "image_prompt": "A realistic local service ad.",
                    }
                ]
            }
        )
    )

    with pytest.raises(ValueError, match="unsupported channel"):
        provider.generate_variants(
            valid_brief,
            plan=type("Plan", (), {"to_dict": lambda self: {}})(),
        )
