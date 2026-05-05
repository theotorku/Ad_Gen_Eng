from __future__ import annotations

import json
from unittest.mock import patch

from ad_engine.assets import OpenAIImagesProvider


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
