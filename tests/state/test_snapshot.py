from __future__ import annotations

import socket
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
from unittest.mock import patch

from fixtures.support import read_json

from wrap_brief.ingest.parsers import RawEntry
from wrap_brief.models import ContractError
from wrap_brief.state.snapshot import (
    MAX_SNAPSHOT_BYTES,
    PollCheckpoint,
    Snapshot,
    Tombstone,
    merge_items,
)


def snapshot() -> Snapshot:
    return Snapshot.from_dict(read_json("views/digest.json"))


class SnapshotTests(unittest.TestCase):
    def test_complete_round_trip_and_canonical_record_order(self):
        value = snapshot()
        reversed_value = replace(
            value,
            sources=tuple(reversed(value.sources)),
            items=tuple(reversed(value.items)),
            clusters=tuple(reversed(value.clusters)),
        )
        self.assertEqual(value, Snapshot.from_json(value.to_json()))
        self.assertEqual(value.to_json(), reversed_value.to_json())
        self.assertEqual(value.digest, reversed_value.digest)
        self.assertEqual(len(value.items), 5)
        self.assertEqual(len(value.clusters), 3)
        self.assertTrue(any(v.published_at is None for v in value.items))
        self.assertNotIn(value.items[0].title, repr(value))

    def test_set_like_members_and_hosts_are_canonical(self):
        value = snapshot()
        group = next(c for c in value.clusters if len(c.member_ids) > 1)
        changed = replace(
            value,
            clusters=tuple(
                replace(c, member_ids=tuple(reversed(c.member_ids))) if c.id == group.id else c
                for c in value.clusters
            ),
        )
        self.assertEqual(value.to_json(), changed.to_json())
        source = value.sources[0]
        a = replace(source, allowed_hosts=("example.org", *source.allowed_hosts))
        b = replace(a, allowed_hosts=tuple(reversed(a.allowed_hosts)))
        self.assertEqual(
            replace(value, sources=(a, *value.sources[1:])).to_json(),
            replace(value, sources=(b, *value.sources[1:])).to_json(),
        )

    def test_checkpoint_and_minimal_tombstone_round_trip(self):
        value = snapshot()
        checkpoint = PollCheckpoint(
            value.sources[0].id,
            value.observed_at,
            value.observed_at,
            etag='W/"synthetic-etag"',
            last_modified="Fri, 02 Jan 2026 12:00:00 GMT",
            entry_count=2,
            oldest_published_at=value.observed_at - timedelta(hours=1),
            newest_published_at=value.observed_at,
            status="ok",
        )
        tombstone = Tombstone("absent-synthetic-id", value.sources[0].id, value.observed_at)
        complete = replace(value, checkpoints=(checkpoint,), tombstones=(tombstone,))
        self.assertEqual(complete, Snapshot.from_json(complete.to_json()))
        self.assertEqual(
            set(tombstone.to_dict()), {"schema_version", "item_id", "source_id", "removed_at"}
        )
        self.assertNotIn("etag", repr(checkpoint))

    def test_checkpoint_unknowns_errors_and_feed_window_invariants(self):
        value = snapshot()
        source_id = value.sources[0].id
        now = value.observed_at
        failed = PollCheckpoint(source_id, now)
        self.assertIsNone(failed.last_success_at)
        for changes in (
            {"etag": "unvalidated"},
            {"status": "ok"},
            {"last_success_at": now + timedelta(seconds=1)},
            {"entry_count": True},
            {"entry_count": 101},
            {"oldest_published_at": now},
            {
                "last_success_at": now,
                "entry_count": 0,
                "oldest_published_at": now,
                "newest_published_at": now,
            },
            {"last_success_at": now, "etag": "bad\nheader"},
        ):
            with self.subTest(changes=list(changes)), self.assertRaises(ContractError):
                PollCheckpoint(source_id, now, **changes)
        data = failed.to_dict()
        data["authorization"] = "synthetic-unknown-field"
        with self.assertRaises(ContractError):
            PollCheckpoint.from_dict(data)

    def test_refs_counts_versions_and_raw_metadata_rejected(self):
        value = snapshot()
        for changes in (
            {"schema_version": True},
            {"schema_version": 2},
            {"items": list(value.items)},
            {"items": (*value.items, value.items[0])},
            {"items": (RawEntry("demo-a", "synthetic", "https://example.com/a"),)},
            {"observed_at": datetime(2026, 1, 2)},
            {"observed_at": value.observed_at - timedelta(days=1)},
            {"sources": ()},
            {"checkpoints": (PollCheckpoint("unknown", value.observed_at),)},
        ):
            with self.subTest(changes=list(changes)), self.assertRaises(ContractError):
                replace(value, **changes)

    def test_json_validation_is_bounded_and_does_not_echo(self):
        for data in (
            b"not-json-synthetic-private",
            b"\xff",
            b"{}",
            b'{"schema_version":1,"schema_version":1}',
            b'{"schema_version":NaN}',
            b"[" * 1500,
            b"x" * (MAX_SNAPSHOT_BYTES + 1),
            "not-bytes",
        ):
            with self.subTest(kind=type(data).__name__), self.assertRaises(ContractError) as caught:
                Snapshot.from_json(data)
            self.assertNotIn("synthetic-private", str(caught.exception))
        data = snapshot().to_dict()
        data["raw_feed"] = "synthetic"
        with self.assertRaises(ContractError):
            Snapshot.from_dict(data)

    def test_tombstone_does_not_retain_body_and_cannot_overlap_record(self):
        value = snapshot()
        item = value.items[0]
        tombstone = Tombstone(item.id, item.source_id, value.observed_at)
        with self.assertRaises(ContractError):
            replace(value, tombstones=(tombstone,))
        with self.assertRaises(ContractError):
            replace(value, tombstones=(Tombstone("absent", "unknown", value.observed_at),))
        with self.assertRaises(FrozenInstanceError):
            tombstone.item_id = "changed"

    def test_no_clock_or_network_lookup(self):
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("network prohibited")):
            value = snapshot()
            self.assertEqual(value, Snapshot.from_json(value.to_json()))


class ReplayTests(unittest.TestCase):
    def test_known_update_metadata_beats_later_undated_or_earlier_equal_update(self):
        old = replace(self.old, title="Synthetic corrected title", updated_at=self.old.last_seen_at)
        undated = replace(
            self.old,
            title="Synthetic stale title",
            last_seen_at=self.old.last_seen_at + timedelta(hours=1),
        )
        self.assertEqual(merge_items((old,), (undated,))[0].title, old.title)
        older_seen = replace(
            old,
            title="Synthetic old observation",
            first_seen_at=old.first_seen_at - timedelta(minutes=1),
            last_seen_at=old.last_seen_at - timedelta(minutes=1),
        )
        self.assertEqual(merge_items((old,), (older_seen,))[0].title, old.title)

    def setUp(self):
        self.value = snapshot()
        self.old = self.value.items[0]

    def test_replay_is_idempotent_and_does_not_freshen_publication(self):
        incoming = replace(
            self.old,
            title="Synthetic newer title",
            first_seen_at=self.old.first_seen_at + timedelta(days=1),
            last_seen_at=self.old.last_seen_at + timedelta(days=1),
            published_at=self.old.published_at + timedelta(hours=1),
        )
        merged = merge_items((self.old,), (incoming,))
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].first_seen_at, self.old.first_seen_at)
        self.assertEqual(merged[0].published_at, self.old.published_at)
        self.assertEqual(merged[0].last_seen_at, incoming.last_seen_at)
        self.assertEqual(merged, merge_items(merged, (incoming,)))

    def test_stale_source_update_cannot_overwrite_newer_metadata(self):
        old = replace(self.old, title="Synthetic corrected title", updated_at=self.old.last_seen_at)
        incoming = replace(
            self.old,
            title="Synthetic stale title",
            last_seen_at=self.old.last_seen_at + timedelta(hours=1),
            updated_at=self.old.published_at,
        )
        merged = merge_items((old,), (incoming,))[0]
        self.assertEqual(merged.title, old.title)
        self.assertEqual(merged.last_seen_at, incoming.last_seen_at)
        self.assertEqual(merged.updated_at, old.updated_at)

    def test_retraction_is_sticky_and_erasure_tombstone_suppresses_resurfacing(self):
        retracted = replace(self.old, status="retracted")
        self.assertEqual(merge_items((retracted,), (self.old,))[0].status, "retracted")
        tombstone = Tombstone(self.old.id, self.old.source_id, self.value.observed_at)
        self.assertEqual(merge_items((self.old,), (self.old,), tombstones=(tombstone,)), ())
        self.assertEqual(merge_items((), (self.old,), tombstones=(tombstone,)), ())

    def test_identity_conflicts_are_not_silent_overwrites(self):
        other_source = "demo-a" if self.old.source_id != "demo-a" else "demo-b"
        for item in (
            replace(self.old, source_id=other_source),
            replace(self.old, url="https://example.com/different"),
        ):
            with self.assertRaises(ContractError):
                merge_items((self.old,), (item,))
        with self.assertRaises(ContractError):
            merge_items(
                (self.old,),
                (),
                tombstones=(Tombstone(self.old.id, other_source, self.value.observed_at),),
            )

    def test_tracking_variants_merge_without_title_clock_id_changes(self):
        incoming = replace(self.old, url=self.old.url + "?utm_source=synthetic")
        self.assertEqual(len(merge_items((self.old,), (incoming,))), 1)


if __name__ == "__main__":
    unittest.main()
