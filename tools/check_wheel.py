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
from wrap_brief.ingest.polling import reduce_polls

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
poll_batch = reduce_polls(Snapshot(datetime(2026, 1, 2, tzinfo=UTC)), (),
                         expected_source_ids=(), observed_at=datetime(2026, 1, 2, tzinfo=UTC))
assert poll_batch.health == 'no_sources'
assert poll_batch.to_snapshot(clusters=()).items == ()
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
inputs = Path(sys.argv[2]).resolve()
assert not inputs.is_relative_to(Path(sys.argv[1]).resolve())
def cli(*arguments):
    result = subprocess.run([sys.executable, '-I', '-B', '-m', 'wrap_brief.cli', *map(str, arguments)],
                            capture_output=True, timeout=15, check=True)
    assert result.stderr == b''
    return json.loads(result.stdout)
collection = Path.cwd() / 'collection.json'
site = Path.cwd() / 'site'
assert cli('collect', '--previous', inputs / 'previous.json', '--plan', inputs / 'plan.json',
           '--code-ref', '0' * 40, '--output', collection)['successful_sources'] == 2
cli('build', '--collection', collection, '--stylesheet', inputs / 'styles.css', '--output', site)
assert cli('check', '--collection', collection, '--stylesheet', inputs / 'styles.css', '--candidate', site)['not_deployed']
dry = Path.cwd() / 'dry-collection.json'
assert cli('collect', '--previous', inputs / 'previous.json', '--plan', inputs / 'plan.json',
           '--code-ref', '0' * 40, '--output', dry, '--dry-run')['dry_run']
assert not dry.exists()
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
        inputs = directory / "inputs"
        inputs.mkdir()
        for source, name in (
            ("tests/fixtures/views/empty.json", "previous.json"),
            ("tests/integration/fixtures/poll-plan.json", "plan.json"),
            ("web/styles.css", "styles.css"),
        ):
            (inputs / name).write_bytes((ROOT / source).read_bytes())
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
                str(inputs),
            ],
            cwd=directory,
            env=environment,
            check=True,
            timeout=120,
        )


if __name__ == "__main__":
    main()
