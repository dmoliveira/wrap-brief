"""Explicit local synthetic collect/build/check; no live HTTP, backend or deployment."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

from wrap_brief.models import ContractError
from wrap_brief.pipeline import (
    FILES,
    MAX_PIPELINE_BYTES,
    MAX_STYLESHEET_BYTES,
    CandidateMismatch,
    Collection,
    PollPlan,
    UnusableHealth,
    build,
    check,
    collect,
    summary,
)
from wrap_brief.state.snapshot import Snapshot


def _emit(value: dict[str, object], *, error: bool = False) -> None:
    print(
        json.dumps(value, sort_keys=True, separators=(",", ":")),
        file=sys.stderr if error else sys.stdout,
    )


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        _emit({"stage": "arguments", "status": "invalid_input"}, error=True)
        raise SystemExit(2)


def _path(path: Path) -> Path:
    if ".." in path.parts:
        raise OSError("unsafe path")
    result = path.absolute()
    if any(parent.is_symlink() for parent in (result, *result.parents)):
        raise OSError("symlinked path")
    return result


def _read(path: Path, limit: int, *, candidate: bool = False) -> bytes:
    path = _path(path)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_size > limit
            or (candidate and (metadata.st_nlink != 1 or metadata.st_mode & 0o111))
        ):
            raise OSError("unsupported input")
        data = stream.read(limit + 1)
    if len(data) > limit or len(data) != metadata.st_size:
        raise OSError("changed input")
    return data


def _destination(path: Path) -> Path:
    path = _path(path)
    if path.exists() or not path.parent.is_dir():
        raise OSError("fresh destination and existing parent required")
    return path


def _write_private(path: Path, data: bytes) -> None:
    path = _destination(path)
    # An exclusive hard-link publication gives a complete file without replacing a destination.
    with tempfile.NamedTemporaryFile(prefix="collection-", dir=path.parent) as stream:
        stream.write(data)
        stream.flush()
        os.link(stream.name, path, follow_symlinks=False)


def _write_candidate(path: Path, files: dict[str, bytes]) -> None:
    path = _destination(path)
    with tempfile.TemporaryDirectory(prefix="candidate-", dir=path.parent) as temporary:
        staging = Path(temporary)
        for name, data in files.items():
            with os.fdopen(
                os.open(staging / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
            ) as stream:
                stream.write(data)
        if path.exists() or path.is_symlink():
            raise OSError("output collision")
        staging.rename(path)


def _candidate(path: Path) -> dict[str, bytes]:
    path = _path(path)
    if not path.is_dir():
        raise OSError("candidate directory required")
    names = []
    for entry in path.iterdir():
        names.append(entry.name)
        if len(names) > len(FILES):
            raise OSError("candidate inventory limit")
    if set(names) != set(FILES):
        raise CandidateMismatch("pipeline: candidate inventory mismatch")
    return {name: _read(path / name, limit, candidate=True) for name, limit in FILES.items()}


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    commands = parser.add_subparsers(dest="stage", required=True, parser_class=_Parser)
    collect_parser = commands.add_parser("collect", help="reduce supplied synthetic fetch results")
    collect_parser.add_argument("--previous", required=True, type=Path)
    collect_parser.add_argument("--plan", required=True, type=Path)
    collect_parser.add_argument("--code-ref", required=True)
    collect_parser.add_argument("--output", required=True, type=Path)
    for name in ("build", "check"):
        stage_parser = commands.add_parser(
            name, help="verify synthetic execution envelope and candidate"
        )
        stage_parser.add_argument("--collection", required=True, type=Path)
        stage_parser.add_argument("--stylesheet", required=True, type=Path)
        stage_parser.add_argument(
            "--output" if name == "build" else "--candidate", required=True, type=Path
        )
    for command in commands.choices.values():
        command.add_argument(
            "--dry-run", action="store_true", help="validate in memory without creating outputs"
        )
    args = parser.parse_args(argv)
    try:
        if args.stage == "collect":
            previous = Snapshot.from_json(_read(args.previous, MAX_PIPELINE_BYTES))
            plan = PollPlan.from_json(_read(args.plan, MAX_PIPELINE_BYTES))
            collection = collect(previous, plan, code_ref=args.code_ref)
            _destination(args.output)
            if not args.dry_run:
                _write_private(args.output, collection.to_json())
            value = summary(collection, "collect", dry_run=args.dry_run)
            _emit(value)
            return 3 if collection.batch.health in {"blocked", "no_sources"} else 0
        collection = Collection.from_json(_read(args.collection, MAX_PIPELINE_BYTES))
        collection.require_usable()
        stylesheet = _read(args.stylesheet, MAX_STYLESHEET_BYTES)
        if args.stage == "build":
            result = build(collection, stylesheet)
            _destination(args.output)
            if not args.dry_run:
                _write_candidate(args.output, result.files())
            _emit(summary(collection, "build", dry_run=args.dry_run))
        else:
            value = check(collection, _candidate(args.candidate), stylesheet)
            value["dry_run"] = args.dry_run
            _emit(value)
        return 0
    except UnusableHealth:
        status, code = "unusable_source_health", 3
    except CandidateMismatch:
        status, code = "candidate_mismatch", 5
    except (ContractError, ValueError, TypeError, RecursionError):
        status, code = "invalid_input", 2
    except OSError:
        status, code = "filesystem_error", 4
    except Exception:
        status, code = "internal_error", 5
    _emit({"stage": args.stage, "status": status}, error=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
