from __future__ import annotations

import pytest

from ad_engine.engine import AdGenerationEngine
from ad_engine.providers import build_provider_stack
from ad_engine.store import (
    InMemoryCampaignStore,
    SQLiteCampaignStore,
    StoreSettings,
    build_campaign_store,
)


@pytest.fixture
def bundle(brief_payload):
    return AdGenerationEngine(build_provider_stack()).run(brief_payload)


def test_create_assigns_id_and_draft_status(bundle):
    store = InMemoryCampaignStore()

    stored = store.create(bundle, metadata={"source": "test"})

    assert stored.campaign_id
    assert stored.status == "draft"
    assert stored.metadata == {"source": "test"}
    assert stored.created_at == stored.updated_at
    assert stored.approved_at is None


def test_get_returns_stored_campaign(bundle):
    store = InMemoryCampaignStore()
    stored = store.create(bundle)

    fetched = store.get(stored.campaign_id)

    assert fetched is not None
    assert fetched.campaign_id == stored.campaign_id


def test_organization_scoping_isolates_campaigns(bundle):
    store = InMemoryCampaignStore()
    alpha = store.create(bundle, organization_id="alpha")
    beta = store.create(bundle, organization_id="beta")

    assert store.get(alpha.campaign_id, organization_id="alpha") is not None
    assert store.get(alpha.campaign_id, organization_id="beta") is None
    assert [item.campaign_id for item in store.list(organization_id="alpha")] == [
        alpha.campaign_id
    ]
    assert [item.campaign_id for item in store.list(organization_id="beta")] == [
        beta.campaign_id
    ]


def test_get_unknown_returns_none():
    store = InMemoryCampaignStore()

    assert store.get("does-not-exist") is None


def test_list_orders_by_created_at_desc(bundle):
    store = InMemoryCampaignStore()
    first = store.create(bundle)
    second = store.create(bundle)

    listed = store.list()

    assert [item.campaign_id for item in listed[:2]] == [
        second.campaign_id,
        first.campaign_id,
    ]


def test_approve_sets_status_and_timestamp(bundle):
    store = InMemoryCampaignStore()
    stored = store.create(bundle)

    approved = store.approve(stored.campaign_id, approval_notes="Looks good")

    assert approved is not None
    assert approved.status == "approved"
    assert approved.approval_notes == "Looks good"
    assert approved.approved_at is not None


def test_update_variant_edits_copy(bundle):
    store = InMemoryCampaignStore()
    stored = store.create(bundle)

    updated = store.update_variant(
        stored.campaign_id,
        0,
        headline="Edited headline",
        primary_text="Edited primary text",
        cta="Start now",
        image_prompt="Edited image prompt",
    )

    assert updated is not None
    variant = updated.bundle.variants[0]
    assert variant.headline == "Edited headline"
    assert variant.primary_text == "Edited primary text"
    assert variant.cta == "Start now"
    assert variant.image_prompt == "Edited image prompt"
    assert updated.updated_at != stored.created_at


def test_update_variant_rejects_out_of_range_index(bundle):
    store = InMemoryCampaignStore()
    stored = store.create(bundle)

    with pytest.raises(ValueError, match="out of range"):
        store.update_variant(stored.campaign_id, 99, headline="Nope")


def test_unsupported_status_raises(bundle):
    store = InMemoryCampaignStore()
    stored = store.create(bundle)

    with pytest.raises(ValueError, match="Unsupported campaign status"):
        store.update(stored.campaign_id, status="rejected")


def test_reverting_status_clears_approved_at(bundle):
    store = InMemoryCampaignStore()
    stored = store.create(bundle)
    store.approve(stored.campaign_id, approval_notes="Looks good")

    reverted = store.update(stored.campaign_id, status="draft")

    assert reverted is not None
    assert reverted.status == "draft"
    assert reverted.approved_at is None


def test_build_campaign_store_rejects_unknown_backend():
    with pytest.raises(ValueError, match="Unknown campaign store backend"):
        build_campaign_store(StoreSettings(backend="redis"))


def test_sqlite_round_trip(bundle, local_tmp_path):
    store = SQLiteCampaignStore(str(local_tmp_path / "ad_engine.db"))

    stored = store.create(bundle, metadata={"source": "test"})
    fetched = store.get(stored.campaign_id)

    assert fetched is not None
    assert fetched.campaign_id == stored.campaign_id
    assert fetched.bundle.brief.brand_name == bundle.brief.brand_name
    assert fetched.metadata == {"source": "test"}
    assert fetched.organization_id == "default"


def test_sqlite_organization_scoping_persists(bundle, local_tmp_path):
    store = SQLiteCampaignStore(str(local_tmp_path / "ad_engine.db"))

    alpha = store.create(bundle, organization_id="alpha")
    store.create(bundle, organization_id="beta")

    fresh = SQLiteCampaignStore(str(local_tmp_path / "ad_engine.db"))

    assert fresh.get(alpha.campaign_id, organization_id="alpha") is not None
    assert fresh.get(alpha.campaign_id, organization_id="beta") is None
    assert len(fresh.list(organization_id="alpha")) == 1


def test_sqlite_approve_persists(bundle, local_tmp_path):
    db_path = str(local_tmp_path / "ad_engine.db")
    store = SQLiteCampaignStore(db_path)
    stored = store.create(bundle)

    approved = store.approve(stored.campaign_id, approval_notes="Ship it")

    fresh = SQLiteCampaignStore(db_path)
    fetched = fresh.get(stored.campaign_id)

    assert approved is not None
    assert fetched is not None
    assert fetched.status == "approved"
    assert fetched.approval_notes == "Ship it"


def test_sqlite_update_variant_persists(bundle, local_tmp_path):
    db_path = str(local_tmp_path / "ad_engine.db")
    store = SQLiteCampaignStore(db_path)
    stored = store.create(bundle)

    store.update_variant(stored.campaign_id, 0, headline="Edited headline")

    fresh = SQLiteCampaignStore(db_path)
    fetched = fresh.get(stored.campaign_id)

    assert fetched is not None
    assert fetched.bundle.variants[0].headline == "Edited headline"
