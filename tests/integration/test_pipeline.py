from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from fixtures.support import read_bytes, read_json

from wrap_brief import cli, pipeline
from wrap_brief.grouping.stories import group_items
from wrap_brief.ingest.http import FetchResult
from wrap_brief.ingest.polling import SourcePoll
from wrap_brief.models import ContractError
from wrap_brief.pipeline import Collection, PollPlan, build, check, collect
from wrap_brief.state.snapshot import Snapshot

ROOT = Path(__file__).resolve().parents[2]
CODE = "1" * 40
NO_WRITES = """
import sys
import os
from wrap_brief.cli import main
def guard(event, args):
    if event.startswith('socket.') or event == 'sqlite3.connect':
        raise AssertionError('unexpected external side effect')
    if event in {'os.mkdir', 'os.remove', 'os.rename', 'os.link', 'os.symlink', 'os.rmdir', 'os.chmod'}:
        raise AssertionError('unexpected filesystem mutation')
    if event == 'open':
        mode, flags = args[1:3]
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise AssertionError('unexpected file write')
sys.addaudithook(guard)
raise SystemExit(main(sys.argv[1:]))
"""


def inventory(root):
    return {
        str(path.relative_to(root)): (
            path.stat().st_mode,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def rss(title="Hand-authored game announced"):
    return (
        "<rss version='2.0'><channel><item><title>"
        + title
        + "</title><link>https://example.com/synthetic-game</link>"
        + "<guid>synthetic-private-guid</guid><pubDate>2026-01-02T12:00:00Z</pubDate>"
        + "</item></channel></rss>"
    ).encode()


class PipelineFixtures:
    def setUp(self):
        self.previous = Snapshot.from_dict(read_json("views/empty.json"))
        self.plan = PollPlan.from_json(
            (ROOT / "tests/integration/fixtures/poll-plan.json").read_bytes()
        )
        self.style = (ROOT / "web/styles.css").read_bytes()

    def single(self, response=None, previous=None, observed=None):
        previous = previous or self.previous
        response = response or FetchResult("ok", 1, body=rss(), etag='"private-fixture-validator"')
        plan = PollPlan(
            observed or previous.observed_at, ("demo-a",), (SourcePoll("demo-a", response),)
        )
        return collect(previous, plan, code_ref=CODE)


class PipelineTests(PipelineFixtures, unittest.TestCase):
    def test_plan_fixture_body_equality_and_deterministic_round_trips(self):
        self.assertEqual(self.plan.polls[0].response.body, read_bytes("feeds/rss-basic.xml"))
        self.assertEqual(self.plan.polls[1].response.body, read_bytes("feeds/atom-basic.xml"))
        self.assertEqual(PollPlan.from_json(self.plan.to_json()), self.plan)
        first = collect(self.previous, self.plan, code_ref=CODE)
        replayed = Collection.from_json(first.to_json())
        self.assertEqual(replayed.to_json(), first.to_json())
        self.assertEqual(replayed.batch, first.batch)
        a, b = build(first, self.style), build(replayed, self.style)
        self.assertEqual(a.files(), b.files())
        self.assertEqual(a.snapshot.digest, b.snapshot.digest)
        self.assertEqual(len(a.snapshot.items), 4)
        self.assertEqual(check(replayed, a.files(), self.style)["successful_sources"], 2)

    def test_core_stages_never_lookup_clock_network_or_filesystem(self):
        collection = self.single()
        with (
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(os, "open", side_effect=AssertionError("filesystem")),
            patch.object(pipeline, "datetime") as clock,
        ):
            replay = collect(self.previous, self.plan, code_ref=CODE)
            candidate = build(replay, self.style)
            check(replay, candidate.files(), self.style)
            build(collection, self.style)
        clock.now.assert_not_called()
        clock.utcnow.assert_not_called()

    def test_all_entry_points_reject_live_enabled_and_unrequested_foreign_sources(self):
        for previous in (
            replace(self.previous, kind="live"),
            replace(
                self.previous,
                sources=(
                    replace(
                        self.previous.sources[0],
                        enabled=True,
                        approval_status="approved",
                        approval_ref="tests/fixtures/README.md",
                        reviewed_at=self.previous.observed_at,
                    ),
                    *self.previous.sources[1:],
                ),
            ),
            replace(
                self.previous,
                sources=(
                    *self.previous.sources[:2],
                    replace(
                        self.previous.sources[2],
                        site_url="https://www.iana.org/",
                        feed_url="https://www.iana.org/synthetic-feed.xml",
                        allowed_hosts=("www.iana.org",),
                    ),
                ),
            ),
        ):
            with self.subTest(kind=previous.kind), self.assertRaises(ContractError):
                self.single(previous=previous)
        original = self.single()
        data = json.loads(original.to_json())
        data["previous"]["kind"] = "live"
        with self.assertRaises(ContractError):
            Collection.from_json(json.dumps(data).encode())

    def test_304_empty_and_partial_failure_have_honest_current_health(self):
        first = build(self.single(), self.style).snapshot
        unchanged = self.single(
            FetchResult("not_modified", 1), first, first.observed_at + timedelta(minutes=1)
        )
        self.assertEqual(unchanged.batch.items, first.items)
        self.assertEqual(unchanged.batch.health, "healthy")
        self.assertTrue(unchanged.batch.no_new)
        check(unchanged, build(unchanged, self.style).files(), self.style)
        empty = self.single(
            FetchResult("ok", 1, body=read_bytes("feeds/rss-empty.xml")),
            first,
            first.observed_at + timedelta(minutes=1),
        )
        self.assertEqual(empty.batch.items, first.items)
        self.assertTrue(empty.batch.no_new)
        build(empty, self.style)
        partial = collect(
            first,
            PollPlan(
                first.observed_at + timedelta(minutes=1),
                ("demo-a", "demo-b"),
                (
                    SourcePoll("demo-a", FetchResult("error", 1, "network")),
                    SourcePoll(
                        "demo-b", FetchResult("ok", 1, body=read_bytes("feeds/atom-empty.xml"))
                    ),
                ),
            ),
            code_ref=CODE,
        )
        self.assertEqual(partial.batch.health, "degraded")
        result = build(partial, self.style)
        self.assertEqual(result.snapshot.items, first.items)
        self.assertEqual(json.loads(result.manifest)["health"]["failed_sources"], 1)

    def test_all_failed_deferred_and_no_sources_block_retained_story_build_and_check(self):
        first = build(self.single(), self.style).snapshot
        failed = self.single(FetchResult("error", 1, "network"), first)
        deferred = self.single(
            FetchResult("deferred", 0, "poll_interval", retry_after_seconds=60), first
        )
        none = collect(first, PollPlan(first.observed_at, (), ()), code_ref=CODE)
        previous_candidate = build(self.single(), self.style).files()
        for collection in (failed, deferred, none):
            self.assertTrue(collection.batch.items)
            with (
                self.subTest(health=collection.batch.health),
                patch.object(
                    pipeline, "group_items", side_effect=AssertionError("grouping too early")
                ),
                patch.object(
                    pipeline, "render_digest", side_effect=AssertionError("rendering too early")
                ),
            ):
                with self.assertRaises(pipeline.UnusableHealth):
                    build(collection, self.style)
                with self.assertRaises(pipeline.UnusableHealth):
                    check(collection, previous_candidate, self.style)
        self.assertEqual(deferred.batch.checkpoints, first.checkpoints)

    def test_changed_metadata_is_regrouped_with_complete_fixed_evidence(self):
        first = build(self.single(), self.style).snapshot
        changed = self.single(
            FetchResult("ok", 1, body=rss("Hand-authored game review")),
            first,
            first.observed_at + timedelta(minutes=1),
        )
        with patch.object(pipeline, "group_items", wraps=group_items) as grouping:
            result = build(changed, self.style)
        self.assertEqual(grouping.call_args.kwargs["previous_clusters"], first.clusters)
        self.assertEqual(
            {e.item_id for e in grouping.call_args.kwargs["lead_evidence"]},
            {i.id for i in result.snapshot.items},
        )
        self.assertEqual(result.snapshot.clusters[0].topic, "review")
        self.assertEqual(changed.batch.outcomes[0].updated_items, 1)

    def test_mixed_quarantine_stays_usable_all_quarantine_does_not(self):
        mixed = rss().replace(b"</channel>", b"<item><title>Missing link</title></item></channel>")
        collection = self.single(FetchResult("ok", 1, body=mixed))
        self.assertEqual(collection.batch.outcomes[0].quarantined_rows, 1)
        self.assertIn(
            "quarantined_entries",
            json.loads(build(collection, self.style).manifest)["health"]["warnings"],
        )
        bad = self.single(
            FetchResult(
                "ok", 1, body=b"<rss><channel><item><title>No link</title></item></channel></rss>"
            )
        )
        with self.assertRaises(pipeline.UnusableHealth):
            build(bad, self.style)

    def test_manifest_binds_complete_input_state_policy_style_and_safe_counts_only(self):
        collection = self.single()
        result = build(collection, self.style)
        manifest = json.loads(result.manifest)
        self.assertEqual(manifest["code_ref"], CODE)
        self.assertEqual(manifest["collection_ref"], collection.digest)
        self.assertEqual(manifest["previous_state_ref"], self.previous.digest)
        self.assertEqual(manifest["batch_ref"], collection.batch_ref)
        self.assertEqual(manifest["state_ref"], result.snapshot.digest)
        self.assertEqual(set(manifest["artifacts"]), {"index.html", "styles.css"})
        for marker in (
            b"private-fixture-validator",
            b"synthetic-private-guid",
            b"example.com",
            b"Hand-authored game",
        ):
            self.assertNotIn(marker, result.manifest)
        self.assertNotEqual(build(collection, self.style + b"\n").manifest, result.manifest)
        self.assertNotIn("Hand-authored game", repr(collection))

    def test_plan_envelope_unknowns_duplicates_base64_versions_and_limits_fail_closed(self):
        value = self.plan.to_dict()
        for key, change in (
            ("schema_version", True),
            ("extra", "private"),
            ("observed_at", "not-a-clock"),
        ):
            altered = dict(value, **{key: change})
            with self.subTest(key=key), self.assertRaises(ContractError):
                PollPlan.from_json(json.dumps(altered).encode())
        for encoded in ("not base64!", "x" * (4 * ((2_097_152 + 2) // 3) + 1)):
            altered = json.loads(self.plan.to_json())
            altered["responses"][0]["body_base64"] = encoded
            with self.assertRaises(ContractError):
                PollPlan.from_json(json.dumps(altered).encode())
        with self.assertRaises(ContractError):
            PollPlan.from_json(b'{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ContractError):
            PollPlan.from_json(b'{"clock":NaN}')
        with self.assertRaises(ContractError):
            Collection.from_json(b" " * (pipeline.MAX_PIPELINE_BYTES + 1))
        data = json.loads(self.single().to_json())
        data["health"] = "healthy"
        with self.assertRaises(ContractError):
            Collection.from_json(json.dumps(data).encode())
        with patch.object(pipeline, "MAX_PIPELINE_ITEMS", 0), self.assertRaises(ContractError):
            self.single()

    def test_all_outcome_retry_and_request_fields_affect_batch_reference(self):
        a = self.single(FetchResult("error", 1, "network"))
        b = self.single(FetchResult("error", 2, "network"))
        c = self.single(FetchResult("error", 1, "timeout"))
        self.assertEqual(len({a.batch_ref, b.batch_ref, c.batch_ref}), 3)
        deferred = self.single(FetchResult("deferred", 0, "poll_interval", retry_after_seconds=60))
        data = json.loads(deferred.to_json())
        data["plan"]["responses"][0]["retry_after_seconds"] = 61
        with self.assertRaises(ContractError):
            Collection.from_json(json.dumps(data).encode())

    def test_self_rehashed_manifest_and_changed_or_extra_candidate_are_rejected(self):
        collection = self.single()
        files = build(collection, self.style).files()
        files["index.html"] += b"<p>Substituted</p>"
        manifest = json.loads(files["manifest.json"])
        manifest["artifacts"]["index.html"] = hashlib.sha256(files["index.html"]).hexdigest()
        files["manifest.json"] = json.dumps(
            manifest, sort_keys=True, separators=(",", ":")
        ).encode()
        with self.assertRaises(pipeline.CandidateMismatch):
            check(collection, files, self.style)
        files = build(collection, self.style).files()
        files["state.json"] = b"{}"
        with self.assertRaises(pipeline.CandidateMismatch):
            check(collection, files, self.style)


class CliTests(PipelineFixtures, unittest.TestCase):
    def invoke(self, root, *args, no_writes=False):
        command = [sys.executable, "-I", "-B"]
        command += ["-c", NO_WRITES] if no_writes else ["-m", "wrap_brief.cli"]
        environment = {
            k: v
            for k, v in os.environ.items()
            if k not in {"GH_TOKEN", "GITHUB_TOKEN", "PYTHONPATH"}
        }
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [*command, *map(str, args)],
            cwd=root,
            env=environment,
            capture_output=True,
            timeout=15,
            check=False,
        )

    def inputs(self, root, collection=None):
        (root / "previous.json").write_bytes(self.previous.to_json())
        (root / "plan.json").write_bytes(self.plan.to_json())
        (root / "styles.css").write_bytes(self.style)
        if collection is not None:
            (root / "collection.json").write_bytes(collection.to_json())

    def test_separate_process_collect_build_check_and_two_fresh_outputs_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.inputs(root)
            a = self.invoke(
                root,
                "collect",
                "--previous",
                "previous.json",
                "--plan",
                "plan.json",
                "--code-ref",
                CODE,
                "--output",
                "collection.json",
            )
            self.assertEqual(a.returncode, 0)
            self.assertEqual(stat.S_IMODE((root / "collection.json").stat().st_mode), 0o600)
            replay = self.invoke(
                root,
                "collect",
                "--previous",
                "previous.json",
                "--plan",
                "plan.json",
                "--code-ref",
                CODE,
                "--output",
                "collection-replay.json",
            )
            self.assertEqual(replay.returncode, 0)
            self.assertEqual(
                (root / "collection.json").read_bytes(),
                (root / "collection-replay.json").read_bytes(),
            )
            for name in ("site-a", "site-b"):
                b = self.invoke(
                    root,
                    "build",
                    "--collection",
                    "collection.json",
                    "--stylesheet",
                    "styles.css",
                    "--output",
                    name,
                )
                self.assertEqual(b.returncode, 0)
                before = inventory(root)
                c = self.invoke(
                    root,
                    "check",
                    "--collection",
                    "collection.json",
                    "--stylesheet",
                    "styles.css",
                    "--candidate",
                    name,
                    no_writes=True,
                )
                self.assertEqual(c.returncode, 0)
                self.assertEqual(inventory(root), before)
            self.assertEqual(
                {p.name: p.read_bytes() for p in (root / "site-a").iterdir()},
                {p.name: p.read_bytes() for p in (root / "site-b").iterdir()},
            )

    def test_dry_run_creates_no_files_temp_directories_or_database_on_success_or_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.inputs(root, self.single())
            (root / "private.sqlite3").write_bytes(b"synthetic existing state")
            before = inventory(root)
            directories = sorted(str(p) for p in root.rglob("*"))
            for args in (
                (
                    "collect",
                    "--previous",
                    "previous.json",
                    "--plan",
                    "plan.json",
                    "--code-ref",
                    CODE,
                    "--output",
                    "new.json",
                ),
                (
                    "build",
                    "--collection",
                    "collection.json",
                    "--stylesheet",
                    "styles.css",
                    "--output",
                    "new-site",
                ),
            ):
                result = self.invoke(root, *args, "--dry-run", no_writes=True)
                self.assertEqual(result.returncode, 0)
            failed = self.single(FetchResult("error", 1, "network"))
            (root / "failed.json").write_bytes(failed.to_json())
            before = inventory(root)
            result = self.invoke(
                root,
                "build",
                "--collection",
                "failed.json",
                "--stylesheet",
                "styles.css",
                "--output",
                "new-site",
                "--dry-run",
                no_writes=True,
            )
            self.assertEqual(result.returncode, 3)
            self.assertEqual(inventory(root), before)
            self.assertFalse((root / "new.json").exists())
            self.assertFalse((root / "new-site").exists())
            self.assertEqual(
                sorted(str(p) for p in root.rglob("*") if p.name != "failed.json"), directories
            )

    def test_existing_outputs_collide_without_mutation_in_dry_run_and_normal_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.inputs(root, self.single())
            (root / "existing").mkdir()
            (root / "existing/owned.txt").write_bytes(b"keep")
            before = inventory(root)
            for dry in ((), ("--dry-run",)):
                a = self.invoke(
                    root,
                    "collect",
                    "--previous",
                    "previous.json",
                    "--plan",
                    "plan.json",
                    "--code-ref",
                    CODE,
                    "--output",
                    "collection.json",
                    *dry,
                )
                b = self.invoke(
                    root,
                    "build",
                    "--collection",
                    "collection.json",
                    "--stylesheet",
                    "styles.css",
                    "--output",
                    "existing",
                    *dry,
                )
                self.assertEqual((a.returncode, b.returncode), (4, 4))
                self.assertEqual(inventory(root), before)

    def test_failed_collection_is_private_and_cannot_build_or_check_last_good_story(self):
        first = build(self.single(), self.style).snapshot
        for response in (
            FetchResult("error", 1, "network"),
            FetchResult("deferred", 0, "poll_interval", retry_after_seconds=60),
            None,
        ):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                self.inputs(root)
                (root / "previous.json").write_bytes(first.to_json())
                plan = (
                    PollPlan(first.observed_at, ("demo-a",), (SourcePoll("demo-a", response),))
                    if response is not None
                    else PollPlan(first.observed_at, (), ())
                )
                (root / "plan.json").write_bytes(plan.to_json())
                result = self.invoke(
                    root,
                    "collect",
                    "--previous",
                    "previous.json",
                    "--plan",
                    "plan.json",
                    "--code-ref",
                    CODE,
                    "--output",
                    "blocked.json",
                )
                self.assertEqual(result.returncode, 3)
                self.assertEqual(stat.S_IMODE((root / "blocked.json").stat().st_mode), 0o600)
                for stage, flag in (("build", "--output"), ("check", "--candidate")):
                    result = self.invoke(
                        root,
                        stage,
                        "--collection",
                        "blocked.json",
                        "--stylesheet",
                        "styles.css",
                        flag,
                        "no-site",
                    )
                    self.assertEqual(result.returncode, 3)
                    self.assertFalse((root / "no-site").exists())

    def test_symlink_nonregular_executable_hardlinked_and_extra_candidates_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.inputs(root, self.single())
            (root / "alias").symlink_to(root, target_is_directory=True)
            result = self.invoke(
                root,
                "build",
                "--collection",
                "alias/collection.json",
                "--stylesheet",
                "styles.css",
                "--output",
                "site",
            )
            self.assertEqual(result.returncode, 4)
            self.assertFalse((root / "site").exists())
            result = self.invoke(
                root,
                "build",
                "--collection",
                "collection.json",
                "--stylesheet",
                "styles.css",
                "--output",
                "site",
            )
            self.assertEqual(result.returncode, 0)
            html = root / "site/index.html"
            original = html.read_bytes()
            for mode in ("symlink", "fifo", "executable", "hardlink", "extra"):
                html.unlink()
                html.write_bytes(original)
                if mode == "symlink":
                    html.unlink()
                    html.symlink_to(root / "previous.json")
                if mode == "fifo":
                    html.unlink()
                    os.mkfifo(html)
                if mode == "executable":
                    html.chmod(0o700)
                if mode == "hardlink":
                    html.unlink()
                    os.link(root / "previous.json", html)
                if mode == "extra":
                    (root / "site/extra.json").write_bytes(b"{}")
                result = self.invoke(
                    root,
                    "check",
                    "--collection",
                    "collection.json",
                    "--stylesheet",
                    "styles.css",
                    "--candidate",
                    "site",
                )
                self.assertNotEqual(result.returncode, 0)

    def test_failure_cleanup_and_exclusive_private_file_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            before = inventory(root)
            original = os.open

            def fail(path, *args, **kwargs):
                if Path(path).name == "styles.css":
                    raise OSError("synthetic private failure")
                return original(path, *args, **kwargs)

            with patch.object(cli.os, "open", side_effect=fail), self.assertRaises(OSError):
                cli._write_candidate(root / "site", build(self.single(), self.style).files())
            self.assertEqual(inventory(root), before)
            self.assertEqual(list(root.iterdir()), [])
            with (
                patch.object(cli.os, "link", side_effect=OSError("synthetic private failure")),
                self.assertRaises(OSError),
            ):
                cli._write_private(root / "collection.json", b"synthetic")
            self.assertEqual(list(root.iterdir()), [])

    def test_invalid_arguments_and_input_errors_never_echo_private_fields_or_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.inputs(root)
            marker = "synthetic-private-marker"
            (root / "bad.json").write_bytes(marker.encode())
            for args in (
                (marker,),
                ("collect", "--unexpected", marker),
                (
                    "build",
                    "--collection",
                    "bad.json",
                    "--stylesheet",
                    "styles.css",
                    "--output",
                    "out",
                ),
                ("build", "--collection", marker, "--stylesheet", "styles.css", "--output", "out"),
            ):
                result = self.invoke(root, *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(marker.encode() not in result.stdout + result.stderr)
                self.assertTrue(str(root).encode() not in result.stdout + result.stderr)
                self.assertLess(len(result.stdout + result.stderr), 512)


if __name__ == "__main__":
    unittest.main()
