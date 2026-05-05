from __future__ import annotations

import pytest

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
