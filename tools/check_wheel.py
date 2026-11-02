"""Build and import the wheel in an isolated environment outside the checkout."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORT_CHECK = """
import sys
import json
import subprocess
from datetime import UTC, datetime
from importlib.metadata import distribution
from pathlib import Path
import wrap_brief
from wrap_brief.config import SourceRegistry
from wrap_brief.models import SCHEMA_VERSION
from wrap_brief.ingest.parsers import parse_feed
from wrap_brief.ingest.normalize import normalize_entry
from wrap_brief.grouping.identity import stable_item_id
from wrap_brief.state.snapshot import Snapshot
from wrap_brief.state.local import LocalState
from wrap_brief.grouping.stories import group_items
from wrap_brief.render.digest import render_digest
from wrap_brief.ingest.http import fetch_feed

package = distribution('wrap-brief')
assert package.requires == ['defusedxml==0.7.1'], 'Unexpected runtime dependencies'
assert SourceRegistry().enabled_sources == ()
assert SCHEMA_VERSION == 1
assert callable(parse_feed)
assert callable(normalize_entry)
assert stable_item_id('demo-a', 'https://example.com/a').startswith('item-v1-')
assert callable(Snapshot.from_json) and callable(LocalState)
assert callable(group_items)
assert callable(fetch_feed)
worker = subprocess.run(
    [sys.executable, '-I', '-m', 'wrap_brief.ingest._http_worker'],
    input=b'{}', capture_output=True, timeout=5, check=True,
)
assert json.loads(worker.stdout) == {'error': 'protocol'} and worker.stderr == b''
assert 'Hand-authored examples only.' in render_digest(Snapshot(datetime(2026, 1, 2, tzinfo=UTC)))
assert not Path(wrap_brief.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
assert Path(wrap_brief.__file__).resolve() == Path(
    package.locate_file('wrap_brief/__init__.py')
).resolve()
print('Wheel installation and import outside checkout: passed')
"""


def main() -> None:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "GH_TOKEN",
            "GITHUB_TOKEN",
            "PYTHONPATH",
            "VIRTUAL_ENV",
            "UV_PROJECT_ENVIRONMENT",
            "UV_INDEX",
            "UV_DEFAULT_INDEX",
            "UV_INDEX_URL",
            "UV_EXTRA_INDEX_URL",
            "PIP_INDEX_URL",
            "PIP_EXTRA_INDEX_URL",
        }
    }
    with tempfile.TemporaryDirectory(prefix="wrap-brief-wheel-") as temporary:
        directory = Path(temporary)
        output = directory / "dist"
        subprocess.run(
            ["uv", "build", "--out-dir", str(output)],
            cwd=ROOT,
            env=environment,
            check=True,
            timeout=120,
        )
        wheels = list(output.glob("*.whl"))
        if len(wheels) != 1:
            raise SystemExit("Expected exactly one built wheel")
        subprocess.run(
            [
                "uv",
                "run",
                "--no-project",
                "--isolated",
                "--default-index",
                "https://pypi.org/simple",
                "--python",
                (ROOT / ".python-version").read_text().strip(),
                "--with",
                str(wheels[0]),
                "python",
                "-I",
                "-c",
                IMPORT_CHECK,
                str(ROOT),
            ],
            cwd=directory,
            env=environment,
            check=True,
            timeout=120,
        )


if __name__ == "__main__":
    main()
