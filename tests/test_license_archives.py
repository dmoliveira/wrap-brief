"""Offline adversarial tests for the license distribution-scope checks."""

from __future__ import annotations

import importlib.util
import io
import re
import stat
import tarfile
import tempfile
import tomllib
import unittest
import warnings
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("license_wheel_check", ROOT / "tools/check_wheel.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def write_archives(
    directory: Path,
    *,
    altered_config: str | None = None,
    wheel_info: str | None = None,
    wheel_symlink: str | None = None,
    wheel_extra_directory: str | None = None,
    duplicate_wheel_member: bool = False,
    sdist_extra_directory: str | None = None,
    duplicate_sdist_member: bool = False,
    metadata_headers: bytes | None = None,
) -> None:
    project_bytes = (ROOT / "pyproject.toml").read_bytes()
    project = tomllib.loads(project_bytes.decode("utf-8"))["project"]
    name = re.sub(r"[-_.]+", "_", project["name"]).lower()
    archive_name = f"{name}-{project['version']}"
    info = wheel_info or f"{archive_name}.dist-info/"
    readme = (ROOT / "README.md").read_bytes()
    license_text = (ROOT / "LICENSE").read_bytes()
    headers = (
        metadata_headers or b"Metadata-Version: 2.4\nLicense-Expression: MIT\nLicense-File: LICENSE"
    )
    metadata = headers + b"\n\n" + readme
    source_root = ROOT / "src"
    sources = {
        path.relative_to(source_root).as_posix(): path.read_bytes()
        for path in (source_root / "wrap_brief").rglob("*.py")
    }
    sdist = {
        "LICENSE": license_text,
        "README.md": readme,
        "PKG-INFO": metadata,
        "pyproject.toml": project_bytes,
        "pyproject.toml.orig": project_bytes,
    } | {"src/" + name: data for name, data in sources.items()}
    if altered_config is not None:
        sdist[altered_config] = b'[build-system]\nrequires = ["unreviewed"]\n'
    with tarfile.open(directory / f"{archive_name}.tar.gz", "w:gz") as archive:
        directories = {
            "/".join(f"{archive_name}/{name}".split("/")[:index])
            for name in sdist
            for index in range(1, len(f"{archive_name}/{name}".split("/")))
        }
        if sdist_extra_directory is not None:
            directories.add(sdist_extra_directory)
        for name in sorted(directories):
            member = tarfile.TarInfo(name)
            member.type = tarfile.DIRTYPE
            member.mode = 0o755
            archive.addfile(member)
        for name, data in sdist.items():
            member = tarfile.TarInfo(f"{archive_name}/{name}")
            member.mode = 0o644
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        if duplicate_sdist_member:
            member = tarfile.TarInfo(f"{archive_name}/LICENSE")
            member.mode = 0o644
            member.size = len(license_text)
            archive.addfile(member, io.BytesIO(license_text))

    wheel = sources | {
        info + "METADATA": metadata,
        info + "WHEEL": b"Wheel-Version: 1.0\n",
        info + "RECORD": b"",
        info + "licenses/LICENSE": license_text,
    }
    directories = {
        "/".join(name.split("/")[:index]) + "/"
        for name in wheel
        for index in range(1, len(name.split("/")))
    }
    if wheel_extra_directory is not None:
        directories.add(wheel_extra_directory)
    with zipfile.ZipFile(directory / f"{archive_name}-py3-none-any.whl", "w") as archive:
        for name in sorted(directories):
            member = zipfile.ZipInfo(name)
            member.create_system = 3
            member.external_attr = (stat.S_IFDIR | 0o755) << 16
            archive.writestr(member, b"")
        for name, data in wheel.items():
            member = zipfile.ZipInfo(name)
            member.create_system = 3
            mode = (stat.S_IFLNK | 0o777) if name == wheel_symlink else (stat.S_IFREG | 0o644)
            member.external_attr = mode << 16
            archive.writestr(member, data)
        if duplicate_wheel_member:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(info + "WHEEL", b"duplicate")


class LicenseArchiveTests(unittest.TestCase):
    def verify(self, expected_error: str | None = None, **options: object) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            write_archives(output, **options)
            if expected_error is None:
                checker.verify_archives(output)
            else:
                with self.assertRaisesRegex(SystemExit, expected_error):
                    checker.verify_archives(output)

    def test_matching_archives_are_accepted(self):
        self.verify()

    def test_both_source_build_configurations_must_match_reviewed_bytes(self):
        for name in ("pyproject.toml", "pyproject.toml.orig"):
            with self.subTest(name=name):
                self.verify("different build configuration", altered_config=name)

    def test_source_distribution_rejects_extra_unsafe_directories_and_duplicates(self):
        cases = (
            ("unsafe path", {"sdist_extra_directory": "../../unexpected-directory"}),
            ("Unexpected source-distribution contents", {"sdist_extra_directory": "unrelated"}),
            ("duplicate members", {"duplicate_sdist_member": True}),
        )
        for error, options in cases:
            with self.subTest(error=error):
                self.verify(error, **options)

    def test_wheel_rejects_traversal_symlink_extra_directory_and_duplicate(self):
        info = "wrap_brief-0.1.0.dist-info/"
        cases = (
            ("unsafe path", {"wheel_info": "../outside-0.1.0.dist-info/"}),
            ("unsafe member type or mode", {"wheel_symlink": info + "WHEEL"}),
            ("Unexpected wheel contents", {"wheel_extra_directory": "unexpected/"}),
            ("duplicate members", {"duplicate_wheel_member": True}),
        )
        for error, options in cases:
            with self.subTest(error=error):
                self.verify(error, **options)

    def test_metadata_must_use_valid_pep_639_without_legacy_license(self):
        cases = (
            (
                b"Metadata-Version: 2.1\nLicense-Expression: MIT\nLicense-File: LICENSE",
                "not PEP 639",
            ),
            (
                b"Metadata-Version: 2.4\nLicense: legacy\nLicense-Expression: MIT\nLicense-File: LICENSE",
                "conflicting legacy",
            ),
            (
                b"Metadata-Version: 2.4\nMalformed header\nLicense-Expression: MIT\nLicense-File: LICENSE",
                "malformed",
            ),
            (
                b"Metadata-Version: 2.4\nMetadata-Version: 2.4\nLicense-Expression: MIT\nLicense-File: LICENSE",
                "not PEP 639",
            ),
        )
        for headers, error in cases:
            with self.subTest(error=error):
                self.verify(error, metadata_headers=headers)


if __name__ == "__main__":
    unittest.main()
