from __future__ import annotations

import json
import socket
import unittest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from wrap_brief.models import (
    Cluster,
    ContractError,
    Item,
    Source,
    validate_https_url,
    validate_references,
)

NOW = datetime(2026, 1, 2, 12, tzinfo=UTC)


def source(**changes) -> Source:
    defaults = dict(
        id="demo",
        name="Synthetic Publisher",
        site_url="https://example.com/",
        feed_url="https://example.com/feed",
        allowed_hosts=("example.com",),
        attribution="Synthetic test data",
    )
    defaults.update(changes)
    return Source(**defaults)


def item(**changes) -> Item:
    defaults = dict(
        id="demo-item",
        source_id="demo",
        title="Fictional development headline",
        url="https://example.com/story",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    defaults.update(changes)
    return Item(**defaults)


def cluster(**changes) -> Cluster:
    defaults = dict(id="demo-group", member_ids=("demo-item",), lead_id="demo-item")
    defaults.update(changes)
    return Cluster(**defaults)


class ModelTests(unittest.TestCase):
    def test_formatting_controls_rejected_but_emoji_joiners_preserved(self):
        for (
            character
        ) in "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u2028\u2029":
            text = "synthetic" + character + "text"
            for factory, field in (
                (item, "title"),
                (item, "guid"),
                (source, "name"),
                (source, "attribution"),
                (source, "region"),
            ):
                with (
                    self.subTest(character=ord(character), field=field),
                    self.assertRaises(ContractError),
                ):
                    factory(**{field: text})
        title = "Synthetic astronaut 👩‍🚀"
        self.assertEqual(item(title=title).title, title)

    def test_version_one_compatibility_fixture(self):
        data = json.loads((Path(__file__).parent / "fixtures/v1.json").read_text())
        self.assertEqual(data["schema_version"], 1)
        sources = [Source.from_dict(v) for v in data["sources"]]
        items = [Item.from_dict(v) for v in data["items"]]
        clusters = [Cluster.from_dict(v) for v in data["clusters"]]
        validate_references(sources, items, clusters)
        self.assertEqual([s.to_dict() for s in sources], data["sources"])
        self.assertEqual([i.to_dict() for i in items], data["items"])
        self.assertEqual([c.to_dict() for c in clusters], data["clusters"])

    def test_item_cannot_impersonate_a_different_publisher_host(self):
        with self.assertRaises(ContractError):
            validate_references(
                [source()], [item(url="https://elsewhere.example.org/story")], [cluster()]
            )

    def test_round_trip_and_stable_json(self):
        for value in (source(), item(), cluster()):
            with self.subTest(record=type(value).__name__):
                data = value.to_dict()
                restored = type(value).from_dict(json.loads(json.dumps(data)))
                self.assertEqual(value, restored)
                self.assertEqual(json.dumps(data), json.dumps(restored.to_dict()))

    def test_frozen_records_and_independent_serialization(self):
        original = source()
        with self.assertRaises(FrozenInstanceError):
            original.name = "changed"
        self.assertFalse(hasattr(original, "__dict__"))
        data = original.to_dict()
        data["allowed_hosts"].append("different.example.org")
        self.assertEqual(original.allowed_hosts, ("example.com",))

    def test_no_network_for_construction(self):
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("network prohibited")):
            validate_references([source()], [item()], [cluster()])

    def test_unknown_publication_stays_null(self):
        record = item()
        self.assertIsNone(record.published_at)
        self.assertIsNone(record.to_dict()["published_at"])
        self.assertEqual(record.to_dict()["first_seen_at"], "2026-01-02T12:00:00Z")

    def test_utc_normalization(self):
        offset = datetime(2026, 1, 2, 14, tzinfo=timezone(timedelta(hours=2)))
        record = item(first_seen_at=offset, last_seen_at=offset, published_at=offset)
        self.assertEqual(record.first_seen_at, NOW)
        self.assertIs(record.published_at.tzinfo, UTC)
        self.assertEqual(record.to_dict()["published_at"], "2026-01-02T12:00:00Z")

    def test_naive_and_invalid_timestamps(self):
        for value in (datetime(2026, 1, 2), "secret-input", False):
            with self.subTest(value=value), self.assertRaises(ContractError):
                item(first_seen_at=value)
        data = item().to_dict()
        data["first_seen_at"] = "sensitive-invalid-time"
        with self.assertRaises(ContractError) as caught:
            Item.from_dict(data)
        self.assertNotIn("sensitive-invalid-time", str(caught.exception))

    def test_seen_and_update_order(self):
        with self.assertRaises(ContractError):
            item(last_seen_at=NOW - timedelta(seconds=1))
        with self.assertRaises(ContractError):
            item(published_at=NOW, updated_at=NOW - timedelta(seconds=1))

    def test_strict_versions_and_unknown_fields(self):
        for value in (source(), item(), cluster()):
            for version in (True, 2, "1", None):
                data = value.to_dict()
                data["schema_version"] = version
                with self.subTest(version=version), self.assertRaises(ContractError):
                    type(value).from_dict(data)
            data = value.to_dict()
            del data["schema_version"]
            with self.assertRaises(ContractError):
                type(value).from_dict(data)
            for field in ("body", "description", "image_url", "credentials", "editorial_text"):
                data = value.to_dict()
                data[field] = "not permitted"
                with self.subTest(field=field), self.assertRaises(ContractError):
                    type(value).from_dict(data)

    def test_disabled_source_and_dated_approval(self):
        self.assertFalse(source().enabled)
        with self.assertRaises(ContractError):
            source(enabled=True)
        with self.assertRaises(ContractError):
            source(approval_status="approved")
        approved = source(
            enabled=True,
            approval_status="approved",
            approval_ref="https://example.org/policy#metadata",
            reviewed_at=NOW,
        )
        self.assertEqual(Source.from_dict(approved.to_dict()), approved)
        with self.assertRaises(ContractError):
            source(enabled=1)

    def test_public_references_only(self):
        for ref in (
            "../outside.md",
            "/private/policy",
            "javascript:bad",
            ".",
            "docs/../policy.md",
            "docs/private%2fpolicy.md",
        ):
            with self.subTest(ref=ref), self.assertRaises(ContractError):
                source(approval_ref=ref)
        self.assertEqual(
            source(approval_ref="docs/sources/demo.md").approval_ref, "docs/sources/demo.md"
        )

    def test_host_allowlist_normalization_and_mismatch(self):
        self.assertEqual(source(allowed_hosts=("EXAMPLE.COM.",)).allowed_hosts, ("example.com",))
        with self.assertRaises(ContractError):
            source(allowed_hosts=("example.org",))
        with self.assertRaises(ContractError):
            source(allowed_hosts=("EXAMPLE.COM", "example.com"))
        with self.assertRaises(ContractError):
            source(allowed_hosts=["example.com"])

    def test_invalid_shapes_and_choices_are_bounded_errors(self):
        for value, field in (
            (source(), "approval_status"),
            (item(), "status"),
            (item(), "claim_status"),
            (cluster(), "confidence"),
            (cluster(), "correction_status"),
        ):
            for invalid in ([], {}, None, 1, "unsupported"):
                data = value.to_dict()
                data[field] = invalid
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ContractError):
                    type(value).from_dict(data)

    def test_safe_text_is_data_not_editorial_or_html(self):
        record = item(title="Synthetic <angle> & Unicode 🎮")
        self.assertEqual(Item.from_dict(record.to_dict()).title, record.title)
        for title in ("", " padded ", "bad\nline", "bad\u0085line", "bad\ud800text", "x" * 501):
            with self.subTest(title=title[:20]), self.assertRaises(ContractError):
                item(title=title)

    def test_identifier_and_tuple_bounds(self):
        for value in ("", "../file", "Bad ID", "x" * 129, True):
            with self.subTest(value=value), self.assertRaises(ContractError):
                item(id=value)
        for members in (
            (),
            ("demo-item", "demo-item"),
            ["demo-item"],
            tuple(f"item-{i}" for i in range(101)),
        ):
            with self.subTest(members=type(members).__name__), self.assertRaises(ContractError):
                cluster(member_ids=members)

    def test_lead_membership_and_manual_provenance(self):
        with self.assertRaises(ContractError):
            cluster(lead_id="unknown")
        with self.assertRaises(ContractError):
            cluster(confidence="manual")
        self.assertEqual(
            cluster(confidence="manual", override_ref="config/overrides/demo.json").confidence,
            "manual",
        )

    def test_cross_record_reference_failures(self):
        for sources, items, clusters in (
            ([], [item()], []),
            ([source(), source()], [], []),
            ([source()], [item(), item()], []),
            ([source()], [], [cluster()]),
            ([source()], [item()], [cluster(), cluster()]),
        ):
            with (
                self.subTest(counts=(len(sources), len(items), len(clusters))),
                self.assertRaises(ContractError),
            ):
                validate_references(sources, items, clusters)

    def test_removed_or_missing_leads(self):
        for status in ("removed", "retracted", "quarantined"):
            with self.subTest(status=status), self.assertRaises(ContractError):
                validate_references([source()], [item(status=status)], [cluster()])
        validate_references(
            [source()],
            [item(status="removed")],
            [cluster(lead_id=None, correction_status="retracted")],
        )
        with self.assertRaises(ContractError):
            validate_references([source()], [item()], [cluster(lead_id=None)])

    def test_rumor_and_confirmation_do_not_gain_false_labels(self):
        with self.assertRaises(ContractError):
            validate_references([source()], [item(claim_status="rumor")], [cluster()])
        with self.assertRaises(ContractError):
            validate_references([source()], [item()], [cluster(claim_status="confirmed")])
        validate_references(
            [source()], [item(claim_status="rumor")], [cluster(claim_status="rumor")]
        )


class UrlTests(unittest.TestCase):
    def test_error_label_cannot_be_supplied_by_input(self):
        marker = "synthetic-private-marker" * 100_000
        with self.assertRaises(TypeError) as caught:
            validate_https_url("invalid", field=marker)
        self.assertLess(len(str(caught.exception)), 200)
        self.assertNotIn("synthetic-private-marker", str(caught.exception))

    def test_valid_urls_keep_meaningful_queries(self):
        value = "https://example.com/story?edition=2&utm_source=fixture"
        self.assertEqual(validate_https_url(value), value)
        self.assertEqual(
            validate_https_url("https://example.com:443/story"), "https://example.com:443/story"
        )

    def test_unsafe_url_matrix(self):
        urls = [
            "http://example.com/a",
            "javascript:alert(1)",
            "data:text/plain,example",
            "/relative",
            "https://user:pass@example.com/a",
            "https://@example.com",
            "https://example.com:8443/a",
            "https://localhost/a",
            "https://localhost./a",
            "https://127.0.0.1/a",
            "https://[::1]/a",
            "https://169.254.169.254/a",
            "https://metadata.google.internal/a",
            "https://example.local/a",
            "https://2130706433/a",
            "https://127.1/a",
            "https://example.com../a",
            "https://bad_host.example/a",
            "https://example.com/a#fragment",
            "https://example.com/a?access_token=private-value",
            "https://example.com/a?API-KEY=private-value",
            " https://example.com",
            "https://example.com/a b",
            "https://example.com/\nvalue",
            "https://example.com\\evil/a",
            "https://[invalid/a",
        ]
        urls.extend(f"https://example.com/a{character}b" for character in "\"'<>`")
        for value in urls:
            with self.subTest(url=value), self.assertRaises(ContractError) as caught:
                validate_https_url(value)
            self.assertNotIn("private-value", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
