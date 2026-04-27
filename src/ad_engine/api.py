from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .assets import get_generated_asset_root
from .engine import AdGenerationEngine
from .providers import build_provider_stack
from .store import StoreSettings, build_campaign_store


MAX_REQUEST_BODY_BYTES = 1 * 1024 * 1024  # 1 MiB

DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def _load_cors_origins() -> tuple[frozenset[str], bool]:
    raw = os.getenv("AD_ENGINE_CORS_ORIGINS")
    if raw is None:
        return frozenset(DEFAULT_CORS_ORIGINS), False
    entries = [item.strip() for item in raw.split(",") if item.strip()]
    if "*" in entries:
        return frozenset(), True
    return frozenset(entries), False


class RequestBodyTooLargeError(Exception):
    pass


class AdApiServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, AdApiHandler)
        self.engine = AdGenerationEngine(build_provider_stack())
        self.store = build_campaign_store(StoreSettings.from_env())
        self.cors_origins, self.cors_allow_any = _load_cors_origins()


class AdApiHandler(BaseHTTPRequestHandler):
    server: AdApiServer

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self._send_common_headers(content_length=0)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parts = self._path_parts()

        if parts == ["health"]:
            self._write_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "providers": self.server.engine.providers.describe(),
                    "db_backend": self.server.store.backend_name,
                },
            )
            return

        if parts == ["bundles"]:
            self._write_json(
                HTTPStatus.OK,
                {
                    "message": "Submit a POST request to /bundles to generate a new ad bundle.",
                },
            )
            return

        if len(parts) >= 2 and parts[0] == "generated-assets":
            self._serve_generated_asset("/".join(parts[1:]))
            return

        if len(parts) == 2 and parts[0] == "bundles":
            campaign_id = parts[1]
            stored = self.server.store.get(campaign_id)
            if stored is None:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": f"Bundle '{campaign_id}' was not found."},
                )
                return

            self._write_json(HTTPStatus.OK, stored.bundle.to_dict())
            return

        if parts == ["campaigns"]:
            campaigns = [campaign.to_dict()
                         for campaign in self.server.store.list()]
            self._write_json(
                HTTPStatus.OK, {"campaigns": campaigns, "count": len(campaigns)})
            return

        if len(parts) == 2 and parts[0] == "campaigns":
            campaign_id = parts[1]
            stored = self.server.store.get(campaign_id)
            if stored is None:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": f"Campaign '{campaign_id}' was not found."},
                )
                return

            self._write_json(HTTPStatus.OK, stored.to_dict())
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})

    def do_POST(self) -> None:  # noqa: N802
        parts = self._path_parts()

        if len(parts) == 3 and parts[0] == "campaigns" and parts[2] == "approve":
            self._approve_campaign(parts[1])
            return

        if parts != ["bundles"]:
            self._write_json(HTTPStatus.NOT_FOUND, {
                             "error": "Route not found."})
            return

        try:
            payload = self._read_json_body()
            bundle = self.server.engine.run(payload)
            metadata = self._campaign_metadata_from_brief(payload)
            stored = self.server.store.create(bundle, metadata=metadata)
        except RequestBodyTooLargeError as exc:
            self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {
                             "error": str(exc)})
            return
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {
                             "error": "Request body must be valid JSON."})
            return
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self._write_json(HTTPStatus.CREATED, stored.to_dict())

    def do_PATCH(self) -> None:  # noqa: N802
        parts = self._path_parts()

        if len(parts) != 2 or parts[0] != "campaigns":
            self._write_json(HTTPStatus.NOT_FOUND, {
                             "error": "Route not found."})
            return

        campaign_id = parts[1]
        try:
            payload = self._read_json_body()
            stored = self.server.store.update(
                campaign_id,
                status=self._optional_string(payload, "status"),
                approval_notes=self._optional_string(
                    payload, "approval_notes"),
                metadata=self._optional_object(payload, "metadata"),
            )
        except RequestBodyTooLargeError as exc:
            self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {
                             "error": str(exc)})
            return
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {
                             "error": "Request body must be valid JSON."})
            return
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if stored is None:
            self._write_json(
                HTTPStatus.NOT_FOUND,
                {"error": f"Campaign '{campaign_id}' was not found."},
            )
            return

        self._write_json(HTTPStatus.OK, stored.to_dict())

    def _path_parts(self) -> list[str]:
        parsed = urlparse(self.path)
        return [segment for segment in parsed.path.split("/") if segment]

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json_body(self) -> dict[str, Any]:
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raise ValueError("Request body is required.")

        try:
            length = int(length_header)
        except ValueError as exc:
            raise ValueError("Invalid Content-Length header.") from exc

        if length < 0:
            raise ValueError("Invalid Content-Length header.")
        if length > MAX_REQUEST_BODY_BYTES:
            raise RequestBodyTooLargeError(
                f"Request body exceeds maximum size of {MAX_REQUEST_BODY_BYTES} bytes."
            )

        raw_body = self.rfile.read(length)
        if not raw_body:
            raise ValueError("Request body is required.")

        payload = json.loads(raw_body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        return payload

    def _approve_campaign(self, campaign_id: str) -> None:
        try:
            payload = self._read_optional_json_body()
            stored = self.server.store.approve(
                campaign_id,
                approval_notes=self._optional_string(
                    payload, "approval_notes"),
            )
        except RequestBodyTooLargeError as exc:
            self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {
                             "error": str(exc)})
            return
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {
                             "error": "Request body must be valid JSON."})
            return
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if stored is None:
            self._write_json(
                HTTPStatus.NOT_FOUND,
                {"error": f"Campaign '{campaign_id}' was not found."},
            )
            return

        self._write_json(HTTPStatus.OK, stored.to_dict())

    def _read_optional_json_body(self) -> dict[str, Any]:
        length_header = self.headers.get("Content-Length")
        if length_header is None or length_header == "0":
            return {}
        return self._read_json_body()

    def _serve_generated_asset(self, filename: str) -> None:
        asset_root = get_generated_asset_root().resolve()
        asset_path = (asset_root / filename.strip()).resolve()

        if asset_root not in asset_path.parents and asset_path != asset_root:
            self._write_json(HTTPStatus.BAD_REQUEST, {
                             "error": "Invalid asset path."})
            return
        if not asset_path.exists() or not asset_path.is_file():
            self._write_json(HTTPStatus.NOT_FOUND, {
                             "error": "Generated asset not found."})
            return

        mime_type = mimetypes.guess_type(asset_path.name)[
            0] or "application/octet-stream"
        payload = asset_path.read_bytes()
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _campaign_metadata_from_brief(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "brand_name": str(payload.get("brand_name", "")).strip(),
            "product_name": str(payload.get("product_name", "")).strip(),
            "objective": str(payload.get("objective", "")).strip(),
            "channels": payload.get("channels", []),
        }

    def _optional_string(self, payload: dict[str, Any], field: str) -> str | None:
        # Returns None when the field is omitted or explicitly null (no change
        # downstream). An empty or whitespace string is treated as an explicit
        # clear and surfaced as "" so the store can reset the value.
        if field not in payload:
            return None
        value = payload[field]
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"Field '{field}' must be a string.")
        return value

    def _optional_object(self, payload: dict[str, Any], field: str) -> dict[str, Any] | None:
        if field not in payload:
            return None
        value = payload[field]
        if not isinstance(value, dict):
            raise ValueError(f"Field '{field}' must be an object.")
        return value

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        response = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status.value)
        self._send_common_headers(content_length=len(response))
        self.end_headers()
        self.wfile.write(response)

    def _send_common_headers(self, content_length: int) -> None:
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(content_length))
        self._send_cors_headers()
        self.send_header("Access-Control-Allow-Methods",
                         "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_cors_headers(self) -> None:
        # Always advertise that responses vary by Origin so caches don't serve
        # the wrong allow-origin to a different caller.
        self.send_header("Vary", "Origin")
        origin = self.headers.get("Origin")
        if origin is None:
            return
        if self.server.cors_allow_any:
            self.send_header("Access-Control-Allow-Origin", "*")
            return
        if origin in self.server.cors_origins:
            self.send_header("Access-Control-Allow-Origin", origin)


def run_api_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = AdApiServer((host, port))
    print(f"Ad API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
