"""Unprivileged diagnostics, not an immutable contribution-admission control plane."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import re
import stat
import subprocess
import tarfile
import tempfile
import tomllib
import urllib.request
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_BLOB = 2_000_000
MAX_TREE = 32_000_000
MAX_FILES = 2_000
CI_UV = "0.13.6"
AUDITOR = "2.10.1"
# Deliberate policy baseline, not a YAML parser. Changes require reviewing the entire workflow.
WORKFLOWS = {
    "plan.yml": "2926d2492ca45735d316e9ed108e886bfa6e793f9c683978fb87e5df8f80769c",
    "safety.yml": "9f56ed028add6490b393e9283643237f10abfe5be8fbd98d4c86d5776ffbb7f9",
}
BINARIES = {
    "gitleaks": (
        "gitleaks/gitleaks",
        "8.30.1",
        {
            "Linux": (
                "linux_x64",
                "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
            ),
            "Darwin": (
                "darwin_arm64",
                "b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5",
            ),
        },
    ),
    "actionlint": (
        "rhysd/actionlint",
        "1.7.12",
        {
            "Linux": (
                "linux_amd64",
                "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
            ),
            "Darwin": (
                "darwin_arm64",
                "aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f",
            ),
        },
    ),
}
EXTRA_PACKAGES = {
    "uv": (CI_UV, ("22759b8895e1103578de6fb4cd27e94b4399d021023378d29f01333717751fba",)),
    "uv-build": (CI_UV, ("b23bbf1393acb47c1bd434f79daa91c158a14a504894485b5a9948f68d63170b",)),
}
PIN = r"([a-z0-9]+(?:[-_][a-z0-9]+)*)==([0-9]+(?:\.[0-9]+)*)"
HASH = r"[a-f0-9]{64}"
ARTIFACT_CASES = ("digest", "corrected", "empty")
CLI_ARTIFACT_CASE = "cli"


class SecurityError(ValueError):
    """Only fixed public-safe codes escape this module."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise SecurityError(code)


def environment() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GITLEAKS_", "GIT_CONFIG_", "PIP_", "PIP_AUDIT_"))
    }
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        PIP_CONFIG_FILE=os.devnull,
        PYTHONPATH="",
        PYTHONNOUSERSITE="1",
        PYTHONSAFEPATH="1",
    )
    return env


def run(command: list[str], *, cwd: Path, capture: bool = False, timeout: int = 120) -> bytes:
    # Never forward diagnostics: redaction alone does not hide malicious paths or errors.
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=environment(),
            stdin=subprocess.DEVNULL,
            stdout=output if capture else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        require(result.returncode == 0, "tool_failed")
        require(output.tell() <= MAX_TREE, "tool_output_limit")
        output.seek(0)
        return output.read() if capture else b""


def safe_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    require(
        bool(name)
        and len(name.encode()) <= 240
        and not path.is_absolute()
        and path.as_posix() == name
        and not set(path.parts) & {"..", ".", ".git"}
        and "\\" not in name
        and all(ord(char) >= 32 and ord(char) != 127 for char in name),
        "unsafe_path",
    )
    return path


def commit_tree(root: Path, commit: str = "HEAD") -> dict[str, bytes]:
    require(
        commit == "HEAD" or re.fullmatch(r"[a-f0-9]{40}", commit) is not None, "commit_required"
    )
    sha = run(["git", "rev-parse", "--verify", commit], cwd=root, capture=True).decode().strip()
    require(re.fullmatch(r"[a-f0-9]{40}", sha) is not None, "commit_required")
    records = run(["git", "ls-tree", "-rlz", "--full-tree", sha], cwd=root, capture=True).split(
        b"\0"
    )
    require(len(records) <= MAX_FILES + 1, "tree_count_limit")
    tree, total = {}, 0
    for record in filter(None, records):
        metadata, raw_name = record.split(b"\t", 1)
        mode, kind, object_id, raw_size = metadata.split()
        require(mode in {b"100644", b"100755"} and kind == b"blob", "unsupported_mode")
        name = str(safe_path(raw_name.decode("utf-8")))
        size = int(raw_size)
        total += size
        require(size <= MAX_BLOB and total <= MAX_TREE, "tree_byte_limit")
        data = run(["git", "cat-file", "blob", object_id.decode("ascii")], cwd=root, capture=True)
        require(len(data) == size, "incomplete_blob")
        require(name not in tree, "duplicate_path")
        tree[name] = data
    require(bool(tree), "empty_tree")
    return tree


def stage(tree: dict[str, bytes], directory: Path) -> None:
    for name, data in tree.items():
        target = directory.joinpath(*safe_path(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def validate_public_tree(tree: dict[str, bytes]) -> None:
    private_directories = {".local", ".state", "runtime", ".codememory", ".opencode", ".venv"}
    private_suffixes = {".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx"}
    for name, data in tree.items():
        path = safe_path(name)
        require(
            not set(path.parts) & private_directories
            and path.suffix.lower() not in private_suffixes
            and re.search(r"\.(?:db|sqlite|sqlite3)-[^/]+$", path.name.lower()) is None
            and not (path.name.startswith(".env") and path.name != ".env.example"),
            "private_file",
        )
        require(
            re.search(rb"/(?:Users|home)/[^/\s]+|ses_[A-Za-z0-9]{16,}", data) is None,
            "private_marker",
        )


def validate_workflows(tree: dict[str, bytes]) -> None:
    workflows = {
        name.removeprefix(".github/workflows/"): data
        for name, data in tree.items()
        if name.startswith(".github/workflows/")
    }
    require(set(workflows) == set(WORKFLOWS), "workflow_inventory")
    require(
        all(
            hashlib.sha256(data).hexdigest() == WORKFLOWS[name] for name, data in workflows.items()
        ),
        "workflow_policy_changed",
    )


def scan(gitleaks: Path, mode: str, target: Path, policy: Path) -> None:
    require(mode in {"dir", "git"}, "scan_mode")
    config = policy / "gitleaks.toml"
    config.write_text("[extend]\nuseDefault = true\n")
    ignore = policy / "empty-ignore"
    ignore.write_bytes(b"")
    command = [
        str(gitleaks),
        mode,
        "--config",
        str(config),
        "--gitleaks-ignore-path",
        str(ignore),
        "--ignore-gitleaks-allow",
        "--redact=100",
        "--no-banner",
        "--max-decode-depth=2",
    ]
    if mode == "git":
        command.append(
            "--log-opts=--all --full-history --diff-merges=first-parent --text --no-ext-diff --no-textconv"
        )
    run([*command, str(target)], cwd=policy)


def scan_publication(root: Path, gitleaks: Path, actionlint: Path) -> None:
    tree = commit_tree(root)
    validate_public_tree(tree)
    validate_workflows(tree)
    require(
        run(["git", "rev-parse", "--is-shallow-repository"], cwd=root, capture=True).strip()
        == b"false",
        "shallow_history",
    )
    # Bound every local object before asking Gitleaks to inspect fetched reachable history.
    objects = run(
        ["git", "cat-file", "--batch-all-objects", "--batch-check=%(objecttype) %(objectsize)"],
        cwd=root,
        capture=True,
    ).splitlines()
    require(len(objects) <= 40_000, "history_count_limit")
    sizes = [int(row.split()[1]) for row in objects]
    require(
        all(size <= MAX_BLOB for size in sizes) and sum(sizes) <= 256_000_000, "history_byte_limit"
    )
    with tempfile.TemporaryDirectory(prefix="public-scan-") as temporary:
        base = Path(temporary)
        public, policy = base / "tree", base / "policy"
        public.mkdir()
        policy.mkdir()
        stage(tree, public)
        scan(gitleaks, "dir", public, policy)
        scan(gitleaks, "git", root, policy)
        config = policy / "actionlint.yaml"
        config.write_text("{}\n")
        run(
            [
                str(actionlint),
                "-config-file",
                str(config),
                "-shellcheck=",
                "-pyflakes=",
                "-no-color",
                *[str(public / ".github/workflows" / name) for name in sorted(WORKFLOWS)],
            ],
            cwd=policy,
        )


def pinned(value: str) -> tuple[str, str]:
    match = re.fullmatch(PIN, value)
    require(match is not None, "unsupported_requirement")
    return match[1].replace("_", "-"), match[2]


def parse_requirements(data: bytes) -> dict[str, tuple[str, tuple[str, ...]]]:
    require(len(data) <= 64_000, "requirement_limit")
    inventory = {}
    for line in data.decode("ascii").replace("\\\n", " ").splitlines():
        require(
            re.fullmatch(PIN + rf"(?:\s+--hash=sha256:{HASH})+\s*", line) is not None,
            "unsupported_requirement",
        )
        name, version = pinned(line.split()[0])
        require(name not in inventory, "duplicate_requirement")
        hashes = tuple(sorted(set(re.findall(r"--hash=sha256:(" + HASH + ")", line))))
        inventory[name] = (version, hashes)
    require(0 < len(inventory) <= 100, "requirement_count")
    return inventory


def requirements(inventory: dict[str, tuple[str, tuple[str, ...]]]) -> bytes:
    return (
        "\n".join(
            f"{name}=={version} " + " ".join(f"--hash=sha256:{digest}" for digest in hashes)
            for name, (version, hashes) in sorted(inventory.items())
        )
        + "\n"
    ).encode("ascii")


def inventory(tree: dict[str, bytes]) -> tuple[dict, dict]:
    validate_workflows(tree)
    project = tomllib.loads(tree["pyproject.toml"].decode())
    lock = tomllib.loads(tree["uv.lock"].decode())
    tool = parse_requirements(tree[".github/security/audit-requirements.txt"])
    require(tool.get("pip-audit", (None,))[0] == AUDITOR, "auditor_pin")
    declared = project["project"]
    require(not set(declared) & {"dynamic", "optional-dependencies"}, "unsupported_dependencies")
    require(set(project.get("dependency-groups", {})) == {"dev"}, "unsupported_dependency_groups")
    uv = project["tool"]["uv"]
    require(
        set(uv) <= {"required-version", "index"}
        and uv.get("index")
        == [{"name": "pypi", "url": "https://pypi.org/simple", "default": True}],
        "unsupported_index",
    )
    direct = dict(pinned(value) for value in declared["dependencies"])
    development = dict(pinned(value) for value in project["dependency-groups"]["dev"])
    require(
        len(direct) == len(declared["dependencies"])
        and len(development) == len(project["dependency-groups"]["dev"])
        and not set(direct) & set(development),
        "duplicate_requirement",
    )
    build = project["build-system"]
    require(build == {"requires": [f"uv_build=={CI_UV}"], "build-backend": "uv_build"}, "build_pin")
    external, local = {}, []
    for package in lock["package"]:
        if package["source"] == {"editable": "."}:
            local.append(package)
            continue
        require(package["source"] == {"registry": "https://pypi.org/simple"}, "unsupported_source")
        name, version = pinned(f"{package['name']}=={package['version']}")
        require(name not in external, "duplicate_package")
        artifacts = package.get("wheels", []) + ([package["sdist"]] if "sdist" in package else [])
        hashes = []
        for artifact in artifacts:
            url = artifact["url"]
            require(
                type(url) is str
                and len(url) <= 2_048
                and all(33 <= ord(char) <= 126 for char in url),
                "package_url",
            )
            parsed = urlsplit(url)
            require(
                parsed.scheme == "https"
                and parsed.netloc == "files.pythonhosted.org"
                and parsed.path.startswith("/packages/")
                and not parsed.query
                and not parsed.fragment,
                "package_origin",
            )
            require(re.fullmatch("sha256:" + HASH, artifact["hash"]) is not None, "package_hash")
            hashes.append(artifact["hash"][7:])
        require(bool(hashes), "missing_package_hash")
        external[name] = (version, tuple(sorted(set(hashes))))
    require(len(local) == 1 and local[0]["name"] == declared["name"], "local_package")
    metadata = local[0]["metadata"]
    for rows, declared_pins in (
        (metadata["requires-dist"], direct),
        (metadata["requires-dev"]["dev"], development),
    ):
        require(
            all(set(row) == {"name", "specifier"} for row in rows), "unsupported_lock_requirement"
        )
        pins = dict(pinned(row["name"] + row["specifier"]) for row in rows)
        require(pins == declared_pins and len(pins) == len(rows), "lock_declaration_mismatch")
    require(
        all(
            name in external and external[name][0] == version
            for name, version in (direct | development).items()
        ),
        "missing_locked_dependency",
    )
    combined = dict(external)
    for addition in (tool, EXTRA_PACKAGES):
        for name, (version, hashes) in addition.items():
            if name in combined:
                require(combined[name][0] == version, "inventory_version_conflict")
                hashes = tuple(sorted(set(hashes + combined[name][1])))
            combined[name] = (version, hashes)
    return tool, combined


def validate_audit(data: bytes, expected: dict) -> None:
    require(len(data) <= 8_000_000, "audit_output_limit")
    report = json.loads(data)
    require(type(report) is dict and report.get("fixes", []) == [], "audit_shape")
    rows = report.get("dependencies")
    require(type(rows) is list and len(rows) == len(expected), "incomplete_audit")
    found = {}
    for row in rows:
        require(
            type(row) is dict and "skip_reason" not in row and row.get("vulns") == [],
            "advisory_or_skip",
        )
        name, version = pinned(f"{row['name']}=={row['version']}")
        require(name not in found, "duplicate_audit")
        found[name] = version
    require(found == {name: value[0] for name, value in expected.items()}, "incomplete_audit")


def audit(root: Path, auditor: Path) -> None:
    _, expected = inventory(commit_tree(root))
    with tempfile.TemporaryDirectory(prefix="advisory-audit-") as temporary:
        directory = Path(temporary)
        path = directory / "requirements.txt"
        path.write_bytes(requirements(expected))
        result = run(
            [
                str(auditor),
                "--strict",
                "--disable-pip",
                "--no-deps",
                "--require-hashes",
                "--progress-spinner=off",
                "--format=json",
                "--desc=off",
                "--aliases=off",
                "--timeout=15",
                "--cache-dir",
                str(directory / "cache"),
                "-r",
                str(path),
            ],
            cwd=directory,
            capture=True,
            timeout=300,
        )
        validate_audit(result, expected)


def _artifact_names(directory: Path, limit: int) -> set[str]:
    names = set()
    for path in directory.iterdir():
        names.add(path.name)
        require(len(names) <= limit, "artifact_inventory")
    return names


def artifact_tree(directory: Path) -> dict[str, bytes]:
    require(
        not any(parent.is_symlink() for parent in (directory, *directory.parents)),
        "artifact_symlink",
    )
    cases = (*ARTIFACT_CASES, CLI_ARTIFACT_CASE)
    require(_artifact_names(directory, len(cases)) == set(cases), "artifact_inventory")
    result = {}
    for case in cases:
        folder = directory / case
        require(not folder.is_symlink() and folder.is_dir(), "artifact_mode")
        files = {"index.html": 1_048_576, "styles.css": 65_536}
        if case == CLI_ARTIFACT_CASE:
            files["manifest.json"] = 16_384
        require(_artifact_names(folder, len(files)) == set(files), "artifact_inventory")
        for name, limit in files.items():
            path = folder / name
            with os.fdopen(
                os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb"
            ) as stream:
                metadata = os.fstat(stream.fileno())
                require(
                    stat.S_ISREG(metadata.st_mode)
                    and not metadata.st_mode & 0o111
                    and metadata.st_nlink == 1
                    and metadata.st_size <= limit,
                    "artifact_byte_limit",
                )
                data = stream.read(limit + 1)
            require(len(data) == metadata.st_size and len(data) <= limit, "artifact_changed")
            result[f"{case}/{name}"] = data
    return result


def bootstrap(directory: Path) -> None:
    system = platform.system()
    require(
        (system, platform.machine()) in {("Linux", "x86_64"), ("Darwin", "arm64")},
        "unsupported_platform",
    )
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name, (repo, version, platforms) in BINARIES.items():
        suffix, digest = platforms[system]
        url = f"https://github.com/{repo}/releases/download/v{version}/{name}_{version}_{suffix}.tar.gz"
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read(32_000_001)
        require(
            len(data) <= 32_000_000 and hashlib.sha256(data).hexdigest() == digest,
            "download_integrity",
        )
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            member = archive.getmember(name)
            require(member.isfile() and member.size <= 64_000_000, "archive_member")
            with archive.extractfile(member) as stream:
                executable = stream.read(64_000_001)
        require(len(executable) == member.size, "archive_size")
        target = directory / name
        with target.open("xb") as stream:
            stream.write(executable)
        target.chmod(0o700)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("bootstrap", "publication", "inventory", "audit", "artifacts")
    )
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--gitleaks", type=Path)
    parser.add_argument("--actionlint", type=Path)
    parser.add_argument("--auditor", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "bootstrap":
            require(args.directory is not None, "directory_required")
            bootstrap(args.directory.absolute())
        elif args.command == "publication":
            require(args.gitleaks is not None and args.actionlint is not None, "tools_required")
            scan_publication(ROOT, args.gitleaks.absolute(), args.actionlint.absolute())
        elif args.command == "inventory":
            require(args.directory is not None, "directory_required")
            tool, combined = inventory(commit_tree(ROOT))
            args.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
            (args.directory / "tool.txt").write_bytes(requirements(tool))
            (args.directory / "all.txt").write_bytes(requirements(combined))
        elif args.command == "audit":
            require(args.auditor is not None, "auditor_required")
            audit(ROOT, args.auditor.absolute())
        else:
            require(args.directory is not None and args.gitleaks is not None, "tools_required")
            tree = artifact_tree(args.directory.absolute())
            with tempfile.TemporaryDirectory(prefix="artifact-scan-") as temporary:
                base = Path(temporary)
                public, policy = base / "public", base / "policy"
                public.mkdir()
                policy.mkdir()
                stage(tree, public)
                scan(args.gitleaks.absolute(), "dir", public, policy)
    except (
        SecurityError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
        tarfile.TarError,
    ):
        parser.exit(1, "Security diagnostic failed; findings and raw tool output are withheld.\n")
    print(f"Security diagnostic {args.command}: passed (not an admission or fork-isolation proof).")


if __name__ == "__main__":
    main()
