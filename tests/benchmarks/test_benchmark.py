from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from benchmarks.support import FIXTURE, MAX_BYTES, load_fixture, parse_fixture
from tools import check_security
from wrap_brief.grouping import benchmark
from wrap_brief.grouping.benchmark import CATEGORIES, GoldScenario, PairCounts, evaluate
from wrap_brief.grouping.stories import LeadEvidence, group_items
from wrap_brief.models import ContractError, Item, Source
from wrap_brief.state.snapshot import Snapshot

AT = datetime(2026, 1, 4, 12, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[2]
FROZEN_REF = "f2e3ea734a6d36aed33c161f29c06656a890030d906b121d8c1b2a2661b4c296"


def scenario(name="fictional-matrix", *, titles=None, parts=(("a", "d"), ("b", "c"))):
    titles = titles or ("Fictional citrine game update announced",) * 3 + (
        "Fictional citrine game review",
    )
    sources, items, ids = [], [], {}
    for key, title in zip(("a", "b", "c", "d"), titles, strict=True):
        source_id = "sample-" + key
        sources.append(
            Source(
                source_id,
                "Fictional source " + key,
                "https://example.com/",
                f"https://example.com/feeds/{key}",
                ("example.com",),
                "Hand-authored measurement fixture",
            )
        )
        ids[key] = name + "-" + key
        items.append(
            Item(
                ids[key],
                source_id,
                title,
                f"https://example.com/{name}/{key}",
                AT,
                AT,
                published_at=AT - timedelta(hours=1),
            )
        )
    return GoldScenario(
        name,
        "ambiguity",
        Snapshot(AT, tuple(sources), tuple(items)),
        tuple(LeadEvidence(item.id) for item in items),
        tuple(tuple(ids[key] for key in part) for part in parts),
        "Artificial confusion-matrix contract, not real-event accuracy evidence.",
        "tests/benchmarks/README.md#labels",
        AT,
    )


class BenchmarkTests(unittest.TestCase):
    def test_frozen_synthetic_corpus_is_exhaustive_mixed_and_never_qualifies_real_gate(self):
        raw = FIXTURE.read_bytes()
        self.assertLess(len(raw), MAX_BYTES)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), FROZEN_REF)
        at, values = load_fixture()
        self.assertEqual(len(values), 12)
        self.assertEqual({value.category for value in values}, CATEGORIES)
        self.assertEqual(sum(len(value.snapshot.items) for value in values), 60)
        self.assertEqual(sum(len(value.gold_groups) for value in values), 24)
        self.assertTrue(all(len(value.snapshot.items) == 5 for value in values))
        self.assertTrue(
            all(
                not source.enabled and source.allowed_hosts == ("example.com",)
                for value in values
                for source in value.snapshot.sources
            )
        )
        report = evaluate(values, dataset_kind="synthetic", observed_at=at)
        self.assertEqual(report.counts.pairs, 120)
        self.assertEqual(report.counts.tp + report.counts.fn, 48)
        self.assertEqual(report.counts.fp + report.counts.tn, 72)
        self.assertEqual(report.summary()["real_corpus_qualification"], "not_assessed")
        self.assertFalse(report.counts.numeric_target_met)
        self.assertIsNone(report.counts.precision)
        self.assertEqual(
            (report.counts.tp, report.counts.fp, report.counts.fn, report.counts.tn), (0, 0, 48, 72)
        )

    def test_actual_complete_batch_scoring_counts_collateral_false_merges(self):
        value = scenario()
        with patch.object(benchmark, "group_items", wraps=group_items) as grouping:
            report = evaluate((value,), dataset_kind="synthetic", observed_at=AT)
        self.assertEqual(grouping.call_count, 1)
        self.assertEqual(len(grouping.call_args.args[0]), 4)
        self.assertNotIn("previous_clusters", grouping.call_args.kwargs)
        self.assertEqual(report.counts, PairCounts(tp=1, fp=2, fn=1, tn=2))
        self.assertAlmostEqual(report.counts.precision, 1 / 3)
        self.assertEqual(report.counts.recall, 0.5)
        self.assertEqual(len(report.false_merges), 2)
        self.assertEqual(report.categories[0][0], "ambiguity")

    def test_zero_predictions_and_no_positive_labels_have_undefined_denominators(self):
        titles = (
            "Fictional citrine game announced",
            "Fictional citrine game review",
            "Fictional citrine game preview",
            "Fictional citrine game delayed",
        )
        report = evaluate((scenario(titles=titles),), dataset_kind="synthetic", observed_at=AT)
        self.assertIsNone(report.counts.precision)
        self.assertEqual(report.counts.recall, 0)
        self.assertFalse(report.counts.numeric_target_met)
        none = scenario(titles=titles, parts=(("a",), ("b",), ("c",), ("d",)))
        report = evaluate((none,), dataset_kind="synthetic", observed_at=AT)
        self.assertIsNone(report.counts.recall)
        self.assertIsNone(report.counts.precision)
        self.assertIn(b'"precision":null', report.to_json())
        self.assertNotIn(b"NaN", report.to_json())

    def test_numeric_target_uses_exact_denominators_and_is_not_a_qualification(self):
        self.assertTrue(PairCounts(tp=98, fp=2).numeric_target_met)
        self.assertFalse(PairCounts(tp=97, fp=3).numeric_target_met)
        self.assertFalse(PairCounts(tp=49, fp=1).numeric_target_met)
        self.assertFalse(PairCounts(tn=100).numeric_target_met)
        for changes in ({"tp": True}, {"fn": -1}, {"tn": benchmark.MAX_PAIRS + 1}):
            with self.assertRaises(ContractError):
                PairCounts(**changes)
        self.assertEqual(
            evaluate((scenario(),), dataset_kind="private_evaluation", observed_at=AT).summary()[
                "real_corpus_qualification"
            ],
            "not_assessed",
        )

    def test_scenario_and_item_order_are_deterministic_without_cross_scenario_inflation(self):
        a, b = scenario("family-a"), scenario("family-b")
        first = evaluate((a, b), dataset_kind="synthetic", observed_at=AT)
        changed = replace(
            a,
            snapshot=replace(a.snapshot, items=tuple(reversed(a.snapshot.items))),
            gold_groups=tuple(reversed(a.gold_groups)),
            lead_evidence=tuple(reversed(a.lead_evidence)),
        )
        self.assertEqual(
            evaluate((b, changed), dataset_kind="synthetic", observed_at=AT).to_json(),
            first.to_json(),
        )
        self.assertEqual(first.counts.pairs, 12)
        self.assertEqual(first.scenario_count, 2)
        self.assertEqual(first.gold_group_count, 4)
        with self.assertRaisesRegex(ContractError, "reused item"):
            evaluate(
                (a, replace(a, id="duplicate-family")), dataset_kind="synthetic", observed_at=AT
            )

    def test_public_summary_excludes_private_pair_identifiers_metadata_and_label_details(self):
        value = scenario("private-scenario-marker")
        report = evaluate((value,), dataset_kind="private_evaluation", observed_at=AT)
        self.assertTrue(report.false_merges)
        for marker in (
            b"private-scenario-marker",
            b"Fictional citrine",
            b"https://example.com",
            b"Artificial confusion",
            b"tests/benchmarks",
        ):
            self.assertNotIn(marker, report.to_json())
        self.assertNotIn("private-scenario-marker", repr(report))
        with self.assertRaises(FrozenInstanceError):
            report.dataset_kind = "synthetic"

    def test_gold_partition_evidence_clock_and_record_shape_are_strict(self):
        value = scenario()
        for parts in (
            value.gold_groups[:-1],
            (value.gold_groups[0], value.gold_groups[0]),
            (("unknown",),),
        ):
            with self.assertRaises(ContractError):
                replace(value, gold_groups=parts)
        with self.assertRaises(ContractError):
            replace(value, lead_evidence=value.lead_evidence[:-1])
        with self.assertRaises(ContractError):
            replace(value, reviewed_at=AT - timedelta(seconds=1))
        with self.assertRaises(ContractError):
            replace(value, category="private-category")
        with self.assertRaises(ContractError):
            replace(value, schema_version=True)
        with self.assertRaises(ContractError):
            replace(value, labeling_ref="https://example.com/?contact=private")
        with self.assertRaises(ContractError):
            evaluate((value,), dataset_kind="synthetic", observed_at=AT - timedelta(seconds=1))
        with self.assertRaises(ContractError):
            evaluate((value, value), dataset_kind="synthetic", observed_at=AT)

    def test_corpus_size_and_pair_limits_fail_before_grouping(self):
        value = scenario()
        for field, limit in (("MAX_SCENARIOS", 0), ("MAX_PAIRS", 0), ("MAX_CORPUS_BYTES", 1)):
            with (
                patch.object(benchmark, field, limit),
                patch.object(benchmark, "group_items") as grouping,
                self.assertRaises(ContractError),
            ):
                evaluate((value,), dataset_kind="synthetic", observed_at=AT)
            grouping.assert_not_called()
        with patch.object(benchmark, "MAX_SCENARIO_ITEMS", 1), self.assertRaises(ContractError):
            replace(value)

    def test_fixture_recipe_unknown_duplicate_nonfinite_and_non_synthetic_data_are_rejected(self):
        raw = FIXTURE.read_bytes()
        for data in (b'{"id":1,"id":1}', b'{"observed_at":NaN}', b"x" * (MAX_BYTES + 1)):
            with self.assertRaises(ContractError):
                parse_fixture(data)
        base = json.loads(raw)
        for change in ("kind", "extra", "row", "unknown-gold", "duplicate-row"):
            data = copy.deepcopy(base)
            if change == "kind":
                data["kind"] = "real-and-approved"
            if change == "extra":
                data["approved"] = True
            if change == "row":
                data["scenarios"][0]["items"][0]["private_note"] = "not allowed"
            if change == "unknown-gold":
                data["scenarios"][0]["gold_groups"][0][0] = "unknown"
            if change == "duplicate-row":
                data["scenarios"][0]["items"][1]["id"] = "a"
            with self.subTest(change=change), self.assertRaises(ContractError):
                parse_fixture(json.dumps(data).encode())

    def test_evaluation_does_not_fetch_read_or_choose_system_time(self):
        value = scenario()
        with (
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(Path, "read_bytes", side_effect=AssertionError("filesystem")),
        ):
            self.assertEqual(
                evaluate((value,), dataset_kind="synthetic", observed_at=AT).counts.pairs, 6
            )

    def test_fixed_fixture_measurement_command_reports_score_not_gold_success(self):
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(ROOT / "tools/measure_grouping_fixture.py")],
            capture_output=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        data = json.loads(result.stdout)
        self.assertEqual(data["dataset_kind"], "synthetic")
        self.assertEqual(data["real_corpus_qualification"], "not_assessed")
        self.assertFalse(data["numeric_target_met"])
        self.assertIsNone(data["counts"]["precision"])
        self.assertLess(len(result.stdout), 8_192)

    @unittest.skipUnless(
        os.environ.get("WRAP_BRIEF_GITLEAKS"), "explicit checksum-verified scanner required"
    )
    def test_new_public_aggregate_report_is_scanned_without_private_diagnostics(self):
        at, values = load_fixture()
        report = evaluate(values, dataset_kind="synthetic", observed_at=at)
        with tempfile.TemporaryDirectory(prefix="wrap-brief-benchmark-public-") as temporary:
            root = Path(temporary).resolve()
            public, policy = root / "public", root / "policy"
            public.mkdir()
            policy.mkdir()
            (public / "measurement.json").write_bytes(report.to_json())
            self.assertEqual({path.name for path in public.iterdir()}, {"measurement.json"})
            check_security.scan(
                Path(os.environ["WRAP_BRIEF_GITLEAKS"]).absolute(), "dir", public, policy
            )
