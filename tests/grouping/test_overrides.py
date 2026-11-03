from __future__ import annotations

import json
import socket
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from wrap_brief.editorial.controls import (
    ClaimEvidence,
    ControlLedger,
    apply_controls,
    metadata_reference,
)
from wrap_brief.grouping import overrides
from wrap_brief.grouping.identity import stable_item_id
from wrap_brief.grouping.overrides import (
    GroupingDecision,
    GroupingPlan,
    OverrideTarget,
    group_with_overrides,
    grouping_reference,
)
from wrap_brief.grouping.stories import LeadEvidence, group_items
from wrap_brief.models import Cluster, ContractError, Item, Source
from wrap_brief.state.local import LocalState
from wrap_brief.state.snapshot import Snapshot

AT = datetime(2026, 1, 4, 12, tzinfo=UTC)
REF = "config/overrides/README.md#synthetic"
SOURCES = tuple(
    Source(
        key,
        "Synthetic channel " + key,
        "https://example.com/",
        f"https://example.com/feeds/{key}",
        ("example.com",),
        "Hand-authored grouping fixture only",
    )
    for key in ("a", "b", "c")
)


def item(key, title="Fictional citrine game update announced", *, source="a", url=None):
    return Item(
        key,
        source,
        title,
        url or f"https://example.com/story/{key}",
        AT,
        AT,
        published_at=AT - timedelta(hours=1),
    )


def evidence(items):
    return tuple(LeadEvidence(value.id) for value in items)


def decision(action, items, *, identifier="synthetic-review", partitions=()):
    targets = tuple(
        OverrideTarget(value.source_id, value.id, grouping_reference(value)) for value in items
    )
    return GroupingDecision(identifier, action, targets, AT, REF, partitions)


def plan(*decisions):
    return GroupingPlan("synthetic-current", 1, AT, tuple(decisions))


def grouped(items, current_plan, *, previous=(), policies=None, at=AT, fuzzy=True):
    return group_with_overrides(
        items,
        SOURCES,
        lead_evidence=evidence(items) if policies is None else policies,
        plan=current_plan,
        observed_at=at,
        previous_clusters=previous,
        fuzzy_enabled=fuzzy,
    )


class FuzzyPolicyTests(unittest.TestCase):
    def test_unknown_event_identical_titles_require_same_uri_even_in_previous_groups(self):
        values = (
            item("a", "Silvergate servers return after maintenance"),
            item("b", "Silvergate servers return after maintenance", source="b"),
        )
        before = tuple(value.to_dict() for value in values)
        for previous in ((), (Cluster("former-related", ("a", "b"), "a"),)):
            first = group_items(
                values, SOURCES, lead_evidence=evidence(values), previous_clusters=previous
            )
            self.assertEqual({group.member_ids for group in first}, {("a",), ("b",)})
            self.assertEqual(
                group_items(
                    tuple(reversed(values)),
                    SOURCES,
                    lead_evidence=tuple(reversed(evidence(values))),
                    previous_clusters=previous,
                ),
                first,
            )
        self.assertEqual(tuple(value.to_dict() for value in values), before)

    def test_unknown_event_uri_shortcut_keeps_all_hard_semantic_guards(self):
        a = item("a", "Silvergate servers return after maintenance")
        b = item("b", a.title, source="b", url=a.url)
        self.assertEqual(len(group_items((a, b), SOURCES, lead_evidence=evidence((a, b)))), 1)
        cases = (
            (a, replace(b, claim_status="rumor")),
            (
                replace(a, title="Silvergate maintenance 1 completed"),
                replace(b, title="Silvergate maintenance 2 completed"),
            ),
            (
                replace(a, title="Silvergate standard maintenance completed"),
                replace(b, title="Silvergate deluxe maintenance completed"),
            ),
            (
                replace(a, title='"Silvergate" maintenance completed'),
                replace(b, title='"Cloud Loom" maintenance completed'),
            ),
            (a, replace(b, published_at=a.published_at - timedelta(hours=49))),
        )
        for values in cases:
            with self.subTest(titles=tuple(value.title for value in values)):
                self.assertEqual(
                    len(group_items(values, SOURCES, lead_evidence=evidence(values))), 2
                )

    def test_disable_affects_new_and_previous_fuzzy_groups_without_changing_items(self):
        items = (item("a"), item("b", source="b"), item("c", source="c"))
        before = tuple(value.to_dict() for value in items)
        original = group_items(items, SOURCES, lead_evidence=evidence(items))
        self.assertEqual(len(original), 1)
        for previous in ((), original):
            disabled = group_items(
                items,
                SOURCES,
                lead_evidence=evidence(items),
                previous_clusters=previous,
                fuzzy_enabled=False,
            )
            self.assertEqual(len(disabled), 3)
            self.assertEqual(
                {key for group in disabled for key in group.member_ids},
                {value.id for value in items},
            )
        self.assertEqual(tuple(value.to_dict() for value in items), before)
        self.assertEqual(
            stable_item_id("a", "https://example.com/article?utm_source=fixture"),
            stable_item_id("a", "https://example.com/article"),
        )

    def test_disable_preserves_exact_uri_groups_and_hard_semantic_guards(self):
        a, b = item("a"), item("b", source="b", url="https://example.com/story/a")
        self.assertEqual(
            len(group_items((a, b), SOURCES, lead_evidence=evidence((a, b)), fuzzy_enabled=False)),
            1,
        )
        b = replace(b, title="Fictional citrine game review")
        self.assertEqual(
            len(group_items((a, b), SOURCES, lead_evidence=evidence((a, b)), fuzzy_enabled=False)),
            2,
        )
        for flag in (1, None, "false"):
            with self.assertRaises(ContractError):
                group_items((a, b), SOURCES, lead_evidence=evidence((a, b)), fuzzy_enabled=flag)


class OverrideTests(unittest.TestCase):
    def setUp(self):
        self.items = (item("a"), item("b", source="b"), item("c", source="c"))

    def test_split_is_locked_replayable_and_does_not_absorb_new_members(self):
        current = plan(decision("split", self.items, partitions=(("a",), ("b", "c"))))
        first = grouped(self.items, current)
        self.assertEqual({group.member_ids for group in first}, {("a",), ("b", "c")})
        self.assertTrue(
            all(group.confidence == "manual" and group.override_ref == REF for group in first)
        )
        replay = GroupingPlan.from_json(current.to_json())
        self.assertEqual(
            grouped(tuple(reversed(self.items)), replay, previous=tuple(reversed(first))), first
        )
        new = (*self.items, item("new", source="c"))
        result = grouped(new, current, previous=first)
        self.assertIn(("new",), {group.member_ids for group in result})
        bad_context = (replace(first[0], member_ids=(*first[0].member_ids, "new")), *first[1:])
        with self.assertRaisesRegex(ContractError, "reviewed coverage"):
            grouped(new, current, previous=bad_context)

    def test_merge_locks_only_reviewed_targets_and_preserves_every_original_record(self):
        items = (
            item("a", "Fictional citrine game announced"),
            item("b", "Fictional citrine game review", source="b"),
            item("c", "Fictional citrine game announced", source="c"),
        )
        before = tuple(value.to_dict() for value in items)
        result = grouped(items, plan(decision("merge", items[:2])))
        self.assertEqual({group.member_ids for group in result}, {("a", "b"), ("c",)})
        self.assertEqual(tuple(value.to_dict() for value in items), before)
        manual = next(group for group in result if group.confidence == "manual")
        self.assertTrue(manual.id.startswith("manual-group-v1-"))
        self.assertNotIn("synthetic-review", manual.id)
        self.assertEqual(manual.topic, "other")

    def test_mixed_event_lead_does_not_depend_on_order_or_lexical_ids_and_withdrawal_demotes(self):
        for first_id, second_id in (("a", "z"), ("z", "a")):
            announcement = item(first_id, "Fictional citrine game announced")
            review = item(second_id, "Fictional citrine game review", source="b")
            items = (announcement, review)
            policies = (
                LeadEvidence(first_id, "primary", 100, REF),
                LeadEvidence(second_id, "original", 0, REF),
            )
            current = plan(decision("merge", items))
            original = grouped(items, current, policies=policies)[0]
            self.assertEqual((original.topic, original.lead_id), ("other", review.id))
            self.assertEqual(
                grouped(tuple(reversed(items)), current, policies=tuple(reversed(policies)))[0],
                original,
            )
            withdrawn = (announcement, replace(review, status="retracted"))
            self.assertEqual(grouping_reference(review), grouping_reference(withdrawn[1]))
            result = grouped(withdrawn, current, previous=(original,), policies=policies)[0]
            self.assertEqual(
                (result.topic, result.lead_id, result.correction_status),
                ("other", announcement.id, "corrected"),
            )
            self.assertEqual(result.claim_status, "reported")

    def test_missing_targets_are_dormant_and_resurfacing_observation_changes_reapply(self):
        current = plan(decision("merge", self.items[:2]))
        first = grouped(self.items[:2], current)
        missing = grouped(self.items[1:2], current, previous=first)
        self.assertEqual(missing[0].member_ids, ("b",))
        later = tuple(
            replace(value, last_seen_at=AT + timedelta(hours=1)) for value in self.items[:2]
        )
        self.assertEqual(
            grouped(later, current, previous=missing, at=AT + timedelta(hours=1)), first
        )
        self.assertEqual(grouped((), current, previous=first), ())

    def test_release_is_explicit_and_prior_manual_context_is_never_blindly_downgraded(self):
        items = (
            item("a", "Fictional citrine game announced"),
            item("b", "Fictional citrine game review", source="b"),
        )
        merged = grouped(items, plan(decision("merge", items)))
        with self.assertRaisesRegex(ContractError, "reviewed coverage"):
            grouped(items, plan(), previous=merged)
        released = grouped(items, plan(decision("release", items)), previous=merged)
        self.assertEqual(len(released), 2)
        self.assertTrue(all(group.confidence != "manual" for group in released))

    def test_all_prior_retained_overlap_is_rejected_before_locked_target_filtering(self):
        manual = Cluster("manual", ("a", "b"), "a", confidence="manual", override_ref=REF)
        automatic = Cluster("automatic", ("a", "c"), "a")
        with self.assertRaisesRegex(ContractError, "overlapping retained"):
            grouped(
                self.items, plan(decision("merge", self.items[:2])), previous=(manual, automatic)
            )
        with self.assertRaisesRegex(ContractError, "duplicate identifier"):
            grouped(
                self.items,
                plan(),
                previous=(automatic, replace(automatic, member_ids=("expired",), lead_id=None)),
            )
        expired_overlap = (
            Cluster("old-a", ("a", "expired"), "a"),
            Cluster("old-b", ("b", "expired"), "b"),
        )
        self.assertEqual(len(grouped(self.items[:2], plan(), previous=expired_overlap)), 2)

    def test_fuzzy_disable_and_reenable_never_silently_override_reviewed_partitions(self):
        current = plan(decision("split", self.items, partitions=(("a",), ("b", "c"))))
        first = grouped(self.items, current, fuzzy=False)
        self.assertEqual(grouped(self.items, current, previous=first, fuzzy=True), first)
        automatic = group_items(self.items, SOURCES, lead_evidence=evidence(self.items))
        self.assertEqual(len(grouped(self.items, plan(), previous=automatic, fuzzy=False)), 3)

    def test_bound_metadata_and_source_changes_fail_instead_of_fuzzy_fallback(self):
        current = plan(decision("merge", self.items[:2]))
        for change in (
            {"title": "Changed claim"},
            {"url": "https://example.com/changed"},
            {"guid": "changed-guid"},
            {"published_at": None},
            {"updated_at": AT},
            {"claim_status": "confirmed"},
        ):
            values = (replace(self.items[0], **change), self.items[1])
            with (
                self.subTest(change=change),
                self.assertRaisesRegex(ContractError, "metadata needs review"),
            ):
                grouped(values, current)
        bad_target = replace(current.decisions[0].targets[0], source_id="b")
        bad = replace(current.decisions[0], targets=(bad_target, current.decisions[0].targets[1]))
        with self.assertRaisesRegex(ContractError, "source conflict"):
            grouped(self.items[:2], plan(bad))

    def test_claim_and_availability_are_never_promoted_by_grouping_decisions(self):
        values = (
            replace(self.items[0], status="retracted", claim_status="rumor"),
            replace(self.items[1], status="quarantined", claim_status="confirmed"),
        )
        result = grouped(values, plan(decision("merge", values)))[0]
        self.assertIsNone(result.lead_id)
        self.assertEqual((result.claim_status, result.correction_status), ("reported", "retracted"))
        self.assertEqual(values[0].status, "retracted")
        self.assertEqual(values[1].status, "quarantined")

    def test_review_clock_source_bounds_and_exact_evidence_validation(self):
        current = plan(decision("merge", self.items[:2]))
        with self.assertRaises(ContractError):
            grouped(self.items, replace(current, reviewed_at=AT + timedelta(seconds=1)))
        with self.assertRaises(ContractError):
            grouped(self.items, current, at=AT - timedelta(seconds=1))
        with self.assertRaises(ContractError):
            grouped(self.items, current, policies=evidence(self.items)[:-1])
        with self.assertRaises(ContractError):
            grouped(self.items, current, policies=(*evidence(self.items), LeadEvidence("unknown")))
        before_publication = self.items[0].published_at - timedelta(seconds=1)
        old = replace(current.decisions[0], reviewed_at=before_publication)
        with self.assertRaisesRegex(ContractError, "precedes publisher"):
            grouped(self.items[:2], plan(old))

    def test_plan_shape_conflicts_partitions_bounds_and_fixed_errors(self):
        merge = decision("merge", self.items[:2])
        with self.assertRaises(ContractError):
            plan(merge, replace(merge, id="other"))
        with self.assertRaises(ContractError):
            replace(merge, targets=(merge.targets[0], merge.targets[0]))
        with self.assertRaises(ContractError):
            replace(merge, action="release", partitions=(("a", "b"),))
        for parts in ((("a",),), (("a",), ("a", "b")), (("a",), ("unknown",)), ((), ("a", "b"))):
            with self.assertRaises(ContractError):
                replace(merge, action="split", partitions=parts)
        good = plan(merge)
        self.assertEqual(GroupingPlan.from_json(good.to_json()), good)
        with self.assertRaises(FrozenInstanceError):
            good.revision = 2
        for raw in (
            b'{"id":"x","id":"x"}',
            b'{"revision":NaN}',
            b"x" * (overrides.MAX_PLAN_BYTES + 1),
        ):
            with self.assertRaises(ContractError):
                GroupingPlan.from_json(raw)
        data = json.loads(good.to_json())
        data["approved"] = "synthetic-private-error-marker"
        with self.assertRaises(ContractError) as error:
            GroupingPlan.from_json(json.dumps(data).encode())
        self.assertNotIn("synthetic-private-error-marker", str(error.exception))
        with self.assertRaises(ContractError):
            replace(good, revision=True)
        with patch.object(overrides, "MAX_PLAN_BYTES", 1), self.assertRaises(ContractError):
            good.to_json()
        with patch.object(overrides, "MAX_DECISIONS", 0), self.assertRaises(ContractError):
            plan(merge)

    def test_empty_committed_example_is_inert_and_references_are_not_authority(self):
        root = Path(__file__).resolve().parents[2]
        empty = GroupingPlan.from_json((root / "config/overrides/empty.json").read_bytes())
        self.assertEqual(empty.decisions, ())
        for ref in (
            "../private",
            "https://example.com/?token=private",
            "https://127.0.0.1/",
            "https://example.com/?contact=private",
        ):
            with self.assertRaises(ContractError):
                replace(decision("merge", self.items[:2]), evidence_ref=ref)

    def test_private_reload_snapshot_restart_and_replay_preserve_decisions_and_items(self):
        current = plan(decision("split", self.items, partitions=(("a",), ("b", "c"))))
        with tempfile.TemporaryDirectory(prefix="wrap-brief-overrides-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            path = root / "current.json"
            path.write_bytes(current.to_json())
            path.chmod(0o600)
            first = grouped(self.items, current)
            state = Snapshot(AT, SOURCES, self.items, first)
            LocalState(root / "state.sqlite3").commit(state, expected_revision=0)
            restored = LocalState(root / "state.sqlite3").load().snapshot
            replay = grouped(
                restored.items,
                GroupingPlan.from_json(path.read_bytes()),
                previous=restored.clusters,
            )
            self.assertEqual(replay, first)
            self.assertEqual(
                tuple(value.to_dict() for value in self.items),
                tuple(
                    value.to_dict() for value in sorted(restored.items, key=lambda value: value.id)
                ),
            )

    def test_raw_manual_output_remains_rejected_by_editorial_boundary(self):
        current = plan(decision("merge", self.items[:2]))
        manual = grouped(self.items, current)
        claims = tuple(
            ClaimEvidence(
                "claim-" + value.id,
                value.source_id,
                value.id,
                "reported",
                metadata_reference(value),
                AT,
                "content/corrections/synthetic-review.md#claim",
            )
            for value in self.items
        )
        batch = apply_controls(
            Snapshot(AT, SOURCES, self.items),
            ledger=ControlLedger("current", 1, AT, claims),
            observed_at=AT,
        )
        with self.assertRaises(ContractError):
            batch.finish(clusters=manual)

    def test_adapter_has_no_network_or_asset_io(self):
        with (
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(Path, "read_bytes", side_effect=AssertionError("filesystem")),
        ):
            self.assertEqual(len(grouped(self.items, plan(decision("merge", self.items[:2])))), 2)
