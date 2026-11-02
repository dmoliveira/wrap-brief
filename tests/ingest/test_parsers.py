from __future__ import annotations

import socket
import unittest
from dataclasses import FrozenInstanceError, asdict
from unittest.mock import patch

from fixtures.support import read_bytes, read_json, recipe_bytes

from wrap_brief.config import SourceRegistry
from wrap_brief.ingest.parsers import EntryIssue, FeedLimits, FeedParseError, parse_feed


class ParserTests(unittest.TestCase):
    def test_dtd_without_entities_is_still_forbidden(self):
        with self.assertRaises(FeedParseError) as caught:
            parse_feed(b"<!DOCTYPE rss><rss><channel/></rss>", self.sources["demo-a"])
        self.assertEqual(caught.exception.code, "xml_security")

    def test_invalid_title_markup_is_quarantined_without_raw_errors(self):
        data = b"<rss><channel><item><title><![CDATA[<![synthetic-private-markup]>]]></title><link>https://example.com/a</link></item><item><title>Surviving synthetic title</title><link>https://example.com/b</link></item></channel></rss>"
        result = parse_feed(data, self.sources["demo-a"])
        self.assertEqual(result.issues, (EntryIssue(0, "invalid_title"),))
        self.assertEqual(len(result.entries), 1)
        self.assertNotIn("synthetic-private-markup", repr(result))

    def test_unreviewed_formats_and_title_types_are_not_guessed(self):
        for data in (b"<feed><entry/></feed>", b'<rss version="9.0"><channel/></rss>'):
            with self.assertRaises(FeedParseError) as caught:
                parse_feed(data, self.sources["demo-a"])
            self.assertEqual(caught.exception.code, "unsupported_feed")
        data = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title type="application/octet-stream">Unsupported</title><link href="https://example.org/a"/></entry></feed>'
        self.assertEqual(
            parse_feed(data, self.sources["demo-b"]).issues, (EntryIssue(0, "invalid_title"),)
        )

    def test_limits_subclass_cannot_bypass_hard_caps(self):
        class UnsafeLimits(FeedLimits):
            def __post_init__(self):
                pass

        with self.assertRaises(FeedParseError) as caught:
            parse_feed(
                b"<rss><channel/></rss>",
                self.sources["demo-a"],
                limits=UnsafeLimits(max_bytes=99_999_999),
            )
        self.assertEqual(caught.exception.code, "invalid_limits")

    def setUp(self):
        self.manifest = read_json("manifest.json")
        self.sources = {
            s.id: s for s in SourceRegistry.from_dict(read_json("sources.json")).sources
        }

    def test_all_shared_cases_match_exact_metadata_or_rejection(self):
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]):
                expected = case["expected"]
                if "error" in expected:
                    with self.assertRaises(FeedParseError) as caught:
                        parse_feed(read_bytes(case["path"]), self.sources[case["source_id"]])
                    self.assertEqual(caught.exception.code, expected["error"])
                    continue
                parsed = parse_feed(read_bytes(case["path"]), self.sources[case["source_id"]])
                self.assertEqual([asdict(v) for v in parsed.entries], expected["entries"])
                self.assertEqual(
                    [asdict(v) for v in parsed.issues], expected.get("item_issues", [])
                )

    def test_all_limit_recipes_reject_before_output(self):
        for recipe in self.manifest["recipes"]:
            with self.subTest(recipe=recipe["id"]), self.assertRaises(FeedParseError) as caught:
                parse_feed(recipe_bytes(recipe), self.sources["demo-a"])
            self.assertEqual(caught.exception.code, recipe["expected_error"])

    def test_no_network_for_entities_or_enclosures(self):
        source = self.sources["demo-a"]
        with (
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("network prohibited")),
            patch("urllib.request.urlopen", side_effect=AssertionError("request prohibited")),
        ):
            for name in ("external-entity", "entity", "hostile-description"):
                case = next(c for c in self.manifest["cases"] if c["id"] == name)
                try:
                    parse_feed(read_bytes(case["path"]), source)
                except FeedParseError as error:
                    self.assertEqual(error.code, "xml_security")

    def test_nested_fake_entries_are_not_articles(self):
        data = b"<rss><channel><description><item><title>Nested probe</title><link>https://example.com/fake</link></item></description></channel></rss>"
        self.assertEqual(parse_feed(data, self.sources["demo-a"]).entries, ())
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><content><entry><title>Nested</title><link href="https://example.org/fake"/></entry></content></feed>'
        self.assertEqual(parse_feed(atom, self.sources["demo-b"]).entries, ())

    def test_titles_are_bounded_plain_metadata_not_body_or_script(self):
        data = b"<rss><channel><item><title><![CDATA[Fictional <b>styled</b> <script>neverExpose()</script> &amp; safe]]></title><link>https://example.com/safe</link><description>synthetic-hidden-body</description></item></channel></rss>"
        result = parse_feed(data, self.sources["demo-a"])
        self.assertEqual(result.entries[0].title, "Fictional styled  & safe")
        self.assertNotIn("neverExpose", repr(result))
        self.assertNotIn("synthetic-hidden-body", repr(result))
        self.assertEqual(
            set(asdict(result.entries[0])),
            {"source_id", "title", "url", "guid", "published", "updated"},
        )

    def test_metadata_is_provisional_and_dates_are_not_fabricated(self):
        case = next(c for c in self.manifest["cases"] if c["id"] == "atom-basic")
        result = parse_feed(read_bytes(case["path"]), self.sources["demo-b"])
        self.assertIsNone(result.entries[1].published)
        self.assertEqual(result.entries[1].updated, "2026-01-01T18:00:00Z")
        unsafe = next(c for c in self.manifest["cases"] if c["id"] == "unsafe-link")
        self.assertEqual(
            parse_feed(read_bytes(unsafe["path"]), self.sources["demo-a"]).entries[0].url,
            "javascript:synthetic",
        )

    def test_hard_caps_and_invalid_inputs_cannot_be_disabled(self):
        for field, value in (
            ("max_bytes", 2_097_153),
            ("max_depth", 65),
            ("max_items", 101),
            ("max_text", 4097),
            ("max_nodes", 10_001),
            ("max_items", True),
            ("max_depth", 0),
        ):
            with self.subTest(field=field), self.assertRaises(FeedParseError) as caught:
                FeedLimits(**{field: value})
            self.assertEqual(caught.exception.code, "invalid_limits")
        for value in (None, "<rss/>", bytearray(b"<rss/>")):
            with self.assertRaises(FeedParseError) as caught:
                parse_feed(value, self.sources["demo-a"])
            self.assertEqual(caught.exception.code, "invalid_input")
        with self.assertRaises(FeedParseError):
            parse_feed(b"<rss/>", None)

    def test_smaller_budgets_and_total_nodes_apply(self):
        data = b"<rss><channel><item><title>Fictional</title><link>https://example.com/a</link></item></channel></rss>"
        for limits, code in (
            (FeedLimits(max_bytes=10), "size_limit"),
            (FeedLimits(max_depth=2), "depth_limit"),
            (FeedLimits(max_text=3), "text_limit"),
            (FeedLimits(max_nodes=2), "node_limit"),
        ):
            with self.subTest(code=code), self.assertRaises(FeedParseError) as caught:
                parse_feed(data, self.sources["demo-a"], limits=limits)
            self.assertEqual(caught.exception.code, code)

    def test_unsafe_dtds_are_rejected_even_in_utf16(self):
        xml = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE rss [<!ENTITY probe "synthetic">]><rss><channel/></rss>'
        with self.assertRaises(FeedParseError) as caught:
            parse_feed(xml.encode("utf-16"), self.sources["demo-a"])
        self.assertEqual(caught.exception.code, "xml_security")

    def test_structural_errors_and_messages_do_not_echo_values(self):
        for data, code in (
            (b"<rss/>", "unsupported_feed"),
            (b"<rss><channel/><channel/></rss>", "unsupported_feed"),
            (b"<rss><channel><title>synthetic-private-marker</channel>", "malformed_xml"),
            (
                b'<?xml version="1.0" encoding="synthetic-unknown"?><rss><channel/></rss>',
                "malformed_xml",
            ),
        ):
            with self.subTest(code=code), self.assertRaises(FeedParseError) as caught:
                parse_feed(data, self.sources["demo-a"])
            self.assertEqual(caught.exception.code, code)
            self.assertLess(len(str(caught.exception)), 100)
            self.assertNotIn("synthetic-private-marker", str(caught.exception))
        self.assertEqual(FeedParseError("synthetic" * 10_000).code, "invalid_input")

    def test_results_and_issues_are_immutable(self):
        result = parse_feed(b"<rss><channel><item/></channel></rss>", self.sources["demo-a"])
        self.assertEqual(result.issues, (EntryIssue(0, "missing_title"),))
        with self.assertRaises(FrozenInstanceError):
            result.format = "changed"


if __name__ == "__main__":
    unittest.main()
