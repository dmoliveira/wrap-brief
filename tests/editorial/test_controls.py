from __future__ import annotations

import hashlib
import json
import socket
import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from editorial.support import (
    GUID_MARKER,
    PUBLIC_REF,
    TITLE_MARKER,
    URL_MARKER,
    evidence,
    finish,
    fixture,
    ledger_for,
    reviewed,
)
from wrap_brief.editorial import controls
from wrap_brief.editorial.controls import (
    ControlLedger,
    CorrectionControl,
    EditorialResult,
    apply_controls,
    metadata_reference,
)
from wrap_brief.ingest.http import FetchResult
from wrap_brief.ingest.polling import SourcePoll, reduce_polls
from wrap_brief.models import Cluster, ContractError
from wrap_brief.render.digest import render_digest, render_editorial
from wrap_brief.state.snapshot import Tombstone


class Parsed(HTMLParser):
    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.tags, self.text = [], []
        self.feed(value)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


class EditorialControlTests(unittest.TestCase):
    def setUp(self):
        self.state = fixture()
        self.at = self.state.observed_at
        self.item = next(item for item in self.state.items if item.source_id == "demo-a")

    def control(self, action, *, item=None, at=None, **kwargs):
        item = item or self.item
        return CorrectionControl(
            "control-" + action,
            item.source_id,
            action,
            at or self.at,
            item_id=None if action == "exclude_source" else item.id,
            **kwargs,
        )

    def correction(self, item=None):
        item = item or self.item
        return self.control(
            "correct",
            item=item,
            metadata_ref=metadata_reference(item),
            public_notice_ref=PUBLIC_REF + "#correction",
        )

    def test_canonical_domain_separated_metadata_excludes_observation_and_flags(self):
        original = metadata_reference(self.item)
        changed = replace(
            self.item,
            first_seen_at=self.at - timedelta(days=1),
            last_seen_at=self.at + timedelta(hours=1),
            status="corrected",
            claim_status="confirmed",
        )
        self.assertEqual(metadata_reference(changed), original)
        data = self.item.to_dict()
        metadata = {
            key: data[key]
            for key in ("id", "source_id", "title", "url", "guid", "published_at", "updated_at")
        }
        canonical = json.dumps(
            metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
        self.assertEqual(
            original, hashlib.sha256(b"wrap-brief:claim-metadata:v1\0" + canonical).hexdigest()
        )
        for key, value in (
            ("title", "Changed claim"),
            ("url", "https://example.com/other"),
            ("guid", "changed-guid"),
            ("published_at", None),
            ("updated_at", self.at),
        ):
            with self.subTest(field=key):
                self.assertNotEqual(
                    metadata_reference(replace(self.item, **{key: value})), original
                )
        offset = timezone(timedelta(hours=2))
        self.assertEqual(
            metadata_reference(
                replace(self.item, published_at=self.item.published_at.astimezone(offset))
            ),
            original,
        )

    def test_all_labels_come_from_current_explicit_evidence_not_item_flags(self):
        forged = replace(
            self.state,
            items=tuple(replace(item, claim_status="confirmed") for item in self.state.items),
        )
        self.assertNotIn(
            "Confirmed by source", render_editorial(reviewed(forged, ledger_for(self.state)))
        )
        for label in ("reported", "confirmed", "rumor"):
            claims = tuple(evidence(item, self.at, status=label) for item in self.state.items)
            ledger = ledger_for(self.state, claims=claims)
            result = reviewed(self.state, ledger)
            self.assertTrue(all(item.claim_status == label for item in result.snapshot.items))
            self.assertEqual({notice.kind for notice in result.notices}, {label})
        with self.assertRaisesRegex(ContractError, "current evidence required"):
            apply_controls(
                self.state, ledger=ControlLedger("empty", 1, self.at), observed_at=self.at
            )

    def test_stale_evidence_blocks_but_observation_updates_remain_reviewed(self):
        ledger = ledger_for(self.state)
        later = replace(
            self.state,
            observed_at=self.at + timedelta(hours=1),
            items=tuple(
                replace(item, last_seen_at=self.at + timedelta(hours=1))
                for item in self.state.items
            ),
        )
        reviewed(later, ledger, later.observed_at)
        changed = replace(
            later,
            items=tuple(
                replace(item, title="Changed headline") if item.id == self.item.id else item
                for item in later.items
            ),
        )
        with self.assertRaisesRegex(ContractError, "metadata needs review"):
            reviewed(changed, ledger, later.observed_at)
        self.assertEqual(
            next(
                item
                for item in reviewed(
                    changed, ledger_for(changed, at=later.observed_at)
                ).snapshot.items
                if item.id == self.item.id
            ).claim_status,
            "reported",
        )

    def test_corrected_status_needs_current_metadata_bound_correction_provenance(self):
        corrected = replace(
            self.state,
            items=tuple(
                replace(item, status="corrected") if item.id == self.item.id else item
                for item in self.state.items
            ),
        )
        with self.assertRaisesRegex(ContractError, "current provenance required"):
            reviewed(corrected, ledger_for(corrected))
        control = self.correction()
        ledger = ledger_for(self.state, controls=(control,))
        result = reviewed(self.state, ledger)
        self.assertEqual(
            next(item for item in result.snapshot.items if item.id == self.item.id).status,
            "corrected",
        )
        html = render_editorial(result)
        self.assertIn("Correction acknowledged", html)
        self.assertIn("Corrected coverage", html)
        changed = replace(
            self.state,
            items=tuple(
                replace(item, title="A corrected newer claim") if item.id == self.item.id else item
                for item in self.state.items
            ),
        )
        with self.assertRaisesRegex(ContractError, "metadata needs review"):
            reviewed(changed, ledger_for(changed, controls=(control,)))
        # The replacement reviewed set retains effective correction acknowledgement on an old active Snapshot.
        replacement = replace(ledger, revision=2, reviewed_at=self.at + timedelta(minutes=1))
        self.assertIn(
            "Correction acknowledged",
            render_editorial(reviewed(self.state, replacement, replacement.reviewed_at)),
        )

    def test_correct_never_lifts_retraction_removal_or_quarantine_and_absent_target_has_no_notice(
        self,
    ):
        control = self.correction()
        for status in ("retracted", "removed", "quarantined"):
            state = replace(
                self.state,
                clusters=(),
                items=tuple(
                    replace(item, status=status) if item.id == self.item.id else item
                    for item in self.state.items
                ),
            )
            result = reviewed(state, ledger_for(state, controls=(control,)))
            self.assertEqual(
                next(item for item in result.snapshot.items if item.id == self.item.id).status,
                status,
            )
            self.assertNotIn("Correction acknowledged", render_editorial(result))
        absent = replace(
            self.state,
            items=tuple(item for item in self.state.items if item.id != self.item.id),
            clusters=(),
        )
        self.assertNotIn(
            "Correction acknowledged",
            render_editorial(reviewed(absent, ledger_for(absent, controls=(control,)))),
        )

    def test_retraction_survives_changed_publisher_metadata_and_has_only_generic_public_trace(self):
        control = self.control("retract", public_notice_ref=PUBLIC_REF + "#retraction")
        later = self.at + timedelta(hours=1)
        changed = replace(
            self.state,
            observed_at=later,
            clusters=(),
            items=tuple(
                replace(
                    item,
                    title="New withdrawn title",
                    updated_at=later,
                    last_seen_at=later,
                    claim_status="confirmed",
                )
                if item.id == self.item.id
                else item
                for item in self.state.items
            ),
        )
        result = reviewed(changed, ledger_for(changed, controls=(control,), at=later), later)
        html = render_editorial(result)
        self.assertIn("Coverage withdrawn following review", html)
        for marker in ("New withdrawn title", URL_MARKER, GUID_MARKER, self.item.id):
            self.assertNotIn(marker, html)
        self.assertNotIn(self.item.id, [notice.item_id for notice in result.notices])

    def test_erase_uses_only_minimal_tombstone_and_removes_all_returned_group_references(self):
        dirty_groups = tuple(
            replace(group, topic=TITLE_MARKER, override_ref=URL_MARKER)
            for group in self.state.clusters
        )
        state = replace(self.state, clusters=dirty_groups)
        control = self.control("erase_item")
        batch = apply_controls(
            state, ledger=ledger_for(state, controls=(control,)), observed_at=self.at
        )
        self.assertEqual(
            {field.name for field in fields(Tombstone)},
            {"schema_version", "item_id", "source_id", "removed_at"},
        )
        self.assertNotIn(self.item.id, {item.id for item in batch.items})
        self.assertTrue(
            all(self.item.id not in group.member_ids for group in batch.previous_clusters)
        )
        combined = batch.state.to_json() + batch.ledger.to_json()
        for marker in (TITLE_MARKER, URL_MARKER, GUID_MARKER):
            self.assertNotIn(marker.encode(), combined)
        self.assertNotIn("erase_item", {notice.kind for notice in finish(batch).notices})
        again = apply_controls(self.state, ledger=batch.ledger, observed_at=self.at)
        self.assertEqual(again.state.to_json(), batch.state.to_json())

    def test_source_exclusion_erases_records_checkpoints_tombstones_and_suppresses_future_ids(self):
        stale = Tombstone("previously-erased", "demo-a", self.at)
        state = replace(self.state, tombstones=(stale,))
        control = self.control("exclude_source")
        ledger = ledger_for(state, controls=(control,))
        result = reviewed(state, ledger)
        self.assertFalse(
            next(source for source in result.snapshot.sources if source.id == "demo-a").enabled
        )
        self.assertFalse(any(item.source_id == "demo-a" for item in result.snapshot.items))
        self.assertFalse(
            any(
                value.source_id == "demo-a"
                for value in (*result.snapshot.checkpoints, *result.snapshot.tombstones)
            )
        )
        self.assertNotIn(stale.item_id, result.snapshot.to_json().decode())
        new = replace(
            self.item,
            id="future-unseen-id",
            url="https://example.com/future",
            title="Future excluded headline",
        )
        future = replace(
            self.state,
            items=(new, *[item for item in self.state.items if item.id != self.item.id]),
            clusters=(),
        )
        self.assertNotIn("Future excluded headline", render_editorial(reviewed(future, ledger)))
        for marker in (TITLE_MARKER, URL_MARKER, GUID_MARKER):
            self.assertNotIn(marker.encode(), result.ledger.to_json())

    def test_dormant_suppression_and_target_source_conflicts_are_checked(self):
        erase = self.control("erase_item")
        absent = replace(self.state, items=(), clusters=())
        batch = apply_controls(
            absent, ledger=ledger_for(absent, controls=(erase,)), observed_at=self.at
        )
        self.assertIn(self.item.id, {value.item_id for value in batch.state.tombstones})
        bad = replace(erase, source_id="demo-b")
        with self.assertRaisesRegex(ContractError, "source conflict"):
            reviewed(self.state, ledger_for(self.state, controls=(bad,)))
        tombstoned = replace(absent, tombstones=(Tombstone(self.item.id, "demo-a", self.at),))
        with self.assertRaisesRegex(ContractError, "erased metadata"):
            apply_controls(
                tombstoned,
                ledger=ControlLedger("stale", 1, self.at, (evidence(self.item, self.at),)),
                observed_at=self.at,
            )

    def test_ledger_rejects_duplicate_conflicting_erased_or_excluded_claims_and_controls(self):
        claim = evidence(self.item, self.at)
        erase = self.control("erase_item")
        exclude = self.control("exclude_source")
        for claims, actions in (
            ((claim, claim), ()),
            ((claim,), (erase,)),
            ((claim,), (exclude,)),
            ((), (erase, exclude)),
            ((), (erase, replace(erase, id="other"))),
            ((claim,), (replace(self.correction(), source_id="demo-b"),)),
        ):
            with self.subTest(actions=actions), self.assertRaises(ContractError):
                ControlLedger("conflict", 1, self.at, claims, actions)

    def test_review_times_and_publisher_metadata_review_order_fail_closed(self):
        claim = evidence(self.item, self.at)
        with self.assertRaises(ContractError):
            ControlLedger(
                "future", 1, self.at, (replace(claim, reviewed_at=self.at + timedelta(seconds=1)),)
            )
        with self.assertRaises(ContractError):
            reviewed(
                self.state,
                replace(ledger_for(self.state), reviewed_at=self.at + timedelta(seconds=1)),
            )
        with self.assertRaises(ContractError):
            apply_controls(
                self.state,
                ledger=ledger_for(self.state),
                observed_at=self.at - timedelta(seconds=1),
            )
        before = self.item.published_at - timedelta(seconds=1)
        ledger = ledger_for(
            self.state,
            claims=tuple(
                replace(value, reviewed_at=before) for value in ledger_for(self.state).claims
            ),
        )
        with self.assertRaisesRegex(ContractError, "precedes publisher"):
            reviewed(self.state, ledger)
        with self.assertRaises(ContractError):
            replace(claim, reviewed_at=datetime(2026, 1, 2))

    def test_action_matrix_schema_and_reference_bounds_reject_untrusted_fields(self):
        control = self.correction()
        for value in (
            {**control.to_dict(), "reviewed": True},
            {**control.to_dict(), "action": "reactivate"},
            {**control.to_dict(), "item_id": None},
            {**control.to_dict(), "metadata_ref": None},
        ):
            with self.assertRaises(ContractError):
                CorrectionControl.from_dict(value)
        for action in ("erase_item", "retract", "exclude_source"):
            with self.assertRaises(ContractError):
                self.control(action, metadata_ref=metadata_reference(self.item))
        for ref in (
            "../private",
            "docs/private.md",
            "https://example.com/?private=path",
            "https://127.0.0.1/",
            "https://example.com/#bad%20fragment",
            "javascript:bad",
            "content/corrections/.hidden.md",
        ):
            with self.subTest(reference=ref), self.assertRaises(ContractError):
                replace(evidence(self.item, self.at), evidence_ref=ref)
        with self.assertRaises(ContractError):
            replace(control, schema_version=True)
        with self.assertRaises(ContractError):
            replace(ledger_for(self.state), revision=True)

    def test_json_roundtrip_duplicate_unknown_nonfinite_oversize_and_immutability(self):
        ledger = ledger_for(self.state, controls=(self.correction(),))
        self.assertEqual(ControlLedger.from_json(ledger.to_json()), ledger)
        self.assertEqual(ledger.digest, ControlLedger.from_json(ledger.to_json()).digest)
        with self.assertRaises(FrozenInstanceError):
            ledger.revision = 3
        for data in (
            b'{"id":"x","id":"x"}',
            b'{"revision":NaN}',
            ledger.to_json()[:-1],
            b"x" * (controls.MAX_LEDGER_BYTES + 1),
        ):
            with self.assertRaises(ContractError):
                ControlLedger.from_json(data)
        changed = ledger.to_dict()
        changed["reviewed"] = True
        with self.assertRaises(ContractError):
            ControlLedger.from_json(json.dumps(changed).encode())
        with patch.object(controls, "MAX_LEDGER_BYTES", 1), self.assertRaises(ContractError):
            ledger.to_json()
        with patch.object(controls, "MAX_REVIEWS", 0), self.assertRaises(ContractError):
            ledger_for(self.state)

    def test_snapshot_only_entry_and_pure_operations_do_not_fetch_read_or_choose_clock(self):
        ledger = ledger_for(self.state)
        response = FetchResult("ok", 1, body=b"<rss><channel/></rss>")
        poll = reduce_polls(
            self.state,
            (SourcePoll("demo-a", response),),
            expected_source_ids=("demo-a",),
            observed_at=self.at,
        )
        for value in (poll, self.state.to_dict(), object()):
            with self.assertRaises(ContractError):
                apply_controls(value, ledger=ledger, observed_at=self.at)
        with (
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(Path, "read_bytes", side_effect=AssertionError("filesystem")),
        ):
            result = reviewed(self.state, ledger)
            self.assertIn("Headline from", render_editorial(result))
        self.assertNotIn(TITLE_MARKER, repr(result))

    def test_finish_requires_complete_partition_truthful_labels_and_result_binding(self):
        ledger = ledger_for(self.state)
        batch = apply_controls(self.state, ledger=ledger, observed_at=self.at)
        valid = finish(batch)
        with self.assertRaises(ContractError):
            batch.finish(clusters=())
        groups = valid.snapshot.clusters
        with self.assertRaises(ContractError):
            batch.finish(clusters=(*groups, replace(groups[0], id="duplicate")))
        with self.assertRaises(ContractError):
            batch.finish(clusters=(replace(groups[0], correction_status="corrected"), *groups[1:]))
        forged = replace(
            valid.snapshot,
            items=tuple(replace(item, claim_status="confirmed") for item in valid.snapshot.items),
        )
        with self.assertRaises(ContractError):
            EditorialResult(forged, ledger)
        with self.assertRaises(ContractError):
            render_editorial(valid.snapshot)

    def test_title_rumor_caution_and_quarantined_group_do_not_invent_retraction_notice(self):
        item = replace(self.item, title="Unconfirmed rumor of fictional game")
        state = replace(self.state, items=(item,), clusters=())
        result = reviewed(state, ledger_for(state))
        self.assertEqual(result.snapshot.items[0].claim_status, "reported")
        self.assertEqual(result.snapshot.clusters[0].claim_status, "rumor")
        with self.assertRaises(ContractError):
            EditorialResult(
                replace(
                    result.snapshot,
                    clusters=(replace(result.snapshot.clusters[0], claim_status="reported"),),
                ),
                result.ledger,
            )
        quarantined = replace(state, items=(replace(item, status="quarantined"),))
        result = reviewed(quarantined, ledger_for(quarantined))
        self.assertEqual(result.snapshot.clusters[0].correction_status, "retracted")
        self.assertNotIn("Coverage withdrawn following review", render_editorial(result))
        self.assertEqual(result.notices, ())

    def test_editorial_html_escapes_text_references_and_keeps_legacy_and_synthetic_limits(self):
        payload = '"><img src=x onerror=alert(1)>&'
        state = replace(
            self.state,
            items=tuple(
                replace(item, title=payload) if item.id == self.item.id else item
                for item in self.state.items
            ),
            clusters=(),
        )
        result = reviewed(state)
        html = render_editorial(result)
        parsed = Parsed(html)
        self.assertNotIn("<img", html)
        self.assertTrue(any(payload in text for text in parsed.text))
        self.assertNotIn(
            PUBLIC_REF + "#claim", [attrs.get("href") for tag, attrs in parsed.tags if tag == "a"]
        )
        self.assertTrue(any(PUBLIC_REF in text for text in parsed.text))
        ids = [attrs["id"] for _, attrs in parsed.tags if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("Editorial records", render_digest(self.state))
        with self.assertRaises(ContractError):
            render_editorial(reviewed(replace(self.state, kind="live")))
        from wrap_brief.render import digest

        with (
            patch.object(digest, "MAX_HTML_BYTES", len(html.encode()) - 1),
            self.assertRaises(ContractError),
        ):
            render_editorial(result)

    def test_final_partition_rejects_poisoned_topics_and_override_references(self):
        exclusion = self.control("exclude_source")
        batch = apply_controls(
            self.state, ledger=ledger_for(self.state, controls=(exclusion,)), observed_at=self.at
        )
        valid = finish(batch)
        for changes in ({"topic": TITLE_MARKER}, {"override_ref": URL_MARKER}):
            groups = tuple(replace(group, **changes) for group in valid.snapshot.clusters)
            with self.subTest(changes=changes):
                with self.assertRaises(ContractError):
                    batch.finish(clusters=groups)
                with self.assertRaises(ContractError):
                    EditorialResult(replace(valid.snapshot, clusters=groups), valid.ledger)

    def test_generic_retraction_does_not_publish_internal_review_id_equal_to_withdrawn_target(self):
        control = replace(
            self.control("retract", public_notice_ref=PUBLIC_REF + "#retraction"), id=self.item.id
        )
        result = reviewed(self.state, ledger_for(self.state, controls=(control,)))
        html = render_editorial(result)
        self.assertIn("Coverage withdrawn following review", html)
        self.assertNotIn(self.item.id, html)
        self.assertTrue(all(not hasattr(notice, "id") for notice in result.notices))

    def test_prior_identifier_never_retains_withdrawn_item_id_or_identifier_safe_title(self):
        for poisoned in (self.item.id, "synthetic-withdrawn-sentinel-m26q9"):
            items = tuple(
                replace(item, title=poisoned) if item.id == self.item.id else item
                for item in self.state.items
            )
            group = Cluster(poisoned, tuple(item.id for item in items), self.item.id)
            state = replace(self.state, items=items, clusters=(group,))
            exclusion = self.control("exclude_source")
            batch = apply_controls(
                state, ledger=ledger_for(state, controls=(exclusion,)), observed_at=self.at
            )
            result = finish(batch)
            poisoned_final = tuple(
                replace(group, id=poisoned) for group in result.snapshot.clusters
            )
            self.assertEqual(
                batch.finish(clusters=poisoned_final).snapshot.to_json(), result.snapshot.to_json()
            )
            with self.assertRaises(ContractError):
                EditorialResult(replace(result.snapshot, clusters=poisoned_final), result.ledger)
            for data in (
                batch.state.to_json(),
                result.snapshot.to_json(),
                render_editorial(result).encode(),
            ):
                self.assertNotIn(poisoned.encode(), data)
            self.assertEqual(
                {item.id for item in result.snapshot.items},
                {item.id for item in items if item.source_id != "demo-a"},
            )

    def test_final_identifier_is_rebound_by_finish_and_exactly_checked_on_direct_result(self):
        batch = apply_controls(self.state, ledger=ledger_for(self.state), observed_at=self.at)
        valid = finish(batch)
        groups = tuple(
            replace(group, id="editorial-group-v1-" + ("0" if n == 0 else "1") * 64)
            for n, group in enumerate(valid.snapshot.clusters)
        )
        self.assertEqual(batch.finish(clusters=groups).snapshot.to_json(), valid.snapshot.to_json())
        with self.assertRaisesRegex(ContractError, "derived identifier mismatch"):
            EditorialResult(replace(valid.snapshot, clusters=groups), valid.ledger)

    def test_editorial_identifiers_bind_only_current_sorted_membership_not_historical_ids(self):
        batch = apply_controls(
            replace(self.state, clusters=()), ledger=ledger_for(self.state), observed_at=self.at
        )
        members = tuple(item.id for item in self.state.items)
        group = Cluster("raw-untrusted-id", members, self.item.id)
        first = batch.finish(clusters=(group,))
        reverse = batch.finish(
            clusters=(replace(group, id="other-untrusted-id", member_ids=tuple(reversed(members))),)
        )
        self.assertEqual(first.snapshot.to_json(), reverse.snapshot.to_json())
        expected = (
            "editorial-group-v1-"
            + hashlib.sha256(
                b"wrap-brief:editorial-group:v1\0"
                + json.dumps(
                    {"member_ids": sorted(members)}, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()
        )
        self.assertEqual(first.snapshot.clusters[0].id, expected)
        exclusion = self.control("exclude_source")
        remaining = apply_controls(
            first.snapshot,
            ledger=ledger_for(first.snapshot, controls=(exclusion,)),
            observed_at=self.at,
        )
        self.assertNotEqual(remaining.previous_clusters[0].id, expected)
        self.assertNotIn(expected.encode(), remaining.state.to_json())
        self.assertEqual(
            {item.id for item in finish(remaining).snapshot.items}, set(members) - {self.item.id}
        )
