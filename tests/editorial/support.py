"""Hand-authored fixture helpers, never feed-controlled review authority."""

from __future__ import annotations

from datetime import timedelta

from fixtures.support import read_json

from wrap_brief.editorial.controls import (
    ClaimEvidence,
    ControlLedger,
    apply_controls,
    metadata_reference,
)
from wrap_brief.grouping.identity import stable_item_id
from wrap_brief.grouping.stories import LeadEvidence, group_items
from wrap_brief.models import Item
from wrap_brief.state.snapshot import PollCheckpoint, Snapshot

PUBLIC_REF = "content/corrections/synthetic-review.md"
TITLE_MARKER = "Synthetic withdrawn sentinel M26Q9"
URL_MARKER = "https://example.com/synthetic-withdrawn-m26q9"
GUID_MARKER = "synthetic-guid-m26q9"
HEADER_MARKER = '"synthetic-validator-m26q9"'


def fixture() -> Snapshot:
    empty = Snapshot.from_dict(read_json("views/empty.json"))
    at = empty.observed_at
    a = Item(
        stable_item_id("demo-a", URL_MARKER),
        "demo-a",
        TITLE_MARKER,
        URL_MARKER,
        at,
        at,
        published_at=at - timedelta(minutes=30),
        guid=GUID_MARKER,
    )
    url = "https://example.org/synthetic-unrelated"
    b = Item(
        stable_item_id("demo-b", url),
        "demo-b",
        "Unrelated hand-authored coverage survives",
        url,
        at,
        at,
        published_at=at - timedelta(hours=1),
    )
    items = (a, b)
    groups = group_items(
        items, empty.sources, lead_evidence=tuple(LeadEvidence(item.id) for item in items)
    )
    return Snapshot(
        at,
        empty.sources,
        items,
        groups,
        (PollCheckpoint("demo-a", at, at, etag=HEADER_MARKER, entry_count=1, status="ok"),),
    )


def evidence(item: Item, at, *, status="reported", identifier=None) -> ClaimEvidence:
    return ClaimEvidence(
        identifier or f"claim-{item.id}",
        item.source_id,
        item.id,
        status,
        metadata_reference(item),
        at,
        PUBLIC_REF + "#claim",
    )


def ledger_for(
    snapshot: Snapshot, *, controls=(), at=None, claims=None, revision=1
) -> ControlLedger:
    """Tests explicitly choose reported reviews; incoming claim flags are never the policy."""
    at = at or snapshot.observed_at
    hidden_sources = {value.source_id for value in controls if value.action == "exclude_source"}
    hidden_ids = {value.item_id for value in controls if value.action in {"erase_item", "retract"}}
    if claims is None:
        claims = tuple(
            evidence(item, at)
            for item in snapshot.items
            if item.status in {"active", "corrected"}
            and item.source_id not in hidden_sources
            and item.id not in hidden_ids
        )
    return ControlLedger("synthetic-editorial", revision, at, claims, controls)


def finish(batch):
    groups = group_items(
        batch.items,
        batch.state.sources,
        lead_evidence=tuple(LeadEvidence(item.id) for item in batch.items),
        previous_clusters=batch.previous_clusters,
    )
    return batch.finish(clusters=groups)


def reviewed(snapshot, ledger=None, at=None):
    return finish(
        apply_controls(
            snapshot, ledger=ledger or ledger_for(snapshot), observed_at=at or snapshot.observed_at
        )
    )
