from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from .models import AdVariant, CampaignBrief, CreativePlan
from .providers import CopyProvider, PlanningProvider


DEFAULT_OPENAI_TEXT_MODEL = "gpt-5.1"
RESPONSES_URL = "https://api.openai.com/v1/responses"


@dataclass(slots=True)
class OpenAIResponsesClient:
    api_key: str | None = None
    model: str = DEFAULT_OPENAI_TEXT_MODEL
    timeout_seconds: int = 120

    @classmethod
    def from_env(cls) -> "OpenAIResponsesClient":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_TEXT_MODEL", DEFAULT_OPENAI_TEXT_MODEL).strip()
            or DEFAULT_OPENAI_TEXT_MODEL,
            timeout_seconds=int(os.getenv("OPENAI_TEXT_TIMEOUT_SECONDS", "120").strip() or "120"),
        )

    def json_response(
        self,
        *,
        instructions: str,
        input_payload: dict[str, Any],
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for openai_responses providers.")

        payload = {
            "model": self.model,
            "instructions": instructions,
            "input": json.dumps(input_payload),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        }
        api_request = request.Request(
            RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(api_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            message = _extract_openai_error_message(details) or f"HTTP {exc.code}"
            raise ValueError(f"OpenAI Responses API failed: {message}") from exc
        except error.URLError as exc:
            raise ValueError("OpenAI Responses API failed: upstream request error.") from exc

        text = _extract_output_text(response_payload)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAI Responses API returned non-JSON output.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI Responses API returned an unexpected output shape.")
        return parsed


class OpenAIResponsesPlanningProvider(PlanningProvider):
    provider_name = "openai_responses"

    def __init__(self, client: OpenAIResponsesClient | None = None) -> None:
        self.client = client or OpenAIResponsesClient.from_env()

    def build_creative_plan(self, brief: CampaignBrief) -> CreativePlan:
        payload = self.client.json_response(
            instructions=(
                "You are a senior performance creative strategist. Build a concise ad "
                "creative plan grounded only in the provided brief. Respect constraints, "
                "banned claims, service areas, and proof points."
            ),
            input_payload={"brief": brief.to_dict()},
            schema_name="creative_plan",
            schema=_creative_plan_schema(brief.channels),
        )
        return CreativePlan(
            strategy_summary=str(payload["strategy_summary"]).strip(),
            audience_promise=str(payload["audience_promise"]).strip(),
            hooks=[str(item).strip() for item in payload["hooks"]][:3],
            messaging_pillars=[str(item).strip() for item in payload["messaging_pillars"]][:3],
            channel_notes={str(key): str(value) for key, value in payload["channel_notes"].items()},
        )


class OpenAIResponsesCopyProvider(CopyProvider):
    provider_name = "openai_responses"

    def __init__(self, client: OpenAIResponsesClient | None = None) -> None:
        self.client = client or OpenAIResponsesClient.from_env()

    def generate_variants(self, brief: CampaignBrief, plan: CreativePlan) -> list[AdVariant]:
        payload = self.client.json_response(
            instructions=(
                "You are a direct-response copywriter. Generate exactly three distinct "
                "variants per requested channel. Keep copy policy-conscious, specific, "
                "and ready for review. Return only schema-valid JSON."
            ),
            input_payload={
                "brief": brief.to_dict(),
                "creative_plan": plan.to_dict(),
                "requirements": {
                    "variants_per_channel": 3,
                    "channels": brief.channels,
                    "avoid_claims": brief.banned_claims,
                },
            },
            schema_name="ad_variants",
            schema=_ad_variants_schema(),
        )
        variants = []
        for item in payload["variants"]:
            channel = str(item["channel"])
            if channel not in brief.channels:
                raise ValueError(f"OpenAI copy provider returned unsupported channel '{channel}'.")
            variants.append(
                AdVariant(
                    channel=channel,
                    angle=str(item["angle"]).strip(),
                    headline=str(item["headline"]).strip(),
                    primary_text=str(item["primary_text"]).strip(),
                    cta=str(item["cta"]).strip(),
                    image_prompt=str(item.get("image_prompt", "")).strip(),
                )
            )
        return variants


def _creative_plan_schema(channels: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "strategy_summary",
            "audience_promise",
            "hooks",
            "messaging_pillars",
            "channel_notes",
        ],
        "properties": {
            "strategy_summary": {"type": "string"},
            "audience_promise": {"type": "string"},
            "hooks": {"type": "array", "minItems": 3, "maxItems": 3, "items": {"type": "string"}},
            "messaging_pillars": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {"type": "string"},
            },
            "channel_notes": {
                "type": "object",
                "additionalProperties": False,
                "required": channels,
                "properties": {channel: {"type": "string"} for channel in channels},
            },
        },
    }


def _ad_variants_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["variants"],
        "properties": {
            "variants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["channel", "angle", "headline", "primary_text", "cta", "image_prompt"],
                    "properties": {
                        "channel": {"type": "string"},
                        "angle": {"type": "string"},
                        "headline": {"type": "string"},
                        "primary_text": {"type": "string"},
                        "cta": {"type": "string"},
                        "image_prompt": {"type": "string"},
                    },
                },
            }
        },
    }


def _extract_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    if not chunks:
        raise ValueError("OpenAI Responses API returned no output text.")
    return "".join(chunks)


def _extract_openai_error_message(response_text: str) -> str | None:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return None
    error_payload = payload.get("error")
    if isinstance(error_payload, dict) and isinstance(error_payload.get("message"), str):
        return error_payload["message"]
    return None
