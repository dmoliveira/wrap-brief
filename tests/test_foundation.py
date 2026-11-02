"""Observable installed-package contracts, independent of future news features."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from importlib import metadata


class InstalledPackageTests(unittest.TestCase):
    def test_distribution_has_no_runtime_dependencies(self):
        distribution = metadata.distribution("wrap-brief")
        self.assertEqual(distribution.metadata["Name"], "wrap-brief")
        self.assertEqual(distribution.requires or [], [])

    def test_isolated_import_outside_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    "import wrap_brief; from importlib.metadata import version; "
                    "assert wrap_brief.__doc__; print(version('wrap-brief'))",
                ],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
        self.assertEqual(result.stdout.strip(), metadata.version("wrap-brief"))


if __name__ == "__main__":
    unittest.main()
