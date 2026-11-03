from __future__ import annotations

import socket
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

from fixtures.support import read_bytes, read_json

from wrap_brief.grouping.stories import LeadEvidence, group_items
from wrap_brief.ingest.http import FetchResult, RequestPolicy, fetch_feed
from wrap_brief.ingest.polling import SourcePoll, reduce_polls
from wrap_brief.models import ContractError
from wrap_brief.state.local import LocalState, StateConflict
from wrap_brief.state.snapshot import Snapshot, Tombstone


def rss(rows=(), *, host="example.com"):
    entries = []
    for path, title, published in rows:
        date = f"<pubDate>{escape(published)}</pubDate>" if published is not None else ""
        entries.append(
            f"<item><title>{escape(title)}</title><link>https://{host}/{escape(path)}</link>{date}</item>"
        )
    return (
        "<rss version='2.0'><channel><title>Synthetic</title>"
        + "".join(entries)
        + "</channel></rss>"
    ).encode()


def grouped(batch):
    groups = group_items(
        batch.items,
        batch.previous.sources,
        lead_evidence=tuple(LeadEvidence(item.id) for item in batch.items),
        previous_clusters=batch.previous_clusters,
    )
    return batch.to_snapshot(clusters=groups)


class PollingTests(unittest.TestCase):
    def setUp(self):
        fixture = Snapshot.from_dict(read_json("views/digest.json"))
        self.now = fixture.observed_at
        self.initial = replace(fixture, items=(), clusters=())
        self.source = self.initial.sources[0]

    def apply(self, response, previous=None, when=None):
        return reduce_polls(
            previous or self.initial,
            (SourcePoll(self.source.id, response),),
            expected_source_ids=(self.source.id,),
            observed_at=when or self.now,
        )

    def success(self, *, rows=None, previous=None, when=None, etag='"synthetic"', modified=None):
        body = rss(
            rows
            if rows is not None
            else (("one", "Synthetic game announced", "2026-01-02T12:00:00Z"),)
        )
        return self.apply(
            FetchResult("ok", 1, body=body, etag=etag, last_modified=modified), previous, when
        )

    def test_first_success_has_fixed_counts_baseline_and_no_network_or_clock_lookup(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network")):
            result = self.success()
        checkpoint = result.checkpoints[0]
        self.assertEqual(
            (checkpoint.last_success_at, checkpoint.last_attempt_at, checkpoint.entry_count),
            (self.now, self.now, 1),
        )
        self.assertEqual(
            (checkpoint.oldest_published_at, checkpoint.newest_published_at),
            (self.now - timedelta(minutes=30),) * 2,
        )
        self.assertEqual(result.outcomes[0].new_items, 1)
        self.assertEqual(result.outcomes[0].warnings, ("baseline_unknown",))
        self.assertEqual(result.health, "degraded")
        self.assertTrue(result.requires_regrouping)
        result.require_publishable()
        self.assertNotIn("Synthetic game", repr(result))

    def test_replay_stable_identity_and_observation_only_not_a_content_update(self):
        first = grouped(self.success())
        same = self.success(previous=first)
        self.assertEqual(grouped(same).to_json(), first.to_json())
        later = self.success(previous=first, when=self.now + timedelta(minutes=10))
        outcome = later.outcomes[0]
        self.assertEqual((outcome.new_items, outcome.updated_items), (0, 0))
        self.assertTrue(later.no_new)
        self.assertEqual(later.health, "healthy")
        self.assertEqual(later.items[0].first_seen_at, first.items[0].first_seen_at)
        self.assertEqual(later.items[0].published_at, first.items[0].published_at)
        self.assertGreater(later.items[0].last_seen_at, first.items[0].last_seen_at)

    def test_known_item_content_change_counts_update_and_explicit_group_handoff(self):
        first = grouped(self.success())
        changed = self.success(
            rows=(("one", "Synthetic game review", "2026-01-02T12:00:00Z"),),
            previous=first,
            when=self.now + timedelta(minutes=10),
        )
        self.assertEqual((changed.outcomes[0].new_items, changed.outcomes[0].updated_items), (0, 1))
        self.assertTrue(changed.requires_regrouping)
        self.assertEqual(changed.previous_clusters, first.clusters)
        with self.assertRaises(TypeError):
            changed.to_snapshot()
        with self.assertRaises(ContractError):
            changed.to_snapshot(clusters=())
        rebuilt = grouped(changed)
        self.assertEqual(rebuilt.clusters[0].topic, "review")

    def test_200_replaces_absent_validators_and_counts_physical_duplicate_rows(self):
        first = grouped(self.success(modified="Fri, 02 Jan 2026 12:00:00 GMT"))
        rows = (("one", "Synthetic game announced", "2026-01-02T12:00:00Z"),) * 2
        result = self.success(
            rows=rows, previous=first, when=self.now + timedelta(minutes=1), etag=None
        )
        self.assertEqual(len(result.items), 1)
        self.assertEqual(
            (result.outcomes[0].physical_rows, result.outcomes[0].accepted_rows), (2, 2)
        )
        self.assertEqual(result.checkpoints[0].entry_count, 2)
        self.assertIsNone(result.checkpoints[0].etag)
        self.assertIsNone(result.checkpoints[0].last_modified)

    def test_304_retains_records_clocks_count_window_and_missing_validators(self):
        first = grouped(self.success(modified="Fri, 02 Jan 2026 12:00:00 GMT"))
        later = self.now + timedelta(hours=1)
        result = self.apply(FetchResult("not_modified", 1, etag='"changed"'), first, later)
        self.assertEqual(result.items, first.items)
        self.assertFalse(result.requires_regrouping)
        self.assertEqual(result.checkpoints[0].etag, '"changed"')
        self.assertEqual(result.checkpoints[0].last_modified, first.checkpoints[0].last_modified)
        for key in ("entry_count", "oldest_published_at", "newest_published_at"):
            self.assertEqual(
                getattr(result.checkpoints[0], key), getattr(first.checkpoints[0], key)
            )
        self.assertEqual(result.checkpoints[0].last_success_at, later)
        self.assertEqual((result.health, result.no_new), ("healthy", True))
        self.assertEqual(result.outcomes[0].warnings, ())
        self.assertEqual(result.to_snapshot(clusters=first.clusters).items, first.items)

    def test_unsolicited_304_and_304_without_persisted_validator_fail_last_good(self):
        for previous in (self.initial, grouped(self.success(etag=None))):
            with self.subTest(has_checkpoint=bool(previous.checkpoints)):
                result = self.apply(
                    FetchResult("not_modified", 1), previous, self.now + timedelta(minutes=1)
                )
                self.assertEqual(
                    (result.health, result.outcomes[0].code), ("blocked", "invalid_304")
                )
                self.assertEqual(result.items, previous.items)
                if previous.checkpoints:
                    self.assertEqual(
                        result.checkpoints[0].last_success_at,
                        previous.checkpoints[0].last_success_at,
                    )

    def test_transport_parser_and_all_quarantine_freeze_last_good_metadata(self):
        first = grouped(self.success())
        bad = rss((("bad", "Synthetic bad date", "invalid-private-date"),))
        for response in (
            FetchResult("error", 2, "timeout"),
            FetchResult("ok", 1, body=b"<not-xml", etag='"poison"'),
            FetchResult("ok", 1, body=bad, etag='"poison"'),
        ):
            with self.subTest(status=response.status):
                result = self.apply(response, first, self.now + timedelta(minutes=1))
                self.assertEqual(result.items, first.items)
                new = result.checkpoints[0]
                old = first.checkpoints[0]
                self.assertEqual(
                    replace(new, last_attempt_at=old.last_attempt_at, status=old.status), old
                )
                self.assertEqual(new.status, "error")
                self.assertEqual(result.health, "blocked")
                self.assertFalse(result.no_new)
                with self.assertRaises(ContractError):
                    result.require_publishable()
                self.assertEqual(
                    grouped(result).items, first.items
                )  # Failure state may still persist.

    def test_empty_feed_is_valid_success_not_quarantine_or_no_http_body(self):
        first = grouped(self.success())
        result = self.success(rows=(), previous=first, when=self.now + timedelta(minutes=1))
        self.assertEqual(result.items, first.items)
        self.assertTrue(result.no_new)
        self.assertTrue(result.outcomes[0].usable)
        self.assertEqual(result.checkpoints[0].entry_count, 0)
        self.assertIsNone(result.checkpoints[0].oldest_published_at)
        self.assertIsNone(result.checkpoints[0].newest_published_at)
        self.assertEqual(result.outcomes[0].warnings, ("feed_window_shrank",))
        result.require_publishable()
        self.assertEqual(self.apply(FetchResult("ok", 1, body=b"")).health, "blocked")

    def test_mixed_valid_quarantine_and_parser_issues_count_all_physical_rows(self):
        rows = (
            ("one", "Synthetic known", "2026-01-02T12:00:00Z"),
            ("bad", "Synthetic bad", "invalid-date"),
        )
        body = rss(rows).replace(
            b"</channel>", b"<item><title>Missing link</title></item></channel>"
        )
        result = self.apply(FetchResult("ok", 1, body=body, etag='"mixed"'))
        outcome = result.outcomes[0]
        self.assertEqual(
            (outcome.physical_rows, outcome.accepted_rows, outcome.quarantined_rows), (3, 1, 2)
        )
        self.assertEqual(outcome.physical_rows, outcome.accepted_rows + outcome.quarantined_rows)
        self.assertEqual(result.checkpoints[0].entry_count, 3)
        self.assertIn("quarantined_entries", outcome.warnings)
        self.assertEqual(result.health, "degraded")
        self.assertTrue(outcome.usable)

    def test_all_parser_issues_do_not_masquerade_as_empty_feed_success(self):
        body = (
            b"<rss version='2.0'><channel><item><title>Missing link</title></item></channel></rss>"
        )
        result = self.apply(FetchResult("ok", 1, body=body, etag='"never-save"'))
        self.assertEqual(result.outcomes[0].code, "all_quarantined")
        self.assertEqual(
            (result.outcomes[0].physical_rows, result.outcomes[0].quarantined_rows), (1, 1)
        )
        self.assertIsNone(result.checkpoints[0].last_success_at)
        self.assertIsNone(result.checkpoints[0].etag)

    def test_deferrals_distinguish_zero_requests_and_actual_failed_attempts(self):
        first = grouped(self.success())
        for requests, code, delay in (
            (0, "poll_interval", 30),
            (1, "rate_limit", 3600),
            (2, "http_status", None),
        ):
            with self.subTest(requests=requests):
                result = self.apply(
                    FetchResult("deferred", requests, code, retry_after_seconds=delay),
                    first,
                    self.now + timedelta(minutes=1),
                )
                self.assertEqual(result.items, first.items)
                self.assertEqual(result.outcomes[0].retry_after_seconds, delay)
                self.assertEqual(result.health, "blocked")
                if requests == 0:
                    self.assertEqual(result.checkpoints, first.checkpoints)
                else:
                    self.assertEqual(result.checkpoints[0].status, "error")

    def test_partial_all_source_outage_and_expected_source_denominator(self):
        a, b = self.initial.sources[:2]
        response = FetchResult("ok", 1, body=rss(()))
        failed = FetchResult("error", 1, "network")
        partial = reduce_polls(
            self.initial,
            (SourcePoll(a.id, response), SourcePoll(b.id, failed)),
            expected_source_ids=(a.id, b.id),
            observed_at=self.now,
        )
        self.assertEqual(partial.health, "degraded")
        self.assertFalse(partial.no_new)
        partial.require_publishable()
        all_failed = reduce_polls(
            self.initial,
            (SourcePoll(a.id, failed), SourcePoll(b.id, failed)),
            expected_source_ids=(a.id, b.id),
            observed_at=self.now,
        )
        with self.assertRaises(ContractError):
            all_failed.require_publishable()
        self.assertEqual(all_failed.health, "blocked")
        only_a = self.apply(response)
        self.assertEqual(len(only_a.outcomes), 1)  # Other registry sources were not requested.
        self.assertTrue(only_a.no_new)
        none = reduce_polls(self.initial, (), expected_source_ids=(), observed_at=self.now)
        self.assertEqual(none.health, "no_sources")
        with self.assertRaises(ContractError):
            none.require_publishable()

    def test_partial_deferral_is_degraded_not_healthy(self):
        a, b = self.initial.sources[:2]
        result = reduce_polls(
            self.initial,
            (
                SourcePoll(a.id, FetchResult("ok", 1, body=rss(()))),
                SourcePoll(
                    b.id, FetchResult("deferred", 0, "poll_interval", retry_after_seconds=20)
                ),
            ),
            expected_source_ids=(a.id, b.id),
            observed_at=self.now,
        )
        self.assertEqual(result.health, "degraded")
        self.assertFalse(result.no_new)
        self.assertEqual(len(result.checkpoints), 1)

    def test_gap_uses_previous_success_not_last_failed_attempt_and_strict_boundary(self):
        first = grouped(self.success())
        failed = grouped(
            self.apply(FetchResult("error", 1, "network"), first, self.now + timedelta(hours=1))
        )
        for published, warning in (("2026-01-02T12:30:00Z", False), ("2026-01-02T12:30:01Z", True)):
            result = self.success(
                rows=(("new", "Synthetic new", published),),
                previous=failed,
                when=self.now + timedelta(hours=2),
            )
            self.assertEqual("possible_gap" in result.outcomes[0].warnings, warning)

    def test_window_dates_use_current_accepted_publication_not_retained_seen_or_updates(self):
        first = grouped(self.success())
        result = self.success(
            rows=(("unknown", "Synthetic unknown", None),),
            previous=first,
            when=self.now + timedelta(hours=1),
        )
        self.assertIsNone(result.checkpoints[0].oldest_published_at)
        self.assertIn("publication_unknown", result.outcomes[0].warnings)
        empty = self.success(rows=())
        self.assertNotIn("publication_unknown", empty.outcomes[0].warnings)

    def test_saturated_nonoverlap_warns_without_claiming_completeness(self):
        rows = tuple(
            (f"item-{n}", f"Synthetic item {n}", "2026-01-02T12:00:00Z") for n in range(100)
        )
        first = self.success(rows=rows)
        self.assertIn("saturated_no_overlap", first.outcomes[0].warnings)
        again = self.success(
            rows=rows, previous=grouped(first), when=self.now + timedelta(minutes=1)
        )
        self.assertNotIn("saturated_no_overlap", again.outcomes[0].warnings)
        self.assertEqual(again.outcomes[0].new_items, 0)

    def test_tombstones_and_sticky_withdrawal_suppress_new_identity_counts(self):
        first = grouped(self.success())
        item = first.items[0]
        tombstoned = replace(
            first, items=(), clusters=(), tombstones=(Tombstone(item.id, item.source_id, self.now),)
        )
        result = self.success(previous=tombstoned, when=self.now + timedelta(minutes=1))
        self.assertEqual(result.items, ())
        self.assertEqual(result.outcomes[0].new_items, 0)
        self.assertTrue(result.no_new)
        removed = replace(
            first,
            items=(replace(item, status="removed"),),
            clusters=(replace(first.clusters[0], lead_id=None, correction_status="retracted"),),
        )
        result = self.success(previous=removed, when=self.now + timedelta(minutes=1))
        self.assertEqual(result.items[0].status, "removed")

    def test_malformed_fetch_results_are_fatal_without_echo_and_no_partial_state(self):
        for response in (
            FetchResult("unknown-private-marker", 1),
            FetchResult("ok", 0, body=b""),
            FetchResult("ok", 1, body=None),
            FetchResult("ok", True, body=b""),
            FetchResult("not_modified", 1, body=b""),
            FetchResult("error", 1, "network", body=b"private-payload"),
            FetchResult("deferred", 1, "rate_limit", retry_after_seconds=float("inf")),
            FetchResult("ok", 1, body=rss(()), etag="x\r\nprivate-header"),
        ):
            with self.subTest(status=response.status), self.assertRaises(ContractError) as error:
                self.apply(response)
            self.assertNotIn("private-", str(error.exception))
        self.assertEqual(self.initial.checkpoints, ())

    def test_unknown_duplicate_missing_source_results_and_backward_clock_rejected(self):
        response = FetchResult("ok", 1, body=rss(()))
        source_id = self.source.id
        for polls, expected in (
            ((SourcePoll(source_id, response), SourcePoll(source_id, response)), (source_id,)),
            ((), (source_id,)),
            ((SourcePoll("unknown", response),), ("unknown",)),
            ((SourcePoll(source_id, response),), (source_id, source_id)),
        ):
            with self.assertRaises(ContractError):
                reduce_polls(
                    self.initial, polls, expected_source_ids=expected, observed_at=self.now
                )
        with self.assertRaises(ContractError):
            self.apply(response, when=self.now - timedelta(seconds=1))
        with self.assertRaises(ContractError):
            self.apply(response, previous=replace(self.initial, kind="live"))

    def test_to_snapshot_rejects_missing_duplicate_and_incompatible_stale_grouping(self):
        result = self.success()
        groups = group_items(
            result.items,
            self.initial.sources,
            lead_evidence=tuple(LeadEvidence(item.id) for item in result.items),
        )
        with self.assertRaises(ContractError):
            result.to_snapshot(clusters=(groups[0], replace(groups[0], id="duplicate")))
        first = grouped(result)
        original = first.items[0]
        body = rss((("one", "Rumor of synthetic game", "2026-01-02T12:00:00Z"),))
        # Feed normalization labels reported; old confirmed group must not be silently reused.
        confirmed = replace(
            first,
            items=(replace(original, claim_status="confirmed"),),
            clusters=(replace(first.clusters[0], claim_status="confirmed"),),
        )
        changed = self.apply(
            FetchResult("ok", 1, body=body), confirmed, self.now + timedelta(minutes=1)
        )
        with self.assertRaises(ContractError):
            changed.to_snapshot(clusters=confirmed.clusters)
        self.assertTrue(changed.requires_regrouping)
        self.assertEqual(grouped(changed).clusters[0].claim_status, "rumor")

    def test_feed_row_and_snapshot_serialized_size_bounds_fail_without_truncation(self):
        rows = tuple((f"item-{n}", "Synthetic item", None) for n in range(101))
        result = self.success(rows=rows)
        self.assertEqual(result.health, "blocked")
        self.assertEqual(result.items, ())
        good = self.success()
        with (
            patch("wrap_brief.state.snapshot.MAX_SNAPSHOT_BYTES", 100),
            self.assertRaises(ContractError),
        ):
            grouped(good)

    def test_shared_synthetic_rss_atom_and_empty_fixtures(self):
        for source_id, name, count in (
            ("demo-a", "rss-basic.xml", 2),
            ("demo-b", "atom-basic.xml", 2),
            ("demo-a", "rss-empty.xml", 0),
            ("demo-b", "atom-empty.xml", 0),
        ):
            source = next(s for s in self.initial.sources if s.id == source_id)
            result = reduce_polls(
                self.initial,
                (SourcePoll(source.id, FetchResult("ok", 1, body=read_bytes("feeds/" + name))),),
                expected_source_ids=(source.id,),
                observed_at=self.now,
            )
            self.assertTrue(result.outcomes[0].usable)
            self.assertEqual(result.outcomes[0].physical_rows, count)

    def test_record_overflow_is_fatal_and_input_state_is_not_partially_advanced(self):
        first = grouped(self.success())
        before = first.to_json()
        with patch("wrap_brief.state.snapshot.MAX_RECORDS", 1), self.assertRaises(ContractError):
            self.success(
                rows=(("two", "Synthetic second", None),),
                previous=first,
                when=self.now + timedelta(minutes=1),
            )
        self.assertEqual(first.to_json(), before)

    def test_unchanged_200_retains_reviewed_status_and_claim_controls(self):
        first = grouped(self.success())
        for fields in (
            {"status": "quarantined"},
            {"status": "corrected"},
            {"claim_status": "rumor"},
            {"claim_status": "confirmed"},
        ):
            with self.subTest(fields=fields):
                item = replace(first.items[0], **fields)
                groups = group_items((item,), first.sources, lead_evidence=(LeadEvidence(item.id),))
                restricted = replace(first, items=(item,), clusters=groups)
                result = self.success(previous=restricted, when=self.now + timedelta(minutes=1))
                self.assertEqual(result.items[0].status, item.status)
                self.assertEqual(result.items[0].claim_status, item.claim_status)
                self.assertEqual(result.outcomes[0].updated_items, 0)
                refreshed = grouped(result).clusters[0]
                if item.status == "quarantined":
                    self.assertIsNone(refreshed.lead_id)
                if item.status == "corrected":
                    self.assertEqual(refreshed.correction_status, "corrected")
                if item.claim_status in {"rumor", "confirmed"}:
                    self.assertEqual(refreshed.claim_status, item.claim_status)

    def test_changed_feed_cannot_automatically_lift_quarantine_correction_or_rumor(self):
        first = grouped(self.success())
        for fields in (
            {"status": "quarantined"},
            {"status": "corrected"},
            {"claim_status": "rumor"},
        ):
            with self.subTest(fields=fields):
                item = replace(first.items[0], **fields)
                groups = group_items((item,), first.sources, lead_evidence=(LeadEvidence(item.id),))
                restricted = replace(first, items=(item,), clusters=groups)
                changed = self.success(
                    rows=(("one", "Revised synthetic announcement", "2026-01-02T12:00:00Z"),),
                    previous=restricted,
                    when=self.now + timedelta(minutes=1),
                )
                self.assertEqual(changed.items[0].status, item.status)
                self.assertEqual(changed.items[0].claim_status, item.claim_status)

    def test_oversized_integer_backoff_and_nonfinite_delays_fail_bounded(self):
        for delay in (10**1000, float("nan"), float("inf"), -1, True):
            with self.subTest(kind=type(delay)), self.assertRaises(ContractError):
                self.apply(FetchResult("deferred", 1, "rate_limit", retry_after_seconds=delay))

    def test_incompatible_publisher_dates_fail_only_that_source_and_keep_last_good(self):
        initial = grouped(self.success(rows=(("one", "Synthetic known update", None),)))
        original = replace(initial.items[0], updated_at=self.now - timedelta(hours=1))
        previous = replace(initial, items=(original,))
        old_bytes = previous.to_json()
        source_a, source_b = previous.sources[:2]
        responses = (
            SourcePoll(
                source_a.id,
                FetchResult(
                    "ok",
                    1,
                    body=rss((("one", "Synthetic newly dated", "2026-01-02T12:00:00Z"),)),
                    etag='"must-not-advance"',
                ),
            ),
            SourcePoll(source_b.id, FetchResult("ok", 1, body=rss(()))),
        )
        result = reduce_polls(
            previous,
            responses,
            expected_source_ids=(source_a.id, source_b.id),
            observed_at=self.now + timedelta(minutes=1),
        )
        self.assertEqual(result.health, "degraded")
        self.assertEqual(result.items, previous.items)
        self.assertEqual(
            (result.outcomes[0].status, result.outcomes[0].code), ("error", "metadata_conflict")
        )
        self.assertTrue(result.outcomes[1].usable)
        self.assertEqual(
            result.checkpoints[0].last_success_at, previous.checkpoints[0].last_success_at
        )
        self.assertEqual(result.checkpoints[0].etag, previous.checkpoints[0].etag)
        result.require_publishable()
        self.assertEqual(previous.to_json(), old_bytes)

    def test_identity_integrity_conflict_remains_fatal_not_source_quarantine(self):
        previous = grouped(self.success())
        corrupted = replace(
            previous, items=(replace(previous.items[0], url="https://example.com/other"),)
        )
        with self.assertRaisesRegex(ContractError, "identity conflict"):
            self.success(previous=corrupted, when=self.now + timedelta(minutes=1))

    def test_checkpoint_restart_then_conditional_304_restart_and_stale_cas(self):
        first = grouped(self.success())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private.sqlite3"
            revision = LocalState(path).commit(first, expected_revision=0)
            store = LocalState(path)
            loaded = store.load()
            self.assertEqual(loaded.snapshot.checkpoints, first.checkpoints)
            source = replace(
                self.source,
                enabled=True,
                approval_status="approved",
                approval_ref="tests/fixtures/README.md",
                reviewed_at=self.now,
            )
            requests = []

            def transport(request):
                from wrap_brief.ingest.http import HopResponse

                requests.append(request)
                return HopResponse(304)

            later = self.now + timedelta(minutes=2)
            fetched = fetch_feed(
                source,
                loaded.snapshot.checkpoints[0],
                policy=RequestPolicy("tests/fixtures/README.md", self.now, 60),
                observed_at=later,
                transport=transport,
            )
            self.assertEqual(dict(requests[0].headers)["If-None-Match"], '"synthetic"')
            next_batch = self.apply(fetched, loaded.snapshot, later)
            candidate = next_batch.to_snapshot(clusters=loaded.snapshot.clusters)
            next_revision = store.commit(candidate, expected_revision=revision.version)
            with self.assertRaises(StateConflict):
                store.commit(first, expected_revision=revision.version)
            restarted = LocalState(path).load()
            self.assertEqual(restarted.version, next_revision.version)
            self.assertEqual(restarted.snapshot.checkpoints[0].status, "not_modified")
            self.assertEqual(restarted.snapshot.items, first.items)


if __name__ == "__main__":
    unittest.main()
