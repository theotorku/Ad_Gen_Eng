from __future__ import annotations

import json
from unittest.mock import patch

from ad_engine.assets import OpenAIImagesProvider
from ad_engine.models import AdVariant


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return b'{"data":[{"b64_json":"ZmFrZQ=="}]}'


def test_openai_images_provider_defaults_to_gpt_image_2(monkeypatch):
    monkeypatch.delenv("OPENAI_IMAGE_MODEL", raising=False)

    provider = OpenAIImagesProvider()

    assert provider.model == "gpt-image-2"


def test_openai_images_provider_sends_gpt_image_payload(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    provider = OpenAIImagesProvider()

    with patch("ad_engine.assets.request.urlopen", return_value=_FakeResponse()) as urlopen:
        provider._generate_image("A precise product ad.")

    api_request = urlopen.call_args.args[0]
    payload = json.loads(api_request.data.decode("utf-8"))
    assert payload == {
        "model": "gpt-image-2",
        "prompt": "A precise product ad.",
        "size": "1024x1024",
        "quality": "medium",
        "background": "auto",
        "output_format": "png",
    }


def test_openai_images_provider_does_not_generate_during_create_by_default(monkeypatch, valid_brief):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_IMAGE_GENERATE_DURING_CREATE", raising=False)
    provider = OpenAIImagesProvider()
    variant = AdVariant(
        channel="linkedin",
        angle="Speed up launch planning.",
        headline="Launch faster",
        primary_text="Move from brief to campaign faster.",
        cta="Book a demo",
        image_prompt="",
    )

    with patch("ad_engine.assets.request.urlopen") as urlopen:
        provider.attach_image_prompts(valid_brief, [variant])

    urlopen.assert_not_called()
    assert variant.image_prompt
    assert variant.generated_asset is None
    assert variant.image_status == "prompt_only"
