"""Regression tests for public progress, dependency gates and evidence checks."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("plan", ROOT / "tools/plan.py")
plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / plan.BACKLOG).read_text())

    def invalid(self, change, message):
        change(self.data)
        with self.assertRaisesRegex(ValueError, message):
            plan.validate(self.data, ROOT)

    def test_current_plan_valid(self):
        plan.validate(self.data, ROOT)

    def test_duplicate_task(self):
        self.invalid(lambda d: d["tasks"].append(copy.deepcopy(d["tasks"][0])), "duplicate task")

    def test_missing_dependency(self):
        self.invalid(
            lambda d: d["tasks"][1]["depends_on"].append("T99.99"), "missing/self dependency"
        )

    def test_self_dependency(self):
        self.invalid(
            lambda d: d["tasks"][1]["depends_on"].append(d["tasks"][1]["id"]),
            "missing/self dependency",
        )

    def test_cycle_in_disabled_scope(self):
        def change(d):
            future = [t for t in d["tasks"] if t["scope"] == "future"]
            future[0]["depends_on"].append(future[1]["id"])
            future[1]["depends_on"].append(future[0]["id"])

        self.invalid(change, "dependency cycle")

    def test_disabled_scope_cannot_block_mvp(self):
        self.invalid(
            lambda d: d["tasks"][1]["depends_on"].append("T10.01"), "later scope blocks MVP"
        )

    def test_wrong_parent(self):
        self.invalid(lambda d: d["tasks"][1].update(epic="E02"), "invalid parent")

    def test_duplicate_subtask(self):
        self.invalid(
            lambda d: d["tasks"][0]["subtasks"].append(copy.deepcopy(d["tasks"][0]["subtasks"][0])),
            "duplicate subtask",
        )

    def test_invalid_subtask_parent(self):
        self.invalid(
            lambda d: d["tasks"][0]["subtasks"][0].update(id="T01.01.1"), "invalid subtask ID"
        )

    def test_block_reason_required(self):
        self.invalid(lambda d: d["tasks"][1].update(status="blocked"), "reason required")

    def test_active_dependency_required(self):
        planning = self.data["tasks"][0]
        planning.update(
            status="in_progress", completion={"evidence": [], "checks": [], "review": None}
        )
        for subtask in planning["subtasks"]:
            subtask.update(status="not_started", evidence=[])
        self.invalid(lambda d: d["tasks"][1].update(status="in_progress"), "unfinished dependency")

    def test_activation_gate_required(self):
        self.invalid(
            lambda d: d["project"]["enabled_scopes"].append("growth"), "incomplete activation gate"
        )

    def test_parallel_limit(self):
        self.invalid(lambda d: d["project"].update(max_parallel_lanes=3), "parallel lane limit")

    def test_done_requires_subtasks(self):
        self.data["tasks"][0]["subtasks"][0]["status"] = "not_started"
        self.invalid(lambda d: d["tasks"][0].update(status="done"), "unfinished subtask")

    def completed_planning(self):
        task = self.data["tasks"][0]
        evidence = "docs/plan/schema.md"
        task["status"] = "done"
        for subtask in task["subtasks"]:
            subtask.update(status="done", evidence=[evidence])
        task["completion"] = dict(
            evidence=[evidence],
            checks=[dict(name=n, result="pass", evidence=evidence) for n in task["verification"]],
            review=dict(result="pass", evidence=evidence),
        )
        return task

    def test_complete_task_consistency(self):
        self.completed_planning()
        plan.validate(self.data, ROOT)

    def test_done_requires_evidence(self):
        task = self.completed_planning()
        task["completion"]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "evidence required"):
            plan.validate(self.data, ROOT)

    def test_done_requires_named_checks(self):
        task = self.completed_planning()
        task["completion"]["checks"].pop()
        with self.assertRaisesRegex(ValueError, "check coverage mismatch"):
            plan.validate(self.data, ROOT)

    def test_failed_check_prevents_done(self):
        task = self.completed_planning()
        task["completion"]["checks"][0]["result"] = "fail"
        with self.assertRaisesRegex(ValueError, "failed verification"):
            plan.validate(self.data, ROOT)

    def test_done_requires_passing_review(self):
        task = self.completed_planning()
        task["completion"]["review"] = None
        with self.assertRaisesRegex(ValueError, "passing review required"):
            plan.validate(self.data, ROOT)

    def test_malformed_check_record_is_rejected(self):
        task = self.completed_planning()
        task["completion"]["checks"][0] = "not a check object"
        with self.assertRaisesRegex(ValueError, "invalid check record"):
            plan.validate(self.data, ROOT)

    def test_malformed_review_record_is_rejected(self):
        task = self.completed_planning()
        task["completion"]["review"] = "not a review object"
        with self.assertRaisesRegex(ValueError, "passing review required"):
            plan.validate(self.data, ROOT)

    def test_ignored_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "result.txt"
            path.write_text("private output")
            with patch.object(plan, "project_files", return_value=[]):
                with self.assertRaisesRegex(ValueError, "not a public publication candidate"):
                    plan.public_file(root, "result.txt", evidence=True)

    def test_sensitive_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "result.pem"
            path.write_text("private output")
            with self.assertRaisesRegex(ValueError, "sensitive evidence file"):
                plan.public_file(root, "result.pem", evidence=True)

    def test_symlink_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "result.txt").write_text("output")
            (root / "link.txt").symlink_to("result.txt")
            with self.assertRaisesRegex(ValueError, "symlink evidence"):
                plan.public_file(root, "link.txt", evidence=True)

    def test_generated_progress_is_not_evidence(self):
        with self.assertRaisesRegex(ValueError, "not completion evidence"):
            plan.public_file(ROOT, "docs/plan/STATUS.md", evidence=True)

    def test_absolute_and_traversal_evidence_rejected(self):
        for path in ("/etc/passwd", "../outside.md"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "unsafe path"):
                plan.public_file(ROOT, path, evidence=True)

    def test_missing_evidence_file(self):
        with self.assertRaisesRegex(ValueError, "missing file"):
            plan.public_file(ROOT, "docs/not-there.md", evidence=True)

    def test_ready_excludes_disabled_and_blocked(self):
        self.completed_planning()
        ready_ids = {t["id"] for t in plan.ready(self.data)}
        self.assertEqual(ready_ids, {"T01.01", "T01.02", "T01.04", "T02.04"})
        self.data["tasks"][1].update(status="blocked", block_reason="test gate")
        self.assertNotIn("T01.01", {t["id"] for t in plan.ready(self.data)})

    def test_ready_never_includes_canceled_dependency(self):
        self.data["tasks"][0].update(status="canceled", block_reason="test cancellation")
        self.assertEqual(plan.ready(self.data), [])

    def test_progress_separates_planning_and_product(self):
        self.completed_planning()
        text = plan.render_status(self.data)
        self.assertIn("| planning | yes | 1/1 (100%)", text)
        self.assertIn("| mvp | yes | 0/", text)
        self.assertIn("| revenue | no |", text)

    def test_canceled_denominator(self):
        self.assertIn("No committed tasks", plan.count([dict(status="canceled")]))

    def test_render_is_deterministic(self):
        self.assertEqual(plan.generated(self.data), plan.generated(copy.deepcopy(self.data)))

    def test_portfolio_is_not_automatically_done(self):
        self.assertFalse(plan.milestone_done(self.data, "M5"))

    def test_primary_gate_membership_must_match(self):
        self.invalid(lambda d: d["tasks"][1].update(milestone="M1"), "membership mismatch")

    def test_milestone_dependencies_are_acyclic(self):
        self.invalid(
            lambda d: d["milestones"][0].update(depends_on=["M2"]), "milestone dependency cycle"
        )

    def test_milestone_waits_for_predecessor(self):
        for task in self.data["tasks"]:
            if task["milestone"] == "M2":
                task["status"] = "done"
        self.assertFalse(plan.milestone_done(self.data, "M2"))

    def test_optional_tasks_do_not_become_release_requirements(self):
        optional = next(t for t in self.data["tasks"] if t["id"] == "T10.05")
        self.assertFalse(optional["gate_required"])
        milestone = next(m for m in self.data["milestones"] if m["id"] == "M4")
        self.assertNotIn(optional["id"], milestone["tasks"])
        milestone["tasks"].append(optional["id"])
        with self.assertRaisesRegex(ValueError, "membership mismatch"):
            plan.validate(self.data, ROOT)

    def test_non_done_task_cannot_keep_completion_claims(self):
        task = self.data["tasks"][1]
        task["completion"]["evidence"] = ["docs/plan/schema.md"]
        with self.assertRaisesRegex(ValueError, "stale completion claims"):
            plan.validate(self.data, ROOT)

    def test_invalid_subtask_shapes(self):
        for field, value in (("title", 1), ("done_when", {}), ("evidence", "not a list")):
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data["tasks"][1]["subtasks"][0][field] = value
                with self.assertRaises(ValueError):
                    plan.validate(data, ROOT)

    def test_active_subtask_needs_active_parent(self):
        self.invalid(
            lambda d: d["tasks"][1]["subtasks"][0].update(status="in_progress"),
            "inconsistent parent status",
        )

    def test_unfinished_subtask_cannot_keep_done_evidence(self):
        self.invalid(
            lambda d: d["tasks"][1]["subtasks"][0].update(evidence=["README.md"]),
            "unfinished subtask",
        )

    def test_stale_block_reason_rejected(self):
        self.invalid(lambda d: d["tasks"][1].update(block_reason="old reason"), "stale block")

    def test_invalid_dates_and_boolean_lane_limit(self):
        for field, value in (
            ("updated", "2026-02-30"),
            ("updated", 1),
            ("max_parallel_lanes", True),
        ):
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(self.data)
                data["project"][field] = value
                with self.assertRaises(ValueError):
                    plan.validate(data, ROOT)

    def test_unhashable_dependencies_report_validation_error(self):
        self.invalid(lambda d: d["tasks"][1].update(depends_on=[{}]), "invalid text entry")

    def test_generated_evidence_cannot_bypass_with_normalized_path(self):
        with self.assertRaisesRegex(ValueError, "not completion evidence"):
            plan.public_file(ROOT, "docs/plan/./STATUS.md", evidence=True)

    def test_validation_collects_public_candidates_once(self):
        with patch.object(plan, "project_files", wraps=plan.project_files) as files:
            plan.validate(self.data, ROOT)
            self.assertEqual(files.call_count, 1)

    def test_publication_accepts_binary_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "icon.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n\xff")
            with patch.object(plan, "project_files", return_value=[path]):
                plan.check_publication(root)

    def test_binary_asset_does_not_hide_ascii_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "icon.png"
            path.write_bytes(b"\xff" + b"ghp_" + b"a" * 30)
            with patch.object(plan, "project_files", return_value=[path]):
                with self.assertRaisesRegex(ValueError, "possible private material"):
                    plan.check_publication(root)

    def test_publication_rejects_private_and_token_material(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "public.txt"
            path.write_text("ghp_" + "a" * 30)
            with patch.object(plan, "project_files", return_value=[path]):
                with self.assertRaisesRegex(ValueError, "possible private material"):
                    plan.check_publication(root)

    def test_publication_rejects_broken_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "public.md"
            path.write_text("[missing](absent.md)")
            with patch.object(plan, "project_files", return_value=[path]):
                with self.assertRaisesRegex(ValueError, "broken link"):
                    plan.check_publication(root)

    def test_publication_rejects_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / ".env"
            path.write_text("placeholder")
            with patch.object(plan, "project_files", return_value=[path]):
                with self.assertRaisesRegex(ValueError, "private tracked path"):
                    plan.check_publication(root)


if __name__ == "__main__":
    unittest.main()
