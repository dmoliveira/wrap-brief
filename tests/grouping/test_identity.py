from __future__ import annotations

import socket
import unittest
from datetime import UTC, datetime
from functools import partial
from unittest.mock import patch

from fixtures.support import read_bytes, read_json

from wrap_brief.config import SourceRegistry
from wrap_brief.grouping.identity import TRACKING_PARAMETERS, canonical_url, stable_item_id
from wrap_brief.ingest.normalize import normalize_entry
from wrap_brief.ingest.parsers import RawEntry, parse_feed
from wrap_brief.models import ContractError


class IdentityTests(unittest.TestCase):
    def test_reviewed_tracking_allowlist_is_exact(self):
        self.assertEqual(
            TRACKING_PARAMETERS,
            frozenset(
                {
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                    "utm_term",
                    "utm_content",
                    "utm_id",
                    "gclid",
                    "dclid",
                    "fbclid",
                    "msclkid",
                    "mc_cid",
                    "mc_eid",
                }
            ),
        )

    def test_url_v1_namespace_golden_vector(self):
        self.assertEqual(
            stable_item_id("demo-a", "https://example.com/Article?edition=2&utm_source=fixture"),
            "item-v1-c015b069705fd0094ca128d75fa10b58dfb16e2cf9d2ccaf79343425a98b3c8d",
        )

    def test_source_scoping_and_guid_changes_or_collisions(self):
        url = "https://example.com/article"
        identity = stable_item_id("demo-a", url)
        self.assertEqual(identity, stable_item_id("demo-a", url, "changed-guid"))
        self.assertNotEqual(identity, stable_item_id("demo-b", url))
        self.assertNotEqual(
            stable_item_id("demo-a", url, "same-guid"),
            stable_item_id("demo-a", url + "-different", "same-guid"),
        )
        self.assertRegex(identity, r"^item-v1-[0-9a-f]{64}$")

    def test_known_tracking_variants_deduplicate(self):
        base = "https://example.com/Article?edition=2"
        for key in TRACKING_PARAMETERS:
            with self.subTest(key=key):
                variant = base + "&" + key + "=synthetic"
                self.assertEqual(canonical_url(variant), base)
                self.assertEqual(stable_item_id("demo-a", variant), stable_item_id("demo-a", base))
        self.assertEqual(
            canonical_url("https://example.com/a?utm_source=synthetic"), "https://example.com/a"
        )

    def test_only_exact_case_sensitive_reviewed_keys_are_removed(self):
        url = "https://example.com/a?UTM_SOURCE=keep&utm_custom=keep&ref=keep&source=keep&id=2&lang=ja&page=3"
        self.assertEqual(canonical_url(url), url)
        self.assertNotEqual(
            stable_item_id("demo-a", url), stable_item_id("demo-a", "https://example.com/a")
        )

    def test_unknown_query_bytes_order_blanks_and_repeats_are_preserved(self):
        vectors = [
            "q=a+b&q=a%20b",
            "x=%2f&x=%2F",
            "id=1&&empty=&flag",
            "q=%FF&x=%ZZ",
            "utm+source=keep",
            "utm%2Bsource=keep",
        ]
        for query in vectors:
            url = "https://example.com/a?" + query
            with self.subTest(query=query):
                self.assertEqual(canonical_url(url), url)
        self.assertNotEqual(
            stable_item_id("demo-a", "https://example.com/a?id=1&id=2"),
            stable_item_id("demo-a", "https://example.com/a?id=2&id=1"),
        )

    def test_percent_encoded_known_key_only_is_decoded_for_comparison(self):
        self.assertEqual(
            canonical_url("https://example.com/a?x=a%2fb&%75tm_source=synthetic&y=a+b"),
            "https://example.com/a?x=a%2fb&y=a+b",
        )
        self.assertEqual(
            canonical_url("https://example.com/a?utm_source=synthetic%26id%3Dother"),
            "https://example.com/a",
        )

    def test_empty_query_structure_is_not_guessed_away(self):
        for ending in ("?", "?&", "?&&", "?id=&flag"):
            url = "https://example.com/a" + ending
            self.assertEqual(canonical_url(url), url)
        self.assertEqual(
            canonical_url("https://example.com/a?utm_source=x&"), "https://example.com/a?"
        )
        self.assertNotEqual(
            stable_item_id("demo-a", "https://example.com/a"),
            stable_item_id("demo-a", "https://example.com/a?"),
        )

    def test_host_spelling_default_port_and_ip_literals(self):
        self.assertEqual(
            canonical_url("HTTPS://EXAMPLE.COM.:443/A%2fb/"), "https://example.com/A%2fb/"
        )
        self.assertEqual(
            canonical_url("https://bücher.example.org/A"), "https://xn--bcher-kva.example.org/A"
        )
        self.assertEqual(
            canonical_url("https://[2606:4700:4700:0000:0000:0000:0000:1111]:443/a"),
            "https://[2606:4700:4700::1111]/a",
        )
        self.assertEqual(canonical_url("https://1.1.1.1:443/a"), "https://1.1.1.1/a")

    def test_path_spelling_remains_distinct(self):
        urls = [
            "https://example.com/A",
            "https://example.com/a",
            "https://example.com/a/",
            "https://example.com/a%2fb",
            "https://example.com/a%2Fb",
            "https://example.com/a/../b",
            "https://example.com/b",
            "https://example.com",
            "https://example.com/",
        ]
        self.assertEqual(len({stable_item_id("demo-a", u) for u in urls}), len(urls))

    def test_policy_is_subset_only_and_source_can_disable_cleanup(self):
        url = "https://example.com/a?utm_source=content-identity"
        self.assertEqual(canonical_url(url, tracking_parameters=frozenset()), url)
        self.assertNotEqual(
            stable_item_id("demo-a", url),
            stable_item_id("demo-a", url, tracking_parameters=frozenset()),
        )
        for policy in (
            set(),
            [],
            None,
            frozenset({"id"}),
            frozenset({"utm_custom"}),
            frozenset({True}),
        ):
            with self.subTest(policy=type(policy).__name__), self.assertRaises(ContractError):
                canonical_url(url, tracking_parameters=policy)

    def test_invalid_inputs_do_not_echo_values(self):
        for source in (None, True, "Bad ID", "../outside", "x" * 129):
            with self.assertRaises(ContractError):
                stable_item_id(source, "https://example.com/a")
        for url in (
            None,
            "http://example.com/a",
            "https://example.com/a#raw",
            "https://example.com/a#",
            "https://localhost/a",
            "https://user:synthetic-private@example.com/a",
        ):
            with self.assertRaises(ContractError) as caught:
                stable_item_id("demo-a", url)
            self.assertNotIn("synthetic-private", str(caught.exception))

    def test_normalizer_integration_uses_stable_id_without_mutating_source_link(self):
        source = SourceRegistry.from_dict(read_json("sources.json")).sources[0]
        observed = datetime(2026, 1, 2, 12, 30, tzinfo=UTC)
        raw = RawEntry(
            source.id,
            "Fictional identity probe",
            "https://example.com/a?edition=2&utm_source=fixture#section",
            "same-guid",
        )
        result = normalize_entry(raw, source, observed_at=observed, identity=stable_item_id)
        self.assertEqual(
            result.item.id, stable_item_id(source.id, "https://example.com/a?edition=2")
        )
        self.assertEqual(result.item.url, "https://example.com/a?edition=2&utm_source=fixture")
        policy = partial(stable_item_id, tracking_parameters=frozenset())
        self.assertNotEqual(
            normalize_entry(raw, source, observed_at=observed, identity=policy).item.id,
            result.item.id,
        )

    def test_shared_parser_duplicates_get_same_exact_identity_without_merging_records(self):
        source = SourceRegistry.from_dict(read_json("sources.json")).sources[0]
        parsed = parse_feed(read_bytes("feeds/duplicate.xml"), source)
        observed = datetime(2026, 1, 2, 12, 30, tzinfo=UTC)
        items = [
            normalize_entry(raw, source, observed_at=observed, identity=stable_item_id).item
            for raw in parsed.entries
        ]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].id, items[1].id)

    def test_identity_has_no_network_or_clock_dependency(self):
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("network prohibited")):
            first = stable_item_id("demo-a", "https://example.com/a")
            second = stable_item_id("demo-a", "https://example.com/a")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
