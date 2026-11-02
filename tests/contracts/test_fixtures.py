from __future__ import annotations

import hashlib
import re
import socket
import unittest
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.parse import urlsplit

from fixtures.support import MAX_RECIPE_BYTES, read_bytes, read_json, recipe_bytes

from wrap_brief.config import SourceRegistry
from wrap_brief.models import Cluster, Item, Source, validate_references

RAW_FIELDS = {"source_id", "title", "url", "guid", "published", "updated"}


class FixtureContractTests(unittest.TestCase):
    def setUp(self):
        self.manifest = read_json("manifest.json")

    def test_manifest_is_versioned_synthetic_and_clock_is_explicit(self):
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["kind"], "synthetic")
        clock = datetime.fromisoformat(self.manifest["observed_at"])
        self.assertEqual(clock.utcoffset(), UTC.utcoffset(clock))
        self.assertEqual(self.manifest["observed_at"], "2026-01-02T12:30:00Z")
        ids = [case["id"] for case in self.manifest["cases"] + self.manifest["recipes"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_case_hashes_and_raw_metadata_shape(self):
        sources = {
            s.id for s in SourceRegistry.from_dict(read_json(self.manifest["sources_file"])).sources
        }
        paths = []
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]):
                data = read_bytes(case["path"])
                paths.append(case["path"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), case["sha256"])
                self.assertIn(case["source_id"], sources)
                expected = case["expected"]
                self.assertEqual(len({"entries", "error"} & expected.keys()), 1)
                for entry in expected.get("entries", []):
                    self.assertEqual(set(entry), RAW_FIELDS)
                    self.assertEqual(entry["source_id"], case["source_id"])
                    self.assertIsInstance(entry["title"], str)
                    self.assertIsInstance(entry["url"], str)
        self.assertEqual(len(paths), len(set(paths)))

    def test_valid_small_feeds_are_well_formed_without_dtds(self):
        # Adversarial XML is deliberately NEVER parsed with the standard library.
        for case in self.manifest["cases"]:
            if not case["path"].startswith("feeds/"):
                continue
            data = read_bytes(case["path"])
            self.assertNotIn(b"<!DOCTYPE", data)
            self.assertNotIn(b"<!ENTITY", data)
            root = ET.fromstring(data)
            entries = list(root.iter("item")) + list(
                root.iter("{http://www.w3.org/2005/Atom}entry")
            )
            self.assertEqual(len(entries), len(case["expected"]["entries"]))

    def test_adversarial_probes_are_data_not_executed(self):
        cases = {case["id"]: case for case in self.manifest["cases"]}
        self.assertIn(b"<!ENTITY", read_bytes(cases["entity"]["path"]))
        self.assertIn(
            b"https://example.invalid/never-request", read_bytes(cases["external-entity"]["path"])
        )
        self.assertEqual(cases["entity"]["expected"]["error"], "xml_security")
        self.assertEqual(cases["unsafe-link"]["expected"]["normalization"], "reject_url")
        self.assertEqual(cases["future-date"]["expected"]["normalization"], "reject_future")
        self.assertEqual(cases["naive-date"]["expected"]["normalization"], "reject_date")

    def test_legacy_encoding_has_real_non_utf8_bytes(self):
        case = next(c for c in self.manifest["cases"] if c["id"] == "rss-latin1")
        data = read_bytes(case["path"])
        with self.assertRaises(UnicodeDecodeError):
            data.decode("utf-8")
        self.assertIn("Café", data.decode(case["encoding"]))

    def test_view_records_round_trip_without_live_source_activation(self):
        for name in self.manifest["views"]:
            value = read_json(name)
            self.assertEqual(value["kind"], "synthetic")
            self.assertEqual(value["schema_version"], 1)
            self.assertEqual(value["observed_at"], self.manifest["observed_at"])
            sources = tuple(Source.from_dict(v) for v in value["sources"])
            items = tuple(Item.from_dict(v) for v in value["items"])
            clusters = tuple(Cluster.from_dict(v) for v in value["clusters"])
            validate_references(sources, items, clusters)
            self.assertFalse(SourceRegistry(sources).enabled_sources)
            self.assertEqual([s.to_dict() for s in sources], value["sources"])
            self.assertEqual([i.to_dict() for i in items], value["items"])
            self.assertEqual([c.to_dict() for c in clusters], value["clusters"])

    def test_renderer_examples_keep_unknown_dates_rumors_and_corrections(self):
        digest = read_json("views/digest.json")
        self.assertEqual(len(digest["clusters"]), 3)
        self.assertTrue(any(i["published_at"] is None for i in digest["items"]))
        self.assertTrue(any(c["claim_status"] == "rumor" for c in digest["clusters"]))
        self.assertEqual(read_json("views/empty.json")["items"], [])
        corrected = read_json("views/corrected.json")
        self.assertEqual(corrected["clusters"][0]["correction_status"], "corrected")
        self.assertNotEqual(corrected["clusters"][0]["lead_id"], corrected["items"][0]["id"])

    def test_recipes_are_bounded_and_deterministic(self):
        for recipe in self.manifest["recipes"]:
            first = recipe_bytes(recipe)
            self.assertEqual(first, recipe_bytes(recipe))
            self.assertLessEqual(len(first), MAX_RECIPE_BYTES)
            if recipe["kind"] == "bytes":
                self.assertEqual(len(first), recipe["size"])
            elif recipe["kind"] == "depth":
                self.assertEqual(first.count(b"<node>"), recipe["size"] - 2)
            elif recipe["kind"] == "items":
                self.assertEqual(first.count(b"<item>"), recipe["size"])
        for kind, size in (
            ("bytes", MAX_RECIPE_BYTES + 1),
            ("depth", 129),
            ("items", 1001),
            ("title", 8193),
            ("unknown", 1),
            ("bytes", True),
            ("bytes", -1),
        ):
            with self.subTest(kind=kind, size=size), self.assertRaises(ValueError):
                recipe_bytes({"kind": kind, "size": size})

    def test_transport_examples_do_not_fetch_or_include_private_headers(self):
        transport = read_json(self.manifest["transport_file"])
        self.assertEqual(transport["kind"], "synthetic")
        self.assertEqual(
            {case["status"] for case in transport["cases"]}, {None, 302, 304, 429, 503}
        )
        for case in transport["cases"]:
            self.assertIsNone(case["body"])
            self.assertLessEqual(set(case["headers"]), {"ETag", "Retry-After", "Location"})

    def test_fixture_paths_cannot_escape_the_library(self):
        for name in (
            "../outside",
            "/outside",
            ".local/data",
            "feeds/../../outside",
            "feeds\\outside",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                read_bytes(name)

    def test_all_data_loads_offline(self):
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("network prohibited")):
            for case in self.manifest["cases"]:
                read_bytes(case["path"])
            for recipe in self.manifest["recipes"]:
                recipe_bytes(recipe)
            for name in self.manifest["views"]:
                read_json(name)

    def test_static_cases_use_only_reserved_or_standard_namespace_urls(self):
        allowed = {"example.com", "example.org", "example.net", "example.invalid", "www.w3.org"}
        for case in self.manifest["cases"]:
            text = read_bytes(case["path"]).decode(case["encoding"], errors="strict")
            for url in re.findall(r'https?://[^\s<>"\']+', text):
                self.assertIn(urlsplit(url).hostname, allowed)
            self.assertIsNone(re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text))


if __name__ == "__main__":
    unittest.main()
