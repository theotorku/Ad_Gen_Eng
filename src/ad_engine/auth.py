from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import jwt

from .config import DEFAULT_ORGANIZATION_ID


@dataclass(frozen=True, slots=True)
class AuthSettings:
    require_api_key: bool = False
    api_keys: dict[str, str] | None = None
    require_clerk_auth: bool = False
    clerk_issuer: str = ""
    clerk_jwks_url: str = ""
    clerk_audience: str = ""

    @classmethod
    def from_env(cls) -> "AuthSettings":
        return cls(
            require_api_key=_env_flag("AD_ENGINE_REQUIRE_API_KEY"),
            api_keys=_parse_api_keys(os.getenv("AD_ENGINE_API_KEYS", "")),
            require_clerk_auth=_env_flag("AD_ENGINE_REQUIRE_CLERK_AUTH"),
            clerk_issuer=os.getenv("CLERK_ISSUER", "").strip(),
            clerk_jwks_url=os.getenv("CLERK_JWKS_URL", "").strip(),
            clerk_audience=os.getenv("CLERK_JWT_AUDIENCE", "").strip(),
        )


@dataclass(frozen=True, slots=True)
class AuthContext:
    organization_id: str
    authenticated: bool
    principal_id: str | None = None


class AuthenticationError(Exception):
    pass


def resolve_auth_context(
    *,
    settings: AuthSettings,
    api_key: str | None,
    authorization: str | None = None,
    requested_organization_id: str | None,
) -> AuthContext:
    organization_id = _normalize_organization_id(requested_organization_id)
    if api_key:
        return _resolve_api_key_context(
            settings=settings,
            api_key=api_key,
            requested_organization_id=requested_organization_id,
        )

    bearer_token = _extract_bearer_token(authorization)
    if bearer_token:
        return _resolve_clerk_context(
            settings=settings,
            token=bearer_token,
            requested_organization_id=requested_organization_id,
        )

    if not settings.require_api_key and not settings.require_clerk_auth:
        return AuthContext(organization_id=organization_id, authenticated=False)

    raise AuthenticationError("Missing authentication credentials.")


def _resolve_api_key_context(
    *,
    settings: AuthSettings,
    api_key: str,
    requested_organization_id: str | None,
) -> AuthContext:
    if not settings.require_api_key and not settings.api_keys:
        raise AuthenticationError("API key authentication is not configured.")

    mapped_organization_id = (settings.api_keys or {}).get(api_key)
    if mapped_organization_id is None:
        raise AuthenticationError("Invalid API key.")

    organization_id = _normalize_organization_id(requested_organization_id)
    if requested_organization_id and organization_id != mapped_organization_id:
        raise AuthenticationError("API key is not authorized for this organization.")

    return AuthContext(organization_id=mapped_organization_id, authenticated=True)


def _resolve_clerk_context(
    *,
    settings: AuthSettings,
    token: str,
    requested_organization_id: str | None,
) -> AuthContext:
    if not settings.clerk_issuer and not settings.clerk_jwks_url:
        raise AuthenticationError("Clerk authentication is not configured.")

    claims = _decode_clerk_token(settings, token)
    principal_id = _claim_as_string(claims, "sub")
    if not principal_id:
        raise AuthenticationError("Clerk token is missing a subject.")

    claim_organization_id = _claim_as_string(claims, "org_id")
    requested = _normalize_organization_id(requested_organization_id)
    if requested_organization_id and claim_organization_id and requested != claim_organization_id:
        raise AuthenticationError("Clerk token is not authorized for this organization.")

    organization_id = claim_organization_id or requested or principal_id
    return AuthContext(
        organization_id=_normalize_organization_id(organization_id),
        authenticated=True,
        principal_id=principal_id,
    )


def _decode_clerk_token(settings: AuthSettings, token: str) -> dict:
    jwks_url = settings.clerk_jwks_url or _jwks_url_from_issuer(settings.clerk_issuer)
    try:
        signing_key = _jwk_client(jwks_url).get_signing_key_from_jwt(token)
        options = {"verify_aud": bool(settings.clerk_audience)}
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.clerk_audience or None,
            issuer=settings.clerk_issuer or None,
            options=options,
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid Clerk token.") from exc
    if not isinstance(decoded, dict):
        raise AuthenticationError("Invalid Clerk token.")
    return decoded


def _jwks_url_from_issuer(issuer: str) -> str:
    cleaned = issuer.rstrip("/")
    if not cleaned:
        raise AuthenticationError("Clerk JWKS URL is not configured.")
    return f"{cleaned}/.well-known/jwks.json"


@lru_cache(maxsize=8)
def _jwk_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _claim_as_string(claims: dict, name: str) -> str | None:
    value = claims.get(name)
    return value if isinstance(value, str) and value.strip() else None


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
