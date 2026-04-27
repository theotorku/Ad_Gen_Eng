from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from .models import AdBundle, CampaignBrief, CreativePlan, AdVariant, GeneratedAsset, QualitySummary


CAMPAIGN_STATUSES = {"draft", "approved"}


@dataclass(slots=True)
class StoreSettings:
    backend: str = "memory"
    sqlite_path: str = "data/ad_engine.db"

    @classmethod
    def from_env(cls) -> "StoreSettings":
        return cls(
            backend=os.getenv("AD_ENGINE_DB_BACKEND",
                              "memory").strip() or "memory",
            sqlite_path=os.getenv(
                "AD_ENGINE_SQLITE_PATH", "data/ad_engine.db").strip() or "data/ad_engine.db",
        )


@dataclass(slots=True)
class StoredCampaign:
    campaign_id: str
    created_at: str
    updated_at: str
    status: str
    bundle: AdBundle
    approval_notes: str | None = None
    approved_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.campaign_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "approval_notes": self.approval_notes,
            "approved_at": self.approved_at,
            "metadata": self.metadata,
            "bundle": self.bundle.to_dict(),
        }


class CampaignStore(Protocol):
    backend_name: str

    def create(self, bundle: AdBundle, metadata: dict[str, Any] | None = None) -> StoredCampaign:
        ...

    def get(self, campaign_id: str) -> StoredCampaign | None:
        ...

    def list(self) -> list[StoredCampaign]:
        ...

    def update(
        self,
        campaign_id: str,
        *,
        status: str | None = None,
        approval_notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredCampaign | None:
        ...

    def approve(self, campaign_id: str, approval_notes: str | None = None) -> StoredCampaign | None:
        ...


class InMemoryCampaignStore:
    backend_name = "memory"

    def __init__(self) -> None:
        self._items: dict[str, StoredCampaign] = {}
        self._lock = Lock()

    def create(self, bundle: AdBundle, metadata: dict[str, Any] | None = None) -> StoredCampaign:
        now = _utc_now()
        stored = StoredCampaign(
            campaign_id=str(uuid4()),
            created_at=now,
            updated_at=now,
            status="draft",
            bundle=bundle,
            metadata=metadata or {},
        )
        with self._lock:
            self._items[stored.campaign_id] = stored
        return stored

    def get(self, campaign_id: str) -> StoredCampaign | None:
        with self._lock:
            return self._items.get(campaign_id)

    def list(self) -> list[StoredCampaign]:
        with self._lock:
            return sorted(self._items.values(), key=lambda item: item.created_at, reverse=True)

    def update(
        self,
        campaign_id: str,
        *,
        status: str | None = None,
        approval_notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredCampaign | None:
        with self._lock:
            stored = self._items.get(campaign_id)
            if stored is None:
                return None

            _apply_campaign_updates(
                stored, status=status, approval_notes=approval_notes, metadata=metadata)
            return stored

    def approve(self, campaign_id: str, approval_notes: str | None = None) -> StoredCampaign | None:
        return self.update(campaign_id, status="approved", approval_notes=approval_notes)


class SQLiteCampaignStore:
    backend_name = "sqlite"

    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize_schema()

    def create(self, bundle: AdBundle, metadata: dict[str, Any] | None = None) -> StoredCampaign:
        now = _utc_now()
        stored = StoredCampaign(
            campaign_id=str(uuid4()),
            created_at=now,
            updated_at=now,
            status="draft",
            bundle=bundle,
            metadata=metadata or {},
        )

        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO campaigns (
                    id,
                    brand_name,
                    product_name,
                    objective,
                    status,
                    created_at,
                    updated_at,
                    approved_at,
                    approval_notes,
                    metadata_json,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.campaign_id,
                    stored.bundle.brief.brand_name,
                    stored.bundle.brief.product_name,
                    stored.bundle.brief.objective,
                    stored.status,
                    stored.created_at,
                    stored.updated_at,
                    stored.approved_at,
                    stored.approval_notes,
                    json.dumps(stored.metadata),
                    json.dumps(stored.to_dict()),
                ),
            )

        return stored

    def get(self, campaign_id: str) -> StoredCampaign | None:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM campaigns
                WHERE id = ?
                """,
                (campaign_id,),
            ).fetchone()

        if row is None:
            return None
        return _stored_campaign_from_payload(json.loads(row["payload_json"]))

    def list(self) -> list[StoredCampaign]:
        with self._lock, closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM campaigns
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [_stored_campaign_from_payload(json.loads(row["payload_json"])) for row in rows]

    def update(
        self,
        campaign_id: str,
        *,
        status: str | None = None,
        approval_notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredCampaign | None:
        with self._lock, closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM campaigns
                WHERE id = ?
                """,
                (campaign_id,),
            ).fetchone()

            if row is None:
                return None

            stored = _stored_campaign_from_payload(
                json.loads(row["payload_json"]))
            _apply_campaign_updates(
                stored, status=status, approval_notes=approval_notes, metadata=metadata)

            connection.execute(
                """
                UPDATE campaigns
                SET brand_name = ?,
                    product_name = ?,
                    objective = ?,
                    status = ?,
                    updated_at = ?,
                    approved_at = ?,
                    approval_notes = ?,
                    metadata_json = ?,
                    payload_json = ?
                WHERE id = ?
                """,
                (
                    stored.bundle.brief.brand_name,
                    stored.bundle.brief.product_name,
                    stored.bundle.brief.objective,
                    stored.status,
                    stored.updated_at,
                    stored.approved_at,
                    stored.approval_notes,
                    json.dumps(stored.metadata),
                    json.dumps(stored.to_dict()),
                    stored.campaign_id,
                ),
            )

        return stored

    def approve(self, campaign_id: str, approval_notes: str | None = None) -> StoredCampaign | None:
        return self.update(campaign_id, status="approved", approval_notes=approval_notes)

    def _initialize_schema(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS campaigns (
                        id TEXT PRIMARY KEY,
                        brand_name TEXT NOT NULL,
                        product_name TEXT NOT NULL,
                        objective TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        approved_at TEXT,
                        approval_notes TEXT,
                        metadata_json TEXT NOT NULL,
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_campaigns_created_at ON campaigns(created_at DESC)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status)"
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection


def build_campaign_store(settings: StoreSettings | None = None) -> CampaignStore:
    resolved = settings or StoreSettings.from_env()
    if resolved.backend == "memory":
        return InMemoryCampaignStore()
    if resolved.backend == "sqlite":
        return SQLiteCampaignStore(resolved.sqlite_path)

    raise ValueError(
        f"Unknown campaign store backend '{resolved.backend}'. Supported backends: memory, sqlite"
    )


def _apply_campaign_updates(
    stored: StoredCampaign,
    *,
    status: str | None,
    approval_notes: str | None,
    metadata: dict[str, Any] | None,
) -> None:
    if status is not None:
        if status not in CAMPAIGN_STATUSES:
            supported = ", ".join(sorted(CAMPAIGN_STATUSES))
            raise ValueError(
                f"Unsupported campaign status '{status}'. Supported statuses: {supported}")
        stored.status = status

    if approval_notes is not None:
        stored.approval_notes = approval_notes.strip() or None

    if metadata is not None:
        stored.metadata = metadata

    stored.updated_at = _utc_now()
    if stored.status == "approved" and stored.approved_at is None:
        stored.approved_at = stored.updated_at
    if stored.status != "approved":
        stored.approved_at = None


def _stored_campaign_from_payload(payload: dict[str, Any]) -> StoredCampaign:
    bundle_payload = payload["bundle"]
    brief_payload = bundle_payload["brief"]
    plan_payload = bundle_payload["creative_plan"]
    quality_payload = bundle_payload["quality_summary"]

    bundle = AdBundle(
        brief=CampaignBrief.from_dict(brief_payload),
        creative_plan=CreativePlan(
            strategy_summary=plan_payload["strategy_summary"],
            audience_promise=plan_payload["audience_promise"],
            hooks=list(plan_payload["hooks"]),
            messaging_pillars=list(plan_payload["messaging_pillars"]),
            channel_notes=dict(plan_payload["channel_notes"]),
        ),
        variants=[
            AdVariant(
                channel=variant["channel"],
                angle=variant["angle"],
                headline=variant["headline"],
                primary_text=variant["primary_text"],
                cta=variant["cta"],
                image_prompt=variant["image_prompt"],
                generated_asset=_generated_asset_from_payload(
                    variant.get("generated_asset")),
                review_notes=list(variant.get("review_notes", [])),
            )
            for variant in bundle_payload["variants"]
        ],
        quality_summary=QualitySummary(
            strengths=list(quality_payload["strengths"]),
            risks=list(quality_payload["risks"]),
        ),
    )

    return StoredCampaign(
        campaign_id=payload["id"],
        created_at=payload["created_at"],
        updated_at=payload["updated_at"],
        status=payload["status"],
        approval_notes=payload.get("approval_notes"),
        approved_at=payload.get("approved_at"),
        metadata=dict(payload.get("metadata", {})),
        bundle=bundle,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generated_asset_from_payload(payload: dict[str, Any] | None) -> GeneratedAsset | None:
    if not payload:
        return None

    return GeneratedAsset(
        path=payload["path"],
        mime_type=payload["mime_type"],
        provider=payload["provider"],
        prompt=payload["prompt"],
        revised_prompt=payload.get("revised_prompt"),
    )
