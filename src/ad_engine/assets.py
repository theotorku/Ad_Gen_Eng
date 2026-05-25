from __future__ import annotations

import base64
import io
import json
import os
import re
from pathlib import Path
from urllib import error, request
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from .models import AdVariant, CampaignBrief, GeneratedAsset
from .providers import ImageProvider


DEFAULT_OUTPUT_DIR = "data/generated_assets"
DEFAULT_BRAND_LOGO_DIR = "data/brand_logos"
DEFAULT_OPENAI_IMAGE_MODEL = "gpt-image-2"

BRAND_LOGO_MAX_BYTES = 2 * 1024 * 1024
BRAND_LOGO_ALLOWED_MIME_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
}

_PROMPT_FIELD_MAX_LENGTH = 280
_PROMPT_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def attach_image_prompts(brief: CampaignBrief, variants: list[AdVariant]) -> None:
    visual_style = _visual_style_for_tone(brief.tone)
    brand = _sanitize_for_prompt(brief.brand_name)
    product = _sanitize_for_prompt(brief.product_name)
    audience = _sanitize_for_prompt(brief.target_audience)
    primary_value = _sanitize_for_prompt(brief.value_props[0]).lower()

    logo_clause = (
        " Leave the bottom-right corner clear of text or busy details so a brand logo can sit there cleanly."
        if brief.brand_logo
        else ""
    )
    for variant in variants:
        channel = _sanitize_for_prompt(variant.channel)
        cleaned_angle = _sanitize_for_prompt(variant.angle.rstrip("."))
        variant.image_prompt = (
            f"Create an ad image for {brand} promoting {product}. "
            f"Audience: {audience}. Channel: {channel}. "
            f"Visual mood: {visual_style}. "
            f"Highlight this angle: {cleaned_angle}. "
            f"Show the benefit of {primary_value} in a realistic, campaign-ready composition."
            f"{logo_clause}"
        )


def _sanitize_for_prompt(value: str) -> str:
    cleaned = _PROMPT_CONTROL_RE.sub(" ", value)
    cleaned = cleaned.replace("```", " ").replace("\\n", " ")
    collapsed = " ".join(cleaned.split())
    if len(collapsed) > _PROMPT_FIELD_MAX_LENGTH:
        collapsed = collapsed[:_PROMPT_FIELD_MAX_LENGTH].rstrip()
    return collapsed


def _visual_style_for_tone(tone: str) -> str:
    tone_lower = tone.lower()
    if "playful" in tone_lower:
        return "bright, energetic, and human"
    if "luxury" in tone_lower or "premium" in tone_lower:
        return "clean, elevated, and premium"
    if "bold" in tone_lower:
        return "high-contrast, assertive, and modern"
    return "clear, confident, and modern"


class PromptTemplateImageProvider(ImageProvider):
    provider_name = "prompt_template"

    def attach_image_prompts(self, brief: CampaignBrief, variants: list[AdVariant]) -> None:
        attach_image_prompts(brief, variants)


class OpenAIImagesProvider(ImageProvider):
    provider_name = "openai_images"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_IMAGE_MODEL",
                               DEFAULT_OPENAI_IMAGE_MODEL).strip() or DEFAULT_OPENAI_IMAGE_MODEL
        self.size = os.getenv("OPENAI_IMAGE_SIZE",
                              "1024x1024").strip() or "1024x1024"
        self.quality = os.getenv(
            "OPENAI_IMAGE_QUALITY", "medium").strip() or "medium"
        self.background = os.getenv(
            "OPENAI_IMAGE_BACKGROUND", "auto").strip() or "auto"
        self.output_format = os.getenv(
            "OPENAI_IMAGE_OUTPUT_FORMAT", "png").strip() or "png"
        self.timeout_seconds = int(
            os.getenv("OPENAI_IMAGE_TIMEOUT_SECONDS", "180").strip() or "180")
        self.generate_during_create = _env_flag(
            "OPENAI_IMAGE_GENERATE_DURING_CREATE")
        self.output_dir = get_generated_asset_root()

    def attach_image_prompts(self, brief: CampaignBrief, variants: list[AdVariant]) -> None:
        attach_image_prompts(brief, variants)
        if not self.generate_during_create:
            return

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when AD_ENGINE_IMAGE_PROVIDER=openai_images."
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)

        for index, variant in enumerate(variants, start=1):
            self.generate_variant_image(brief, variant, index=index)

    def generate_variant_image(
        self,
        brief: CampaignBrief,
        variant: AdVariant,
        *,
        index: int = 1,
    ) -> GeneratedAsset:
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when generating images with openai_images."
            )

        if not variant.image_prompt:
            attach_image_prompts(brief, [variant])

        self.output_dir.mkdir(parents=True, exist_ok=True)
        response_payload = self._generate_image(variant.image_prompt)
        image_record = response_payload["data"][0]
        image_base64 = image_record.get("b64_json")
        if not image_base64:
            raise ValueError(
                "OpenAI Images API did not return base64 image data.")

        filename = self._build_filename(brief, variant, index)
        file_path = self.output_dir / filename
        file_bytes = base64.b64decode(image_base64)
        file_path.write_bytes(file_bytes)

        logo_path = resolve_brand_logo_path(brief.brand_logo)
        if logo_path is not None:
            try:
                composite_brand_logo(file_path, logo_path)
            except (UnidentifiedImageError, OSError, ValueError):
                pass

        generated_asset = GeneratedAsset(
            path=f"/generated-assets/{filename}",
            mime_type=_mime_type_for_format(self.output_format),
            provider=self.provider_name,
            prompt=variant.image_prompt,
            revised_prompt=image_record.get("revised_prompt"),
        )
        variant.generated_asset = generated_asset
        variant.image_status = "generated"
        variant.image_error = None
        return generated_asset

    def _generate_image(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": self.size,
            "quality": self.quality,
            "background": self.background,
            "output_format": self.output_format,
        }
        body = json.dumps(payload).encode("utf-8")
        api_request = request.Request(
            "https://api.openai.com/v1/images/generations",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(api_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            message = _extract_openai_error_message(
                details) or f"HTTP {exc.code}"
            raise ValueError(
                f"OpenAI image generation failed: {message}") from exc
        except error.URLError as exc:
            raise ValueError(
                "OpenAI image generation failed: upstream request error.") from exc

    def _build_filename(self, brief: CampaignBrief, variant: AdVariant, index: int) -> str:
        brand = _slugify(brief.brand_name)
        product = _slugify(brief.product_name)
        channel = _slugify(variant.channel)
        unique_suffix = uuid4().hex[:12]
        extension = "jpg" if self.output_format == "jpeg" else self.output_format
        return f"{brand}-{product}-{channel}-{index}-{unique_suffix}.{extension}"


def get_generated_asset_root() -> Path:
    configured = os.getenv("OPENAI_IMAGE_OUTPUT_DIR",
                           DEFAULT_OUTPUT_DIR).strip() or DEFAULT_OUTPUT_DIR
    return Path(configured)


def get_brand_logo_root() -> Path:
    configured = os.getenv("BRAND_LOGO_DIR",
                           DEFAULT_BRAND_LOGO_DIR).strip() or DEFAULT_BRAND_LOGO_DIR
    return Path(configured)


def _mime_type_for_format(output_format: str) -> str:
    if output_format == "jpeg":
        return "image/jpeg"
    if output_format == "webp":
        return "image/webp"
    return "image/png"


def _extract_openai_error_message(response_text: str) -> str | None:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return None

    error_payload = payload.get("error")
    if isinstance(error_payload, dict):
        message = error_payload.get("message")
        if isinstance(message, str):
            return message
    return None


def _slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum()
                      else "-" for char in value)
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed or "asset"


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


class BrandLogoValidationError(ValueError):
    """Raised when an uploaded brand logo fails validation."""


def save_brand_logo(content: bytes, content_type: str | None) -> tuple[str, str]:
    """Persist an uploaded brand logo and return (public_path, mime_type)."""
    if not content:
        raise BrandLogoValidationError("Brand logo upload is empty.")
    if len(content) > BRAND_LOGO_MAX_BYTES:
        raise BrandLogoValidationError(
            "Brand logo must be 2 MB or smaller."
        )

    mime = (content_type or "").split(";")[0].strip().lower()
    if mime not in BRAND_LOGO_ALLOWED_MIME_TYPES:
        raise BrandLogoValidationError(
            "Brand logo must be a PNG, JPEG, or WEBP image."
        )
    extension = BRAND_LOGO_ALLOWED_MIME_TYPES[mime]

    try:
        with Image.open(io.BytesIO(content)) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise BrandLogoValidationError(
            "Brand logo could not be decoded as an image."
        ) from exc

    root = get_brand_logo_root()
    root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    (root / filename).write_bytes(content)
    return f"/brand-logos/{filename}", f"image/{extension if extension != 'jpg' else 'jpeg'}"


def resolve_brand_logo_path(public_path: str | None) -> Path | None:
    if not public_path:
        return None
    prefix = "/brand-logos/"
    if not public_path.startswith(prefix):
        return None
    filename = public_path[len(prefix):]
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return None
    root = get_brand_logo_root().resolve()
    candidate = (root / filename).resolve()
    if not candidate.is_relative_to(root):
        return None
    if not candidate.is_file():
        return None
    return candidate


def composite_brand_logo(
    image_path: Path,
    logo_path: Path,
    *,
    logo_fraction: float = 0.12,
    margin_fraction: float = 0.03,
) -> None:
    """Paste the logo onto the bottom-right of the image, preserving alpha."""
    with Image.open(image_path) as base_image:
        base = base_image.convert("RGBA")
    with Image.open(logo_path) as logo_image:
        logo = logo_image.convert("RGBA")

    base_long_edge = max(base.size)
    target_long_edge = max(1, int(base_long_edge * logo_fraction))
    logo_long_edge = max(logo.size)
    if logo_long_edge == 0:
        return
    scale = target_long_edge / logo_long_edge
    new_size = (max(1, int(logo.width * scale)),
                max(1, int(logo.height * scale)))
    logo_resized = logo.resize(new_size, Image.LANCZOS)

    margin = max(1, int(base_long_edge * margin_fraction))
    position = (
        base.width - logo_resized.width - margin,
        base.height - logo_resized.height - margin,
    )

    base.alpha_composite(logo_resized, dest=position)
    output_format = (Image.open(image_path).format or "PNG").upper()
    if output_format == "JPEG":
        base.convert("RGB").save(image_path, format="JPEG", quality=92)
    else:
        base.save(image_path, format=output_format)
