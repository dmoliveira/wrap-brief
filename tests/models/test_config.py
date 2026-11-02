from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wrap_brief.config import MAX_CONFIG_BYTES, SourceRegistry, load_registry
from wrap_brief.models import ContractError

from .test_models import source

ROOT = Path(__file__).resolve().parents[2]


class RegistryTests(unittest.TestCase):
    def test_metadata_io_errors_are_redacted(self):
        with patch.object(
            Path, "is_symlink", side_effect=PermissionError("synthetic-private-path")
        ):
            with self.assertRaises(ContractError) as caught:
                load_registry(Path("config/sources.json"))
        self.assertNotIn("synthetic-private-path", str(caught.exception))

    def test_repository_has_no_enabled_sources(self):
        registry = load_registry(ROOT / "config/sources.json")
        self.assertEqual(registry, SourceRegistry())
        self.assertEqual(registry.enabled_sources, ())

    def test_registry_round_trip(self):
        registry = SourceRegistry((source(),))
        restored = SourceRegistry.from_dict(json.loads(json.dumps(registry.to_dict())))
        self.assertEqual(registry, restored)
        self.assertEqual(restored.enabled_sources, ())

    def test_unknown_fields_duplicates_and_types(self):
        invalid = [
            {"schema_version": 1, "sources": [], "token": "not allowed"},
            {"schema_version": True, "sources": []},
            {"schema_version": 2, "sources": []},
            {"schema_version": 1, "sources": {}},
            {"schema_version": 1, "sources": [source().to_dict(), source().to_dict()]},
        ]
        for value in invalid:
            with self.subTest(value=type(value).__name__), self.assertRaises(ContractError):
                SourceRegistry.from_dict(value)
        with self.assertRaises(ContractError):
            SourceRegistry(sources=[source()])

    def test_json_file_validation(self):
        invalid = [
            b'{"schema_version":1,"sources":[],"sources":[]}',
            b'{"schema_version":1,"sources":NaN}',
            b"not-json",
            b"\xff",
            b" " * (MAX_CONFIG_BYTES + 1),
            b"[" * 1500,
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.json"
            for content in invalid:
                path.write_bytes(content)
                with self.subTest(size=len(content)), self.assertRaises(ContractError):
                    load_registry(path)

    def test_missing_file_and_symlink_errors_do_not_disclose_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private-config.json"
            with self.assertRaises(ContractError) as caught:
                load_registry(path)
            self.assertNotIn(directory, str(caught.exception))
            path.write_text('{"schema_version":1,"sources":[]}')
            link = Path(directory) / "alias.json"
            link.symlink_to(path)
            with self.assertRaises(ContractError):
                load_registry(link)


if __name__ == "__main__":
    unittest.main()
