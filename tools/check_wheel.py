"""Build and import the wheel in an isolated environment outside the checkout."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORT_CHECK = """
import sys
from importlib.metadata import distribution
from pathlib import Path
import wrap_brief

package = distribution('wrap-brief')
assert not package.requires, 'Foundation unexpectedly has runtime dependencies'
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
        not in {"GH_TOKEN", "GITHUB_TOKEN", "PYTHONPATH", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"}
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
