"""Build only committed synthetic views into fresh, ignored local preview directories."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from wrap_brief.models import ContractError, _check
from wrap_brief.render.digest import render_digest
from wrap_brief.state.snapshot import MAX_SNAPSHOT_BYTES, Snapshot

ROOT = Path(__file__).resolve().parents[1]
CASES = ("digest", "corrected", "empty")


def build_fixture(case: str) -> Path:
    _check(type(case) is str and case in CASES, "fixture", "unknown case")
    parent = ROOT / ".local" / "fixture-sites"
    for ancestor in (ROOT / ".local", parent):
        _check(not ancestor.is_symlink(), "fixture", "symlinked output ancestry")
    destination = parent / case
    _check(not destination.exists() and not destination.is_symlink(), "fixture", "output exists")
    with (ROOT / "tests" / "fixtures" / "views" / f"{case}.json").open("rb") as stream:
        snapshot = Snapshot.from_json(stream.read(MAX_SNAPSHOT_BYTES + 1))
    html = render_digest(snapshot).encode("utf-8")
    with (ROOT / "web" / "styles.css").open("rb") as stream:
        stylesheet = stream.read(65_537)
    _check(len(stylesheet) <= 65_536, "fixture", "stylesheet byte limit")
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fixture-build-", dir=parent) as temporary:
        staging = Path(temporary)
        (staging / "index.html").write_bytes(html)
        (staging / "styles.css").write_bytes(stylesheet)
        staging.rename(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", help="digest, corrected or empty")
    args = parser.parse_args()
    try:
        build_fixture(args.case)
    except ContractError as error:
        parser.exit(2, f"{error}\n")
    print("Synthetic fixture built under .local/fixture-sites/; open its index.html locally.")


if __name__ == "__main__":
    main()
