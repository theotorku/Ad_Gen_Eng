from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_ORGANIZATION_ID = "default"


@dataclass(frozen=True, slots=True)
class AuthSettings:
    require_api_key: bool = False
    api_keys: dict[str, str] | None = None

    @classmethod
    def from_env(cls) -> "AuthSettings":
        return cls(
            require_api_key=_env_flag("AD_ENGINE_REQUIRE_API_KEY"),
            api_keys=_parse_api_keys(os.getenv("AD_ENGINE_API_KEYS", "")),
        )


@dataclass(frozen=True, slots=True)
class AuthContext:
    organization_id: str
    authenticated: bool


class AuthenticationError(Exception):
    pass


def resolve_auth_context(
    *,
    settings: AuthSettings,
    api_key: str | None,
    requested_organization_id: str | None,
) -> AuthContext:
    organization_id = _normalize_organization_id(requested_organization_id)
    if not settings.require_api_key:
        return AuthContext(organization_id=organization_id, authenticated=False)

    if not api_key:
        raise AuthenticationError("Missing API key.")

    mapped_organization_id = (settings.api_keys or {}).get(api_key)
    if mapped_organization_id is None:
        raise AuthenticationError("Invalid API key.")

    if requested_organization_id and organization_id != mapped_organization_id:
        raise AuthenticationError("API key is not authorized for this organization.")

    return AuthContext(organization_id=mapped_organization_id, authenticated=True)


def _parse_api_keys(raw: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in raw.split(","):
        item = entry.strip()
        if not item:
            continue
        if ":" not in item:
            continue
        key, organization_id = item.split(":", 1)
        clean_key = key.strip()
        if clean_key:
            mapping[clean_key] = _normalize_organization_id(organization_id)
    return mapping


def _normalize_organization_id(value: str | None) -> str:
    normalized = (value or DEFAULT_ORGANIZATION_ID).strip()
    return normalized or DEFAULT_ORGANIZATION_ID


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
