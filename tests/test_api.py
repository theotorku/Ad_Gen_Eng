from __future__ import annotations

import http.client
import json
import threading
from typing import Any

import pytest

from ad_engine.api import MAX_REQUEST_BODY_BYTES, AdApiServer


@pytest.fixture
def api_server(monkeypatch):
    monkeypatch.setenv("AD_ENGINE_DB_BACKEND", "memory")

    server = AdApiServer(("127.0.0.1", 0))
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield host, port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(
    api_server: tuple[str, int],
    method: str,
    path: str,
    body: str | bytes | None = None,
) -> tuple[int, str]:
    host, port = api_server
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        body_bytes = body.encode("utf-8") if isinstance(body, str) else body
        conn.request(
            method,
            path,
            body=body_bytes,
            headers={"Content-Type": "application/json"} if body_bytes else {},
        )
        response = conn.getresponse()
        return response.status, response.read().decode("utf-8")
    finally:
        conn.close()


def _create_campaign(api_server, brief_payload) -> dict[str, Any]:
    status, body = _request(
        api_server, "POST", "/bundles", body=json.dumps(brief_payload)
    )
    assert status == 201, body
    return json.loads(body)


def test_health_returns_ok(api_server):
    status, body = _request(api_server, "GET", "/health")

    assert status == 200
    assert json.loads(body)["status"] == "ok"


def test_unknown_route_returns_404(api_server):
    status, _ = _request(api_server, "GET", "/does-not-exist")

    assert status == 404


def test_bundle_route_rejects_extra_segments(api_server):
    status, _ = _request(api_server, "GET", "/bundles/abc/extra")

    assert status == 404


def test_campaign_route_rejects_extra_segments(api_server):
    status, _ = _request(api_server, "GET", "/campaigns/abc/extra")

    assert status == 404


def test_post_invalid_json_returns_400(api_server):
    status, body = _request(api_server, "POST", "/bundles", body="not json")

    assert status == 400
    assert "valid JSON" in json.loads(body)["error"]


def test_post_oversized_content_length_returns_413(api_server):
    host, port = api_server
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.putrequest("POST", "/bundles", skip_host=False,
                        skip_accept_encoding=True)
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", str(MAX_REQUEST_BODY_BYTES + 1))
        conn.endheaders()
        response = conn.getresponse()
        status = response.status
        body = response.read().decode("utf-8")
    finally:
        conn.close()

    assert status == 413
    assert "exceeds maximum size" in json.loads(body)["error"]


def test_post_creates_campaign_and_lists_it(api_server, brief_payload):
    created = _create_campaign(api_server, brief_payload)

    status, body = _request(api_server, "GET", "/campaigns")

    assert status == 200
    listed = json.loads(body)
    assert any(c["id"] == created["id"] for c in listed["campaigns"])


def test_patch_null_field_does_not_clear(api_server, brief_payload):
    created = _create_campaign(api_server, brief_payload)
    cid = created["id"]
    _request(
        api_server,
        "POST",
        f"/campaigns/{cid}/approve",
        body=json.dumps({"approval_notes": "looks good"}),
    )

    status, _ = _request(
        api_server,
        "PATCH",
        f"/campaigns/{cid}",
        body=json.dumps({"approval_notes": None}),
    )

    assert status == 200
    _, fetched = _request(api_server, "GET", f"/campaigns/{cid}")
    assert json.loads(fetched)["approval_notes"] == "looks good"


def test_patch_empty_string_clears_field(api_server, brief_payload):
    created = _create_campaign(api_server, brief_payload)
    cid = created["id"]
    _request(
        api_server,
        "POST",
        f"/campaigns/{cid}/approve",
        body=json.dumps({"approval_notes": "looks good"}),
    )

    status, _ = _request(
        api_server,
        "PATCH",
        f"/campaigns/{cid}",
        body=json.dumps({"approval_notes": ""}),
    )

    assert status == 200
    _, fetched = _request(api_server, "GET", f"/campaigns/{cid}")
    assert json.loads(fetched)["approval_notes"] is None


def test_approve_route_rejects_extra_segments(api_server, brief_payload):
    created = _create_campaign(api_server, brief_payload)
    cid = created["id"]

    status, _ = _request(
        api_server, "POST", f"/campaigns/{cid}/extra/approve", body="{}"
    )

    assert status == 404
