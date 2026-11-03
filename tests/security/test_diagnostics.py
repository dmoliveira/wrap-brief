"""Offline policy/boundary tests; real pinned scanner probes require an explicit tool path."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "security_diagnostics", ROOT / "tools/check_security.py"
)
security = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(security)


def current_tree():
    names = ["pyproject.toml", "uv.lock", ".github/security/audit-requirements.txt"]
    names += [".github/workflows/" + name for name in security.WORKFLOWS]
    return {name: (ROOT / name).read_bytes() for name in names}


def git(root, *args):
    return security.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Synthetic",
            "-c",
            "user.email=synthetic@example.com",
            *args,
        ],
        cwd=root,
        capture=True,
    )


def commit(root):
    git(root, "add", "--all")
    git(root, "commit", "-qm", "Synthetic safety test")


def artifacts(root):
    for case in security.ARTIFACT_CASES:
        folder = root / case
        folder.mkdir(parents=True)
        (folder / "index.html").write_bytes(b"<p>Synthetic</p>")
        (folder / "styles.css").write_bytes(b"p { color: black; }")


class DiagnosticTests(unittest.TestCase):
    def test_current_frozen_workflow_policy(self):
        security.validate_workflows(current_tree())

    def test_workflow_policy_rejects_privilege_events_secrets_cache_and_shadowing_changes(self):
        original = current_tree()
        for old, new in (
            (b"contents: read", b"contents: write"),
            (b"pull_request:", b"pull_request_target:"),
            (b"enable-cache: false", b"enable-cache: true"),
            (b"persist-credentials: false", b"persist-credentials: true"),
            (b"run: make validate", b"run: echo ${{ secrets.TEST }}"),
        ):
            with self.subTest(change=new):
                tree = dict(original)
                tree[".github/workflows/plan.yml"] = tree[".github/workflows/plan.yml"].replace(
                    old, new
                )
                with self.assertRaises(security.SecurityError):
                    security.validate_workflows(tree)
        changed = dict(original, **{".github/workflows/shadow.yaml": b"name: Planning checks\n"})
        with self.assertRaises(security.SecurityError):
            security.validate_workflows(changed)

    def test_safe_paths_modes_and_byte_limits(self):
        for path in (
            "../escape",
            "/absolute",
            "a/../escape",
            ".git/config",
            "bad\npath",
            "a\\b",
            "a//b",
        ):
            with self.subTest(path=path), self.assertRaises(security.SecurityError):
                security.safe_path(path)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git(root, "init", "-q")
            (root / "data.txt").write_text("synthetic")
            commit(root)
            with patch.object(security, "MAX_BLOB", 1), self.assertRaises(security.SecurityError):
                security.commit_tree(root)
            (root / "link").symlink_to("data.txt")
            commit(root)
            with self.assertRaisesRegex(security.SecurityError, "unsupported_mode"):
                security.commit_tree(root)

    def test_exact_commit_blobs_ignore_export_attributes_and_working_copy_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git(root, "init", "-q")
            (root / ".gitattributes").write_text("hidden.txt export-ignore\n")
            (root / "hidden.txt").write_bytes(b"synthetic\x00binary")
            (root / ".tracked-dotfile").write_bytes(b"data")
            commit(root)
            (root / "hidden.txt").write_text("changed working copy")
            tree = security.commit_tree(root)
            self.assertEqual(tree["hidden.txt"], b"synthetic\x00binary")
            self.assertIn(".tracked-dotfile", tree)
            with self.assertRaises(security.SecurityError):
                security.commit_tree(root, "--all")

    def test_private_files_and_markers_fail_without_echo(self):
        for name in (
            ".local/public.txt",
            "private.sqlite3",
            ".env.production",
            "runtime/state.json",
        ):
            with self.assertRaises(security.SecurityError):
                security.validate_public_tree({name: b""})
        value = ("/" + "Users" + "/synthetic/private").encode()
        with self.assertRaises(security.SecurityError) as error:
            security.validate_public_tree({"file.txt": value})
        self.assertTrue(value.decode() not in str(error.exception))

    def test_database_sidecar_names_are_private_in_every_supported_spelling(self):
        for suffix in ("db", "sqlite", "sqlite3"):
            for sidecar in ("wal", "shm", "journal", "mj-synthetic"):
                name = f"private.{suffix}-{sidecar}"
                for value in (name, name.upper()):
                    with self.subTest(name=value), self.assertRaises(security.SecurityError):
                        security.validate_public_tree({value: b"synthetic private state"})

    def test_incomplete_history_stops_before_scanners(self):
        with (
            patch.object(security, "commit_tree", return_value=current_tree()),
            patch.object(security, "run", return_value=b"true\n"),
            patch.object(security, "scan") as scan,
            self.assertRaises(security.SecurityError),
        ):
            security.scan_publication(ROOT, Path("unused"), Path("unused"))
        scan.assert_not_called()

    def test_forced_scanner_policy_and_neutral_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(security, "run") as run:
                security.scan(Path("/unused/gitleaks"), "dir", root, root)
            arguments = run.call_args.args[0]
            self.assertIn("--ignore-gitleaks-allow", arguments)
            self.assertIn("--redact=100", arguments)
            self.assertEqual((root / "gitleaks.toml").read_text(), "[extend]\nuseDefault = true\n")
            self.assertEqual((root / "empty-ignore").read_bytes(), b"")
            self.assertTrue("--baseline-path" not in arguments)
        with patch.dict(
            os.environ,
            {
                "GITLEAKS_CONFIG_TOML": "hostile",
                "GIT_CONFIG_COUNT": "1",
                "PIP_INDEX_URL": "hostile",
            },
        ):
            env = security.environment()
        self.assertFalse(any(key.startswith("GITLEAKS_") for key in env))
        self.assertNotIn("GIT_CONFIG_COUNT", env)
        self.assertNotIn("PIP_INDEX_URL", env)

    def test_raw_process_failures_and_timeouts_never_escape_main(self):
        marker = "synthetic-private-diagnostic"
        with (
            tempfile.TemporaryDirectory() as temporary,
            self.assertRaises(security.SecurityError) as error,
        ):
            security.run(
                [sys.executable, "-c", f"import sys; print({marker!r}); sys.exit(1)"],
                cwd=Path(temporary),
                capture=True,
            )
        self.assertTrue(marker not in str(error.exception))
        with (
            patch.object(
                sys,
                "argv",
                [
                    "check_security.py",
                    "publication",
                    "--gitleaks",
                    "/unused",
                    "--actionlint",
                    "/unused",
                ],
            ),
            patch.object(
                security, "scan_publication", side_effect=subprocess.TimeoutExpired(marker, 1)
            ),
            patch("sys.stderr", new_callable=io.StringIO) as stderr,
            self.assertRaises(SystemExit),
        ):
            security.main()
        self.assertTrue(marker not in stderr.getvalue())

    def test_inventory_includes_all_runtime_dev_build_uv_and_auditor_packages(self):
        tool, inventory = security.inventory(current_tree())
        self.assertEqual(len(tool), 28)
        self.assertEqual(len(inventory), 31)
        self.assertEqual(inventory["defusedxml"][0], "0.7.1")
        self.assertEqual(inventory["ruff"][0], "0.16.2")
        self.assertEqual(inventory["uv-build"][0], security.CI_UV)
        self.assertEqual(inventory["uv"][0], security.CI_UV)
        self.assertEqual(inventory["pip-audit"][0], security.AUDITOR)
        self.assertEqual(security.parse_requirements(security.requirements(inventory)), inventory)

    def test_arbitrary_requirement_syntax_hash_omissions_and_sources_are_rejected(self):
        for data in (
            b"package==1.0\n",
            b"-r private.txt\n",
            b"https://example.com/untrusted.whl\n",
            b"package>=1.0\n",
            b"package[extra]==1.0\n",
            b"-e .\n",
        ):
            with self.subTest(data=data), self.assertRaises(security.SecurityError):
                security.parse_requirements(data)
        tree = current_tree()
        tree["uv.lock"] = tree["uv.lock"].replace(
            b'registry = "https://pypi.org/simple"', b'git = "https://example.com/code"', 1
        )
        with self.assertRaises(security.SecurityError):
            security.inventory(tree)

    def test_build_hooks_missing_lock_entries_and_dynamic_metadata_fail_closed(self):
        for old, new in (
            (b"uv_build==0.13.6", b"evil_build==1.0"),
            (b'dependencies = ["defusedxml==0.7.1"]', b'dynamic = ["dependencies"]'),
            (b"defusedxml==0.7.1", b"defusedxml==0.7.2"),
        ):
            tree = current_tree()
            tree["pyproject.toml"] = tree["pyproject.toml"].replace(old, new)
            with self.subTest(change=new), self.assertRaises((security.SecurityError, KeyError)):
                security.inventory(tree)

    def test_lock_artifact_urls_must_use_the_canonical_pypi_artifact_origin(self):
        for url in (
            "http://files.pythonhosted.org/packages/file.whl",
            "https://untrusted.example/packages/file.whl",
            "https://user:pass@files.pythonhosted.org/packages/file.whl",
            "https://files.pythonhosted.org:444/packages/file.whl",
            "https://files.pythonhosted.org/packages/file.whl?redirect=other",
            "https://files.pythonhosted.org/packages/file.whl#fragment",
            "file:///private/file.whl",
        ):
            tree = current_tree()
            text = tree["uv.lock"].decode()
            start = text.index('sdist = { url = "') + len('sdist = { url = "')
            end = text.index('"', start)
            tree["uv.lock"] = (text[:start] + url + text[end:]).encode()
            with self.subTest(url=url), self.assertRaises(security.SecurityError):
                security.inventory(tree)
        security.inventory(current_tree())

    def test_advisory_unknown_skipped_duplicate_and_missing_results_are_not_clean_audits(self):
        expected = {"synthetic": ("1.0", ("0" * 64,))}
        good = {"dependencies": [{"name": "synthetic", "version": "1.0", "vulns": []}], "fixes": []}
        security.validate_audit(json.dumps(good).encode(), expected)
        for change in ("vulnerable", "skipped", "missing", "duplicate", "unknown"):
            report = copy.deepcopy(good)
            row = report["dependencies"][0]
            if change == "vulnerable":
                row["vulns"] = [{"id": "SYNTHETIC-1"}]
            if change == "skipped":
                row["skip_reason"] = "Unavailable"
            if change == "missing":
                report["dependencies"] = []
            if change == "duplicate":
                report["dependencies"].append(row)
            if change == "unknown":
                row["name"] = "unknown"
            with self.subTest(change=change), self.assertRaises(security.SecurityError):
                security.validate_audit(json.dumps(report).encode(), expected)

    def test_advisory_outage_is_failure_and_resolution_is_disabled(self):
        with (
            patch.object(security, "commit_tree", return_value=current_tree()),
            patch.object(security, "run", side_effect=security.SecurityError("tool_failed")) as run,
            self.assertRaises(security.SecurityError),
        ):
            security.audit(ROOT, Path("/unused/pip-audit"))
        args = run.call_args.args[0]
        for flag in ("--strict", "--disable-pip", "--no-deps", "--require-hashes"):
            self.assertIn(flag, args)

    def test_exact_artifact_inventory_symlinks_extra_files_modes_and_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            artifacts(root)
            self.assertEqual(len(security.artifact_tree(root)), 6)
            file = root / "digest/index.html"
            file.write_bytes(b"x" * 1_048_577)
            with self.assertRaises(security.SecurityError):
                security.artifact_tree(root)
            file.unlink()
            file.symlink_to(root / "empty/index.html")
            with self.assertRaises((security.SecurityError, OSError)):
                security.artifact_tree(root)
            file.unlink()
            file.write_bytes(b"synthetic")
            file.chmod(0o700)
            with self.assertRaises(security.SecurityError):
                security.artifact_tree(root)
            file.chmod(0o600)
            (root / "digest/script.js").write_bytes(b"unreviewed")
            with self.assertRaises(security.SecurityError):
                security.artifact_tree(root)

    def test_bootstrap_checks_literal_digest_before_opening_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "bin"
            with (
                patch.object(security.platform, "system", return_value="Linux"),
                patch.object(security.platform, "machine", return_value="x86_64"),
                patch.object(
                    security.urllib.request, "urlopen", return_value=io.BytesIO(b"corrupt")
                ),
                patch.object(security.tarfile, "open") as archive,
                self.assertRaises(security.SecurityError),
            ):
                security.bootstrap(root)
            archive.assert_not_called()

    def test_bootstrap_extracts_only_fixed_regular_member_without_archive_paths(self):
        content = b"synthetic executable, never run"
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            member = tarfile.TarInfo("gitleaks")
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        data = buffer.getvalue()
        binaries = {
            "gitleaks": (
                "gitleaks/gitleaks",
                "8.30.1",
                {"Linux": ("linux_x64", hashlib.sha256(data).hexdigest())},
            )
        }
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "bin"
            with (
                patch.object(security, "BINARIES", binaries),
                patch.object(security.platform, "system", return_value="Linux"),
                patch.object(security.platform, "machine", return_value="x86_64"),
                patch.object(security.urllib.request, "urlopen", return_value=io.BytesIO(data)),
            ):
                security.bootstrap(directory)
            self.assertEqual((directory / "gitleaks").read_bytes(), content)
            self.assertEqual({p.name for p in directory.iterdir()}, {"gitleaks"})


@unittest.skipUnless(
    os.environ.get("WRAP_BRIEF_GITLEAKS"), "explicit checksum-verified scanner required"
)
class ActualScannerTests(unittest.TestCase):
    def setUp(self):
        self.scanner = Path(os.environ["WRAP_BRIEF_GITLEAKS"]).absolute()
        self.canary = ("ghp_" + "aB12cD34eF56gH78iJ90kL12mN34oP56qR78").encode()

    def test_current_tree_cannot_suppress_dotfile_inline_allow_or_binary_credential(self):
        for name, prefix in ((".tracked-dotfile", b""), ("binary.dat", b"\x00")):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                public = root / "public"
                policy = root / "policy"
                public.mkdir()
                policy.mkdir()
                (public / ".gitleaks.toml").write_text('[allowlist]\nregexes = [".*"]\n')
                (public / ".gitleaksignore").write_text(f"{name}:github-pat:1\n")
                (public / name).write_bytes(prefix + self.canary + b" # gitleaks:allow\n")
                with self.assertRaises(security.SecurityError):
                    security.scan(self.scanner, "dir", public, policy)

    def test_deleted_history_credential_is_detected_with_no_raw_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            policy = root / "policy"
            repo.mkdir()
            policy.mkdir()
            git(repo, "init", "-q")
            (repo / "removed.txt").write_bytes(self.canary)
            commit(repo)
            (repo / "removed.txt").unlink()
            (repo / "safe.txt").write_text("synthetic")
            commit(repo)
            self.assertNotIn("removed.txt", security.commit_tree(repo))
            with self.assertRaises(security.SecurityError) as error:
                security.scan(self.scanner, "git", repo, policy)
            self.assertTrue(self.canary.decode() not in str(error.exception))

    def test_generated_public_html_credential_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            public = root / "artifacts"
            policy = root / "policy"
            public.mkdir()
            policy.mkdir()
            artifacts(public)
            (public / "digest/index.html").write_bytes(b"<p>" + self.canary + b"</p>")
            tree = security.artifact_tree(public)
            staged = root / "staged"
            staged.mkdir()
            security.stage(tree, staged)
            with self.assertRaises(security.SecurityError):
                security.scan(self.scanner, "dir", staged, policy)

    def test_merge_only_credential_then_deleted_is_detected_in_first_parent_merge_diff(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            policy = root / "policy"
            repo.mkdir()
            policy.mkdir()
            git(repo, "init", "-q")
            (repo / "base.txt").write_text("synthetic base")
            commit(repo)
            original = git(repo, "symbolic-ref", "--short", "HEAD").decode().strip()
            git(repo, "checkout", "-qb", "side")
            (repo / "side.txt").write_text("synthetic side")
            commit(repo)
            git(repo, "checkout", "-q", original)
            (repo / "main.txt").write_text("synthetic main")
            commit(repo)
            git(repo, "merge", "--no-ff", "--no-commit", "side")
            (repo / "merge-only.txt").write_bytes(self.canary)
            commit(repo)
            self.assertEqual(len(git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()), 3)
            (repo / "merge-only.txt").unlink()
            commit(repo)
            self.assertNotIn("merge-only.txt", security.commit_tree(repo))
            with self.assertRaises(security.SecurityError):
                security.scan(self.scanner, "git", repo, policy)


if __name__ == "__main__":
    unittest.main()
