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

from .models import (
    AdBundle,
    AdVariant,
    CampaignBrief,
    CreativePlan,
    GeneratedAsset,
    GenerationJob,
    LandingSection,
    QualitySummary,
)


CAMPAIGN_STATUSES = {"draft", "approved"}


@dataclass(slots=True)
class StoreSettings:
    backend: str = "memory"
    sqlite_path: str = "data/ad_engine.db"
    postgres_dsn: str = ""

    @classmethod
    def from_env(cls) -> "StoreSettings":
        return cls(
            backend=os.getenv("AD_ENGINE_DB_BACKEND",
                              "memory").strip() or "memory",
            sqlite_path=os.getenv(
                "AD_ENGINE_SQLITE_PATH", "data/ad_engine.db").strip() or "data/ad_engine.db",
            postgres_dsn=os.getenv("AD_ENGINE_POSTGRES_DSN", "").strip(),
        )


@dataclass(slots=True)
class StoredCampaign:
    campaign_id: str
    organization_id: str
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
            "organization_id": self.organization_id,
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

    def create(
        self,
        bundle: AdBundle,
        metadata: dict[str, Any] | None = None,
        organization_id: str = "default",
    ) -> StoredCampaign:
        ...

    def get(self, campaign_id: str, organization_id: str | None = None) -> StoredCampaign | None:
        ...

    def list(self, organization_id: str | None = None) -> list[StoredCampaign]:
        ...

    def update(
        self,
        campaign_id: str,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        approval_notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredCampaign | None:
        ...

    def approve(
        self,
        campaign_id: str,
        approval_notes: str | None = None,
        organization_id: str | None = None,
    ) -> StoredCampaign | None:
        ...

    def update_variant(
        self,
        campaign_id: str,
        variant_index: int,
        *,
        organization_id: str | None = None,
        headline: str | None = None,
        primary_text: str | None = None,
        cta: str | None = None,
        image_prompt: str | None = None,
    ) -> StoredCampaign | None:
        ...

    def update_variant_image(
        self,
        campaign_id: str,
        variant_index: int,
        *,
        organization_id: str | None = None,
        image_status: str,
        generated_asset: GeneratedAsset | None = None,
        image_error: str | None = None,
    ) -> StoredCampaign | None:
        ...

    def get_usage(self, organization_id: str, period: str, metric: str) -> int:
        ...

    def increment_usage(
        self, organization_id: str, period: str, metric: str, amount: int = 1
    ) -> int:
        ...


class InMemoryCampaignStore:
    backend_name = "memory"

    def __init__(self) -> None:
        self._items: dict[str, StoredCampaign] = {}
        self._usage: dict[tuple[str, str, str], int] = {}
        self._lock = Lock()

    def create(
        self,
        bundle: AdBundle,
        metadata: dict[str, Any] | None = None,
        organization_id: str = "default",
    ) -> StoredCampaign:
        now = _utc_now()
        stored = StoredCampaign(
            campaign_id=str(uuid4()),
            organization_id=_normalize_organization_id(organization_id),
            created_at=now,
            updated_at=now,
            status="draft",
            bundle=bundle,
            metadata=metadata or {},
        )
        with self._lock:
            self._items[stored.campaign_id] = stored
        return stored

    def get(self, campaign_id: str, organization_id: str | None = None) -> StoredCampaign | None:
        with self._lock:
            stored = self._items.get(campaign_id)
        if stored is None or not _matches_organization(stored, organization_id):
            return None
        return stored

    def list(self, organization_id: str | None = None) -> list[StoredCampaign]:
        with self._lock:
            items = [
                item
                for item in self._items.values()
                if _matches_organization(item, organization_id)
            ]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def update(
        self,
        campaign_id: str,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        approval_notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredCampaign | None:
        with self._lock:
            stored = self._items.get(campaign_id)
            if stored is None or not _matches_organization(stored, organization_id):
                return None

            _apply_campaign_updates(
                stored, status=status, approval_notes=approval_notes, metadata=metadata)
            return stored

    def approve(
        self,
        campaign_id: str,
        approval_notes: str | None = None,
        organization_id: str | None = None,
    ) -> StoredCampaign | None:
        return self.update(
            campaign_id,
            organization_id=organization_id,
            status="approved",
            approval_notes=approval_notes,
        )

    def update_variant(
        self,
        campaign_id: str,
        variant_index: int,
        *,
        organization_id: str | None = None,
        headline: str | None = None,
        primary_text: str | None = None,
        cta: str | None = None,
        image_prompt: str | None = None,
    ) -> StoredCampaign | None:
        with self._lock:
            stored = self._items.get(campaign_id)
            if stored is None or not _matches_organization(stored, organization_id):
                return None

            _apply_variant_updates(
                stored,
                variant_index,
                headline=headline,
                primary_text=primary_text,
                cta=cta,
                image_prompt=image_prompt,
            )
            return stored

    def update_variant_image(
        self,
        campaign_id: str,
        variant_index: int,
        *,
        organization_id: str | None = None,
        image_status: str,
        generated_asset: GeneratedAsset | None = None,
        image_error: str | None = None,
    ) -> StoredCampaign | None:
        with self._lock:
            stored = self._items.get(campaign_id)
            if stored is None or not _matches_organization(stored, organization_id):
                return None

            _apply_variant_image_updates(
                stored,
                variant_index,
                image_status=image_status,
                generated_asset=generated_asset,
                image_error=image_error,
            )
            return stored

    def get_usage(self, organization_id: str, period: str, metric: str) -> int:
        key = (_normalize_organization_id(organization_id), period, metric)
        with self._lock:
            return self._usage.get(key, 0)

    def increment_usage(
        self, organization_id: str, period: str, metric: str, amount: int = 1
    ) -> int:
        key = (_normalize_organization_id(organization_id), period, metric)
        with self._lock:
            self._usage[key] = self._usage.get(key, 0) + amount
            return self._usage[key]


class SQLiteCampaignStore:
    backend_name = "sqlite"

    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize_schema()

    def create(
        self,
        bundle: AdBundle,
        metadata: dict[str, Any] | None = None,
        organization_id: str = "default",
    ) -> StoredCampaign:
        now = _utc_now()
        stored = StoredCampaign(
            campaign_id=str(uuid4()),
            organization_id=_normalize_organization_id(organization_id),
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
                    organization_id,
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.campaign_id,
                    stored.organization_id,
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

    def get(self, campaign_id: str, organization_id: str | None = None) -> StoredCampaign | None:
        with self._lock, closing(self._connect()) as connection:
            if organization_id is None:
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE id = ?
                    """,
                    (campaign_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE id = ? AND organization_id = ?
                    """,
                    (campaign_id, _normalize_organization_id(organization_id)),
                ).fetchone()

        if row is None:
            return None
        return _stored_campaign_from_payload(json.loads(row["payload_json"]))

    def list(self, organization_id: str | None = None) -> list[StoredCampaign]:
        with self._lock, closing(self._connect()) as connection:
            if organization_id is None:
                rows = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    ORDER BY created_at DESC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE organization_id = ?
                    ORDER BY created_at DESC
                    """,
                    (_normalize_organization_id(organization_id),),
                ).fetchall()

        return [_stored_campaign_from_payload(json.loads(row["payload_json"])) for row in rows]

    def update(
        self,
        campaign_id: str,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        approval_notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredCampaign | None:
        with self._lock, closing(self._connect()) as connection, connection:
            if organization_id is None:
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE id = ?
                    """,
                    (campaign_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE id = ? AND organization_id = ?
                    """,
                    (campaign_id, _normalize_organization_id(organization_id)),
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
                SET organization_id = ?,
                    brand_name = ?,
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
                    stored.organization_id,
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

    def approve(
        self,
        campaign_id: str,
        approval_notes: str | None = None,
        organization_id: str | None = None,
    ) -> StoredCampaign | None:
        return self.update(
            campaign_id,
            organization_id=organization_id,
            status="approved",
            approval_notes=approval_notes,
        )

    def update_variant(
        self,
        campaign_id: str,
        variant_index: int,
        *,
        organization_id: str | None = None,
        headline: str | None = None,
        primary_text: str | None = None,
        cta: str | None = None,
        image_prompt: str | None = None,
    ) -> StoredCampaign | None:
        with self._lock, closing(self._connect()) as connection, connection:
            if organization_id is None:
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE id = ?
                    """,
                    (campaign_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE id = ? AND organization_id = ?
                    """,
                    (campaign_id, _normalize_organization_id(organization_id)),
                ).fetchone()

            if row is None:
                return None

            stored = _stored_campaign_from_payload(json.loads(row["payload_json"]))
            _apply_variant_updates(
                stored,
                variant_index,
                headline=headline,
                primary_text=primary_text,
                cta=cta,
                image_prompt=image_prompt,
            )

            connection.execute(
                """
                UPDATE campaigns
                SET updated_at = ?,
                    payload_json = ?
                WHERE id = ?
                """,
                (
                    stored.updated_at,
                    json.dumps(stored.to_dict()),
                    stored.campaign_id,
                ),
            )

        return stored

    def update_variant_image(
        self,
        campaign_id: str,
        variant_index: int,
        *,
        organization_id: str | None = None,
        image_status: str,
        generated_asset: GeneratedAsset | None = None,
        image_error: str | None = None,
    ) -> StoredCampaign | None:
        with self._lock, closing(self._connect()) as connection, connection:
            stored = self._load_for_update(connection, campaign_id, organization_id)
            if stored is None:
                return None

            _apply_variant_image_updates(
                stored,
                variant_index,
                image_status=image_status,
                generated_asset=generated_asset,
                image_error=image_error,
            )
            self._persist_payload(connection, stored)

        return stored

    def _initialize_schema(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS campaigns (
                        id TEXT PRIMARY KEY,
                        organization_id TEXT NOT NULL DEFAULT 'default',
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
                existing_columns = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_info(campaigns)").fetchall()
                }
                if "organization_id" not in existing_columns:
                    connection.execute(
                        "ALTER TABLE campaigns ADD COLUMN organization_id TEXT NOT NULL DEFAULT 'default'"
                    )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_campaigns_created_at ON campaigns(created_at DESC)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_campaigns_org_created_at ON campaigns(organization_id, created_at DESC)"
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS usage_counters (
                        organization_id TEXT NOT NULL,
                        period TEXT NOT NULL,
                        metric TEXT NOT NULL,
                        count INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (organization_id, period, metric)
                    )
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _load_for_update(
        self,
        connection: sqlite3.Connection,
        campaign_id: str,
        organization_id: str | None,
    ) -> StoredCampaign | None:
        if organization_id is None:
            row = connection.execute(
                """
                SELECT payload_json
                FROM campaigns
                WHERE id = ?
                """,
                (campaign_id,),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT payload_json
                FROM campaigns
                WHERE id = ? AND organization_id = ?
                """,
                (campaign_id, _normalize_organization_id(organization_id)),
            ).fetchone()

        if row is None:
            return None
        return _stored_campaign_from_payload(json.loads(row["payload_json"]))

    def _persist_payload(self, connection: sqlite3.Connection, stored: StoredCampaign) -> None:
        connection.execute(
            """
            UPDATE campaigns
            SET updated_at = ?,
                payload_json = ?
            WHERE id = ?
            """,
            (
                stored.updated_at,
                json.dumps(stored.to_dict()),
                stored.campaign_id,
            ),
        )

    def get_usage(self, organization_id: str, period: str, metric: str) -> int:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT count FROM usage_counters
                WHERE organization_id = ? AND period = ? AND metric = ?
                """,
                (_normalize_organization_id(organization_id), period, metric),
            ).fetchone()
        return int(row["count"]) if row is not None else 0

    def increment_usage(
        self, organization_id: str, period: str, metric: str, amount: int = 1
    ) -> int:
        org = _normalize_organization_id(organization_id)
        with self._lock, closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO usage_counters (organization_id, period, metric, count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(organization_id, period, metric)
                DO UPDATE SET count = count + excluded.count
                """,
                (org, period, metric, amount),
            )
            row = connection.execute(
                """
                SELECT count FROM usage_counters
                WHERE organization_id = ? AND period = ? AND metric = ?
                """,
                (org, period, metric),
            ).fetchone()
        return int(row["count"])


class PostgreSQLCampaignStore:
    backend_name = "postgres"

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("AD_ENGINE_POSTGRES_DSN is required when AD_ENGINE_DB_BACKEND=postgres.")
        try:
            import psycopg
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "Postgres storage requires the optional 'psycopg[binary]' and 'psycopg_pool' dependencies."
            ) from exc

        self.dsn = dsn
        self._psycopg = psycopg
        self._row_factory = dict_row
        self._pool = ConnectionPool(
            conninfo=self.dsn,
            kwargs={"row_factory": self._row_factory},
            min_size=1,
            max_size=int(os.getenv("AD_ENGINE_POSTGRES_POOL_SIZE", "5").strip() or "5"),
        )
        self._lock = Lock()
        self._initialize_schema()

    def create(
        self,
        bundle: AdBundle,
        metadata: dict[str, Any] | None = None,
        organization_id: str = "default",
    ) -> StoredCampaign:
        now = _utc_now()
        stored = StoredCampaign(
            campaign_id=str(uuid4()),
            organization_id=_normalize_organization_id(organization_id),
            created_at=now,
            updated_at=now,
            status="draft",
            bundle=bundle,
            metadata=metadata or {},
        )

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO campaigns (
                    id,
                    organization_id,
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    stored.campaign_id,
                    stored.organization_id,
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

    def get(self, campaign_id: str, organization_id: str | None = None) -> StoredCampaign | None:
        with self._lock, self._connect() as connection:
            if organization_id is None:
                row = connection.execute(
                    "SELECT payload_json FROM campaigns WHERE id = %s",
                    (campaign_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE id = %s AND organization_id = %s
                    """,
                    (campaign_id, _normalize_organization_id(organization_id)),
                ).fetchone()

        if row is None:
            return None
        return _stored_campaign_from_payload(_coerce_json_payload(row["payload_json"]))

    def list(self, organization_id: str | None = None) -> list[StoredCampaign]:
        with self._lock, self._connect() as connection:
            if organization_id is None:
                rows = connection.execute(
                    "SELECT payload_json FROM campaigns ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE organization_id = %s
                    ORDER BY created_at DESC
                    """,
                    (_normalize_organization_id(organization_id),),
                ).fetchall()

        return [
            _stored_campaign_from_payload(_coerce_json_payload(row["payload_json"]))
            for row in rows
        ]

    def update(
        self,
        campaign_id: str,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        approval_notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredCampaign | None:
        with self._lock, self._connect() as connection:
            if organization_id is None:
                row = connection.execute(
                    "SELECT payload_json FROM campaigns WHERE id = %s",
                    (campaign_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE id = %s AND organization_id = %s
                    """,
                    (campaign_id, _normalize_organization_id(organization_id)),
                ).fetchone()

            if row is None:
                return None

            stored = _stored_campaign_from_payload(_coerce_json_payload(row["payload_json"]))
            _apply_campaign_updates(
                stored, status=status, approval_notes=approval_notes, metadata=metadata)

            connection.execute(
                """
                UPDATE campaigns
                SET organization_id = %s,
                    brand_name = %s,
                    product_name = %s,
                    objective = %s,
                    status = %s,
                    updated_at = %s,
                    approved_at = %s,
                    approval_notes = %s,
                    metadata_json = %s,
                    payload_json = %s
                WHERE id = %s
                """,
                (
                    stored.organization_id,
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

    def approve(
        self,
        campaign_id: str,
        approval_notes: str | None = None,
        organization_id: str | None = None,
    ) -> StoredCampaign | None:
        return self.update(
            campaign_id,
            organization_id=organization_id,
            status="approved",
            approval_notes=approval_notes,
        )

    def update_variant(
        self,
        campaign_id: str,
        variant_index: int,
        *,
        organization_id: str | None = None,
        headline: str | None = None,
        primary_text: str | None = None,
        cta: str | None = None,
        image_prompt: str | None = None,
    ) -> StoredCampaign | None:
        with self._lock, self._connect() as connection:
            if organization_id is None:
                row = connection.execute(
                    "SELECT payload_json FROM campaigns WHERE id = %s",
                    (campaign_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM campaigns
                    WHERE id = %s AND organization_id = %s
                    """,
                    (campaign_id, _normalize_organization_id(organization_id)),
                ).fetchone()

            if row is None:
                return None

            stored = _stored_campaign_from_payload(_coerce_json_payload(row["payload_json"]))
            _apply_variant_updates(
                stored,
                variant_index,
                headline=headline,
                primary_text=primary_text,
                cta=cta,
                image_prompt=image_prompt,
            )

            connection.execute(
                """
                UPDATE campaigns
                SET updated_at = %s,
                    payload_json = %s
                WHERE id = %s
                """,
                (
                    stored.updated_at,
                    json.dumps(stored.to_dict()),
                    stored.campaign_id,
                ),
            )

        return stored

    def update_variant_image(
        self,
        campaign_id: str,
        variant_index: int,
        *,
        organization_id: str | None = None,
        image_status: str,
        generated_asset: GeneratedAsset | None = None,
        image_error: str | None = None,
    ) -> StoredCampaign | None:
        with self._lock, self._connect() as connection:
            stored = self._load_for_update(connection, campaign_id, organization_id)
            if stored is None:
                return None

            _apply_variant_image_updates(
                stored,
                variant_index,
                image_status=image_status,
                generated_asset=generated_asset,
                image_error=image_error,
            )
            self._persist_payload(connection, stored)

        return stored

    def _initialize_schema(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL DEFAULT 'default',
                    brand_name TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    approved_at TEXT,
                    approval_notes TEXT,
                    metadata_json JSONB NOT NULL,
                    payload_json JSONB NOT NULL
                )
                """
            )
            connection.execute(
                """
                ALTER TABLE campaigns
                ADD COLUMN IF NOT EXISTS organization_id TEXT NOT NULL DEFAULT 'default'
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_campaigns_created_at ON campaigns(created_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_campaigns_org_created_at ON campaigns(organization_id, created_at DESC)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_counters (
                    organization_id TEXT NOT NULL,
                    period TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    count BIGINT NOT NULL DEFAULT 0,
                    PRIMARY KEY (organization_id, period, metric)
                )
                """
            )

    def _connect(self):
        return self._pool.connection()

    def _load_for_update(
        self,
        connection,
        campaign_id: str,
        organization_id: str | None,
    ) -> StoredCampaign | None:
        if organization_id is None:
            row = connection.execute(
                "SELECT payload_json FROM campaigns WHERE id = %s",
                (campaign_id,),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT payload_json
                FROM campaigns
                WHERE id = %s AND organization_id = %s
                """,
                (campaign_id, _normalize_organization_id(organization_id)),
            ).fetchone()

        if row is None:
            return None
        return _stored_campaign_from_payload(_coerce_json_payload(row["payload_json"]))

    def _persist_payload(self, connection, stored: StoredCampaign) -> None:
        connection.execute(
            """
            UPDATE campaigns
            SET updated_at = %s,
                payload_json = %s
            WHERE id = %s
            """,
            (
                stored.updated_at,
                json.dumps(stored.to_dict()),
                stored.campaign_id,
            ),
        )

    def get_usage(self, organization_id: str, period: str, metric: str) -> int:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT count FROM usage_counters
                WHERE organization_id = %s AND period = %s AND metric = %s
                """,
                (_normalize_organization_id(organization_id), period, metric),
            ).fetchone()
        return int(row["count"]) if row is not None else 0

    def increment_usage(
        self, organization_id: str, period: str, metric: str, amount: int = 1
    ) -> int:
        org = _normalize_organization_id(organization_id)
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO usage_counters (organization_id, period, metric, count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (organization_id, period, metric)
                DO UPDATE SET count = usage_counters.count + EXCLUDED.count
                RETURNING count
                """,
                (org, period, metric, amount),
            ).fetchone()
        return int(row["count"])


def build_campaign_store(settings: StoreSettings | None = None) -> CampaignStore:
    resolved = settings or StoreSettings.from_env()
    if resolved.backend == "memory":
        return InMemoryCampaignStore()
    if resolved.backend == "sqlite":
        return SQLiteCampaignStore(resolved.sqlite_path)
    if resolved.backend == "postgres":
        return PostgreSQLCampaignStore(resolved.postgres_dsn)

    raise ValueError(
        f"Unknown campaign store backend '{resolved.backend}'. Supported backends: memory, sqlite, postgres"
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


def _apply_variant_updates(
    stored: StoredCampaign,
    variant_index: int,
    *,
    headline: str | None,
    primary_text: str | None,
    cta: str | None,
    image_prompt: str | None,
) -> None:
    if variant_index < 0 or variant_index >= len(stored.bundle.variants):
        raise ValueError("Variant index is out of range.")

    variant = stored.bundle.variants[variant_index]
    if headline is not None:
        variant.headline = _normalize_editable_text(headline, "headline")
    if primary_text is not None:
        variant.primary_text = _normalize_editable_text(primary_text, "primary_text")
    if cta is not None:
        variant.cta = _normalize_editable_text(cta, "cta")
    if image_prompt is not None:
        variant.image_prompt = _normalize_editable_text(image_prompt, "image_prompt")

    stored.updated_at = _utc_now()


def _apply_variant_image_updates(
    stored: StoredCampaign,
    variant_index: int,
    *,
    image_status: str,
    generated_asset: GeneratedAsset | None,
    image_error: str | None,
) -> None:
    if variant_index < 0 or variant_index >= len(stored.bundle.variants):
        raise ValueError("Variant index is out of range.")
    if image_status not in {"prompt_only", "generating", "generated", "failed"}:
        raise ValueError("Unsupported image status.")

    variant = stored.bundle.variants[variant_index]
    variant.image_status = image_status
    variant.generated_asset = generated_asset
    variant.image_error = image_error.strip() if image_error else None
    stored.updated_at = _utc_now()


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
                image_status=variant.get("image_status", "generated" if variant.get("generated_asset") else "prompt_only"),
                image_error=variant.get("image_error"),
                review_notes=list(variant.get("review_notes", [])),
                review_score=variant.get("review_score"),
                suggested_fixes=list(variant.get("suggested_fixes", [])),
            )
            for variant in bundle_payload["variants"]
        ],
        quality_summary=QualitySummary(
            strengths=list(quality_payload["strengths"]),
            risks=list(quality_payload["risks"]),
            scores=dict(quality_payload.get("scores", {})),
            suggested_fixes=list(quality_payload.get("suggested_fixes", [])),
        ),
        landing_section=_landing_section_from_payload(bundle_payload.get("landing_section")),
        generation_jobs=[
            GenerationJob(
                job_id=job["job_id"],
                kind=job["kind"],
                status=job["status"],
                provider=job["provider"],
                estimated_credits=int(job.get("estimated_credits", 0)),
                target=job.get("target"),
            )
            for job in bundle_payload.get("generation_jobs", [])
        ],
        cost_summary=dict(bundle_payload.get("cost_summary", {})),
    )

    return StoredCampaign(
        campaign_id=payload["id"],
        organization_id=_normalize_organization_id(payload.get("organization_id", "default")),
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


def _normalize_organization_id(value: str | None) -> str:
    normalized = (value or "default").strip()
    return normalized or "default"


def _normalize_editable_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"Field '{field}' cannot be empty.")
    if len(normalized) > 2000:
        raise ValueError(f"Field '{field}' exceeds maximum length of 2000 characters.")
    return normalized


def _matches_organization(stored: StoredCampaign, organization_id: str | None) -> bool:
    if organization_id is None:
        return True
    return stored.organization_id == _normalize_organization_id(organization_id)


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


def _landing_section_from_payload(payload: dict[str, Any] | None) -> LandingSection | None:
    if not payload:
        return None
    return LandingSection(
        headline=payload["headline"],
        subheadline=payload["subheadline"],
        proof_points=list(payload["proof_points"]),
        cta=payload["cta"],
        html_snippet=payload["html_snippet"],
    )


def _coerce_json_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return json.loads(value)
