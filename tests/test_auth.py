from __future__ import annotations

import pytest

import ad_engine.auth as auth_module
from ad_engine.auth import AuthSettings, AuthenticationError, resolve_auth_context


def test_optional_auth_uses_requested_organization():
    context = resolve_auth_context(
        settings=AuthSettings(require_api_key=False, api_keys={}),
        api_key=None,
        requested_organization_id="alpha",
    )

    assert context.organization_id == "alpha"
    assert context.authenticated is False


def test_required_auth_maps_api_key_to_organization():
    context = resolve_auth_context(
        settings=AuthSettings(require_api_key=True, api_keys={"secret": "alpha"}),
        api_key="secret",
        requested_organization_id=None,
    )

    assert context.organization_id == "alpha"
    assert context.authenticated is True


def test_required_auth_rejects_wrong_organization():
    with pytest.raises(AuthenticationError, match="not authorized"):
        resolve_auth_context(
            settings=AuthSettings(require_api_key=True, api_keys={"secret": "alpha"}),
            api_key="secret",
            requested_organization_id="beta",
        )


def test_required_clerk_auth_accepts_bearer_token(monkeypatch):
    monkeypatch.setattr(
        auth_module,
        "_decode_clerk_token",
        lambda settings, token: {"sub": "user_123", "org_id": "alpha"},
    )

    context = resolve_auth_context(
        settings=AuthSettings(
            require_clerk_auth=True,
            clerk_issuer="https://accounts.example.com",
        ),
        api_key=None,
        authorization="Bearer token",
        requested_organization_id="alpha",
    )

    assert context.organization_id == "alpha"
    assert context.principal_id == "user_123"
    assert context.authenticated is True


def test_required_clerk_auth_rejects_missing_credentials():
    with pytest.raises(AuthenticationError, match="Missing authentication"):
        resolve_auth_context(
            settings=AuthSettings(
                require_clerk_auth=True,
                clerk_issuer="https://accounts.example.com",
            ),
            api_key=None,
            authorization=None,
            requested_organization_id="alpha",
        )


def test_clerk_auth_rejects_wrong_organization(monkeypatch):
    monkeypatch.setattr(
        auth_module,
        "_decode_clerk_token",
        lambda settings, token: {"sub": "user_123", "org_id": "alpha"},
    )

    with pytest.raises(AuthenticationError, match="not authorized"):
        resolve_auth_context(
            settings=AuthSettings(
                require_clerk_auth=True,
                clerk_issuer="https://accounts.example.com",
            ),
            api_key=None,
            authorization="Bearer token",
            requested_organization_id="beta",
        )
