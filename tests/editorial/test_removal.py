from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from editorial.support import (
    GUID_MARKER,
    HEADER_MARKER,
    PUBLIC_REF,
    TITLE_MARKER,
    URL_MARKER,
    finish,
    fixture,
    ledger_for,
    reviewed,
)
from tools import check_security
from wrap_brief.editorial.controls import (
    ControlLedger,
    CorrectionControl,
    apply_controls,
    metadata_reference,
)
from wrap_brief.editorial.removal import SURFACES, RemovalReport, SurfaceRemoval
from wrap_brief.ingest.http import FetchResult
from wrap_brief.ingest.polling import SourcePoll, reduce_polls
from wrap_brief.models import ContractError
from wrap_brief.render.digest import render_editorial
from wrap_brief.state.local import LocalState
from wrap_brief.state.snapshot import Snapshot

ROOT = Path(__file__).resolve().parents[2]
MARKERS = tuple(value.encode() for value in (TITLE_MARKER, URL_MARKER, GUID_MARKER, HEADER_MARKER))


def owned_file(path: Path, data: bytes) -> None:
    """Only called with newly created test-owned paths, never caller-supplied locations."""
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as stream:
        stream.write(data)


def contains_withdrawn(path: Path) -> bool:
    return path.exists() and any(marker in path.read_bytes() for marker in MARKERS)


def public_files(result) -> dict[str, bytes]:
    """Synthetic JSON/RSS drill fixtures, not new product export/feed APIs."""
    items = [item for item in result.snapshot.items if item.status in {"active", "corrected"}]
    json_data = json.dumps(
        [{"title": item.title, "url": item.url, "claim": item.claim_status} for item in items],
        sort_keys=True,
    ).encode()
    root = Element("rss", version="2.0")
    channel = SubElement(root, "channel")
    for item in items:
        entry = SubElement(channel, "item")
        SubElement(entry, "title").text = item.title
        SubElement(entry, "link").text = item.url
    return {
        "index.html": render_editorial(result).encode(),
        "data.json": json_data,
        "feed.xml": tostring(root),
    }


def polled(snapshot, at, *, changed=False):
    title = TITLE_MARKER + (" updated" if changed else "")
    url = URL_MARKER + ("-new-url" if changed else "")
    feed = (
        f"<rss><channel><item><title>{title}</title><link>{url}</link>"
        f"<guid>{GUID_MARKER}</guid><pubDate>2026-01-02T12:00:00Z</pubDate>"
        "</item></channel></rss>"
    ).encode()
    batch = reduce_polls(
        snapshot,
        (SourcePoll("demo-a", FetchResult("ok", 1, body=feed)),),
        expected_source_ids=("demo-a",),
        observed_at=at,
    )
    batch.require_publishable()  # Current poll health is separate from editorial authority.
    return Snapshot(
        batch.observed_at,
        snapshot.sources,
        batch.items,
        checkpoints=batch.checkpoints,
        tombstones=snapshot.tombstones,
        kind=snapshot.kind,
    )


class RemovalTests(unittest.TestCase):
    def setUp(self):
        self.state = fixture()
        self.at = self.state.observed_at
        self.item = next(item for item in self.state.items if item.source_id == "demo-a")

    def remedy(self, action="exclude_source"):
        return CorrectionControl(
            "synthetic-source-request",
            "demo-a",
            action,
            self.at + timedelta(minutes=1),
            item_id=None if action == "exclude_source" else self.item.id,
            public_notice_ref=PUBLIC_REF + "#retraction" if action == "retract" else None,
        )

    def test_owned_physical_source_removal_covers_all_eight_surfaces_restart_replay_and_restore(
        self,
    ):
        # This entire inventory is newly created synthetic data; nothing user-authored is selected.
        with tempfile.TemporaryDirectory(prefix="wrap-brief-removal-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            for name in ("private", "public", "artifacts", "cache", "trusted"):
                (root / name).mkdir(mode=0o700)
            initial = reviewed(self.state)
            db = root / "private/state.sqlite3"
            store = LocalState(db)
            initial_revision = store.commit(initial.snapshot, expected_revision=0)
            export = root / "private/export.json"
            backup = root / "private/backup.sqlite3"
            owned_file(export, initial.snapshot.to_json())
            owned_file(backup, db.read_bytes())
            self.assertEqual(LocalState(backup).load().snapshot.digest, initial.snapshot.digest)
            old_files = public_files(initial)
            for name, data in old_files.items():
                owned_file(root / "public" / name, data)
                owned_file(root / "artifacts" / name, data)
                owned_file(root / "cache" / name, data)
            keep = root / "artifacts/unrelated-owned.txt"
            owned_file(keep, b"unrelated synthetic owned data survives")
            inventory = {
                "private_records": (db,),
                "private_exports": (export,),
                "private_backups": (backup,),
                "public_html": (root / "public/index.html",),
                "public_json": (root / "public/data.json",),
                "public_rss": (root / "public/feed.xml",),
                "deployment_artifacts": tuple(root / "artifacts" / name for name in old_files),
                "owned_caches": tuple(root / "cache" / name for name in old_files),
            }
            before = {
                surface: sum(contains_withdrawn(path) for path in paths)
                for surface, paths in inventory.items()
            }
            self.assertEqual(set(before), SURFACES)
            self.assertTrue(all(count > 0 for count in before.values()))
            remedy = self.remedy()
            ledger = ledger_for(self.state, controls=(remedy,), at=remedy.reviewed_at)
            current_ledger = root / "trusted/current.json"
            owned_file(current_ledger, ledger.to_json())
            controlled = reviewed(self.state, ledger, remedy.reviewed_at)
            store.commit(controlled.snapshot, expected_revision=initial_revision.version)
            # Only exact files in the newly owned inventory are removed/rebuilt.
            export.unlink()
            backup.unlink()
            for name, data in public_files(controlled).items():
                (root / "public" / name).write_bytes(data)
            for path in (*inventory["deployment_artifacts"], *inventory["owned_caches"]):
                path.unlink()
            after = {
                surface: sum(contains_withdrawn(path) for path in paths)
                for surface, paths in inventory.items()
            }
            self.assertEqual(set(after.values()), {0})
            self.assertEqual(keep.read_bytes(), b"unrelated synthetic owned data survives")
            self.assertIn(
                b"Unrelated hand-authored coverage survives",
                (root / "public/index.html").read_bytes(),
            )
            self.assertEqual(
                {path.name for path in (root / "private").iterdir()}, {"state.sqlite3"}
            )
            # Inspect actual main-database bytes and every extant owned file, not just logical receipts.
            for path in root.rglob("*"):
                if path.is_file():
                    self.assertFalse(contains_withdrawn(path))
            reloaded = ControlLedger.from_json(current_ledger.read_bytes())
            for changed in (False, True):
                at = self.at + timedelta(hours=1 + int(changed))
                incoming = polled(
                    self.state, at, changed=changed
                )  # Deliberately stale pre-removal input.
                output = finish(apply_controls(incoming, ledger=reloaded, observed_at=at))
                self.assertFalse(any(item.source_id == "demo-a" for item in output.snapshot.items))
                restarted = LocalState(db)
                head = restarted.load()
                restarted.commit(output.snapshot, expected_revision=head.version)
                self.assertFalse(contains_withdrawn(db))
            # Restore through current controls using the current CAS version, not the old version.
            restarted = LocalState(db)
            current = restarted.load()
            restored = reviewed(self.state, reloaded, self.at + timedelta(hours=3))
            committed = restarted.commit(restored.snapshot, expected_revision=current.version)
            self.assertGreater(committed.version, initial_revision.version)
            self.assertFalse(
                any(item.source_id == "demo-a" for item in LocalState(db).load().snapshot.items)
            )
            self.assertFalse(contains_withdrawn(db))
            report = RemovalReport(
                "synthetic-owned-remedy",
                "owned_synthetic_sandbox",
                self.at + timedelta(hours=3),
                tuple(
                    SurfaceRemoval(
                        surface,
                        "removed",
                        before[surface],
                        after[surface],
                        self.at + timedelta(hours=3),
                        PUBLIC_REF + "#removal",
                    )
                    for surface in sorted(SURFACES)
                ),
            )
            report.require_resolved()
            self.assertTrue(report.resolved)
            self.assertEqual(RemovalReport.from_json(report.to_json()), report)
            self.assertNotIn(TITLE_MARKER.encode(), report.to_json())
            self.assertNotIn(str(root).encode(), report.to_json())

    def test_item_erasure_tombstone_and_retraction_survive_independent_poll_and_restart(self):
        for action in ("erase_item", "retract"):
            with (
                self.subTest(action=action),
                tempfile.TemporaryDirectory(prefix="wrap-brief-replay-") as temporary,
            ):
                root = Path(temporary).resolve()
                root.chmod(0o700)
                remedy = self.remedy(action)
                ledger = ledger_for(self.state, controls=(remedy,), at=remedy.reviewed_at)
                current_path = root / "current.json"
                owned_file(current_path, ledger.to_json())
                first = reviewed(self.state, ledger, remedy.reviewed_at)
                store = LocalState(root / "state.sqlite3")
                store.commit(first.snapshot, expected_revision=0)
                head = LocalState(root / "state.sqlite3").load()
                incoming = polled(head.snapshot, self.at + timedelta(hours=1))
                result = reviewed(
                    incoming,
                    ControlLedger.from_json(current_path.read_bytes()),
                    incoming.observed_at,
                )
                if action == "erase_item":
                    self.assertNotIn(self.item.id, {item.id for item in result.snapshot.items})
                    self.assertIn(
                        self.item.id, {value.item_id for value in result.snapshot.tombstones}
                    )
                else:
                    self.assertEqual(
                        next(
                            item for item in result.snapshot.items if item.id == self.item.id
                        ).status,
                        "retracted",
                    )
                self.assertNotIn(TITLE_MARKER, render_editorial(result))
                # Same URL, changed claim metadata, and a restored old state remain suppressed.
                changed = polled(self.state, self.at + timedelta(hours=2))
                changed = replace(
                    changed,
                    items=tuple(
                        replace(item, title="New withdrawn claim")
                        if item.id == self.item.id
                        else item
                        for item in changed.items
                    ),
                )
                self.assertNotIn(
                    "New withdrawn claim",
                    render_editorial(reviewed(changed, ledger, changed.observed_at)),
                )

    def test_raw_current_revision_cas_is_not_semantic_erasure_but_current_controls_restore_it(self):
        with tempfile.TemporaryDirectory(prefix="wrap-brief-cas-negative-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            db = root / "state.sqlite3"
            store = LocalState(db)
            store.commit(self.state, expected_revision=0)
            remedy = self.remedy()
            ledger = ledger_for(self.state, controls=(remedy,), at=remedy.reviewed_at)
            removed = reviewed(self.state, ledger, remedy.reviewed_at)
            current = store.commit(removed.snapshot, expected_revision=store.load().version)
            unsafe = store.commit(self.state, expected_revision=current.version)
            self.assertIn(self.item.id, {item.id for item in unsafe.snapshot.items})
            self.assertTrue(contains_withdrawn(db))
            safe = reviewed(unsafe.snapshot, ledger, self.at + timedelta(hours=1))
            store.commit(safe.snapshot, expected_revision=unsafe.version)
            self.assertFalse(contains_withdrawn(db))

    def outcomes(self, status="not_configured"):
        return tuple(
            SurfaceRemoval(
                surface,
                status,
                0 if status == "not_configured" else 1,
                0,
                self.at,
                PUBLIC_REF + "#removal",
            )
            for surface in sorted(SURFACES)
        )

    def test_reports_distinguish_genuinely_unconfigured_pending_and_failed_surfaces(self):
        # A newly owned empty directory stands for an absent service, not deleted content.
        with tempfile.TemporaryDirectory(prefix="wrap-brief-unconfigured-") as temporary:
            self.assertEqual(list(Path(temporary).iterdir()), [])
            absent = RemovalReport("absent", "operator_reported", self.at, self.outcomes())
            self.assertTrue(absent.resolved)
            self.assertTrue(all(value.status == "not_configured" for value in absent.outcomes))
        for status in ("pending", "failed"):
            outcomes = list(self.outcomes("removed"))
            outcomes[0] = replace(outcomes[0], status=status)
            report = RemovalReport("incomplete", "operator_reported", self.at, tuple(outcomes))
            self.assertFalse(report.resolved)
            with self.assertRaises(ContractError):
                report.require_resolved()

    def test_report_schemas_require_exact_coverage_counts_times_and_safe_references(self):
        good = RemovalReport("good", "owned_synthetic_sandbox", self.at, self.outcomes("removed"))
        for outcomes in (good.outcomes[:-1], (good.outcomes[0],) * len(SURFACES)):
            with self.assertRaises(ContractError):
                replace(good, outcomes=outcomes)
        value = good.outcomes[0]
        for changes in (
            {"matched_before": True},
            {"remaining": -1},
            {"matched_before": 0},
            {"status": "not_configured"},
            {"status": "purged"},
            {"evidence_ref": "private/contacts.md"},
            {"schema_version": True},
        ):
            with self.assertRaises(ContractError):
                replace(value, **changes)
        with self.assertRaises(ContractError):
            replace(good, checked_at=self.at - timedelta(seconds=1))
        for data in (b'{"id":"x","id":"x"}', b'{"id":NaN}', good.to_json()[:-1], b"x" * 32_769):
            with self.assertRaises(ContractError):
                RemovalReport.from_json(data)
        raw = json.loads(good.to_json())
        raw["private_request"] = "not permitted"
        with self.assertRaises(ContractError):
            RemovalReport.from_json(json.dumps(raw).encode())

    def test_unremoved_owned_copy_stays_pending_or_failed_and_never_resolves(self):
        with tempfile.TemporaryDirectory(prefix="wrap-brief-removal-failure-") as temporary:
            path = Path(temporary).resolve() / "owned-retained-copy.html"
            owned_file(path, TITLE_MARKER.encode())
            self.assertTrue(contains_withdrawn(path))
            for status in ("pending", "failed"):
                outcomes = list(self.outcomes())
                outcomes = [
                    SurfaceRemoval(value.surface, status, 1, 1, self.at, PUBLIC_REF + "#removal")
                    if value.surface == "owned_caches"
                    else value
                    for value in outcomes
                ]
                report = RemovalReport(
                    "unremoved", "owned_synthetic_sandbox", self.at, tuple(outcomes)
                )
                self.assertFalse(report.resolved)
                with self.assertRaises(ContractError):
                    report.require_resolved()
                self.assertTrue(contains_withdrawn(path))

    @unittest.skipUnless(
        os.environ.get("WRAP_BRIEF_GITLEAKS"), "explicit checksum-verified scanner required"
    )
    def test_new_editorial_html_and_removal_report_are_scanned_as_explicit_public_outputs(self):
        with tempfile.TemporaryDirectory(prefix="wrap-brief-editorial-public-") as temporary:
            root = Path(temporary).resolve()
            public, policy = root / "public", root / "policy"
            public.mkdir()
            policy.mkdir()
            correction = CorrectionControl(
                "synthetic-correct",
                self.item.source_id,
                "correct",
                self.at,
                item_id=self.item.id,
                metadata_ref=metadata_reference(self.item),
                public_notice_ref=PUBLIC_REF + "#correction",
            )
            result = reviewed(self.state, ledger_for(self.state, controls=(correction,)))
            owned_file(public / "index.html", render_editorial(result).encode())
            owned_file(public / "styles.css", (ROOT / "web/styles.css").read_bytes())
            report = RemovalReport(
                "synthetic-scanned-report",
                "owned_synthetic_sandbox",
                self.at,
                self.outcomes("removed"),
            )
            owned_file(public / "removal-report.json", report.to_json())
            self.assertEqual(
                {path.name for path in public.iterdir()},
                {"index.html", "styles.css", "removal-report.json"},
            )
            check_security.scan(
                Path(os.environ["WRAP_BRIEF_GITLEAKS"]).absolute(), "dir", public, policy
            )
