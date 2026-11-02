from __future__ import annotations

import socket
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import Mock, patch

from fixtures.support import read_bytes, read_json

from wrap_brief.config import SourceRegistry
from wrap_brief.ingest.normalize import (
    FUTURE_TOLERANCE,
    NormalizationResult,
    normalize_entry,
    normalize_url,
)
from wrap_brief.ingest.parsers import RawEntry, parse_feed
from wrap_brief.models import ContractError, Item

OBSERVED = datetime(2026, 1, 2, 12, 30, tzinfo=UTC)


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.sources = {
            s.id: s for s in SourceRegistry.from_dict(read_json("sources.json")).sources
        }
        self.source = self.sources["demo-a"]
        self.entry = RawEntry(
            "demo-a", "Fictional headline", "https://example.com/story", "synthetic-guid"
        )

    def normalize(self, entry=None, **changes):
        return normalize_entry(
            entry or self.entry,
            self.source,
            observed_at=changes.pop("observed_at", OBSERVED),
            identity=changes.pop("identity", lambda *_: "synthetic-id"),
            **changes,
        )

    def test_success_is_a_valid_immutable_item_with_observation_provenance(self):
        result = self.normalize()
        self.assertIsInstance(result.item, Item)
        self.assertIsNone(result.rejection)
        self.assertEqual(result.item.id, "synthetic-id")
        self.assertEqual(result.item.first_seen_at, OBSERVED)
        self.assertEqual(result.item.last_seen_at, OBSERVED)
        self.assertIsNone(result.item.published_at)
        with self.assertRaises(FrozenInstanceError):
            result.rejection = "invalid_url"
        self.assertNotIn("Fictional headline", repr(result))

    def test_safe_spacing_is_normalized_but_controls_are_not_erased(self):
        accepted = self.normalize(
            replace(self.entry, title="  Fictional   headline \u00a0 with space  ")
        )
        self.assertEqual(accepted.item.title, "Fictional headline with space")
        for value in (
            "headline\nspoof",
            "headline\tspoof",
            "headline\u2028spoof",
            "headline\u202e.exe",
            "headline\u200f.exe",
            "bad\ud800text",
            "x" * 4097,
            False,
            {},
            "<script>synthetic</script>",
            "<vector> example",
        ):
            with self.subTest(value=type(value).__name__):
                result = self.normalize(replace(self.entry, title=value))
                self.assertEqual(result.rejection, "invalid_title")
        self.assertIsNotNone(
            self.normalize(replace(self.entry, title="Fictional <3 & emoji 👩‍🚀")).item
        )

    def test_url_changes_are_narrow_and_meaningful_parameters_stay(self):
        raw = " https://example.com/story?edition=2&utm_source=fixture&x=1&x=2#section "
        self.assertEqual(
            normalize_url(raw), "https://example.com/story?edition=2&utm_source=fixture&x=1&x=2"
        )
        self.assertEqual(self.normalize(replace(self.entry, url=raw)).item.url, normalize_url(raw))
        for url in (
            "/relative",
            "http://example.com/story",
            "javascript:synthetic",
            "https://127.0.0.1/story",
            "https://example.org/story",
            "https://user:pass@example.com/story",
            "https://exa\nmple.com/story",
            "x" * 4097,
            None,
        ):
            with self.subTest(url=type(url).__name__):
                self.assertEqual(
                    self.normalize(replace(self.entry, url=url)).rejection, "invalid_url"
                )

    def test_rfc_and_iso_dates_normalize_to_utc(self):
        entry = replace(
            self.entry,
            published="Fri, 02 Jan 2026 08:00:00 -0400",
            updated="2026-01-02T13:10:00+01:00",
        )
        result = self.normalize(entry).item
        self.assertEqual(result.published_at, datetime(2026, 1, 2, 12, tzinfo=UTC))
        self.assertEqual(result.updated_at, datetime(2026, 1, 2, 12, 10, tzinfo=UTC))
        self.assertIs(result.published_at.tzinfo, UTC)

    def test_unknown_publication_is_never_filled_from_other_dates(self):
        result = self.normalize(
            replace(self.entry, published=None, updated="2026-01-01T18:00:00Z")
        ).item
        self.assertIsNone(result.published_at)
        self.assertIsNotNone(result.updated_at)
        self.assertEqual(result.first_seen_at, OBSERVED)
        self.assertIsNone(result.to_dict()["published_at"])

    def test_invalid_and_ambiguous_dates_are_quarantined(self):
        for value, code in (
            ("not-a-date", "invalid_date"),
            ("2026-01-02T11:00:00", "ambiguous_date"),
            ("Fri, 02 Jan 2026 11:00:00 -0000", "ambiguous_date"),
            ("Fri, 02 Jan 2026 11:00:00 XYZ", "ambiguous_date"),
            ("x" * 129, "invalid_date"),
            (True, "invalid_date"),
            ("2026-01-02T12:00:00Z\n", "invalid_date"),
        ):
            with self.subTest(value=type(value).__name__):
                self.assertEqual(
                    self.normalize(replace(self.entry, published=value)).rejection, code
                )

    def test_future_tolerance_and_date_range(self):
        boundary = (OBSERVED + FUTURE_TOLERANCE).isoformat()
        self.assertIsNotNone(self.normalize(replace(self.entry, published=boundary)).item)
        future = (OBSERVED + FUTURE_TOLERANCE + timedelta(microseconds=1)).isoformat()
        for field in ("published", "updated"):
            self.assertEqual(
                self.normalize(replace(self.entry, **{field: future})).rejection, "future_date"
            )
        entry = replace(
            self.entry, published="2026-01-02T12:00:00Z", updated="2026-01-02T11:59:59Z"
        )
        self.assertEqual(self.normalize(entry).rejection, "invalid_date_range")

    def test_clock_validation_and_offsets_are_explicit(self):
        offset = OBSERVED.astimezone(timezone(timedelta(hours=2)))
        self.assertEqual(self.normalize(observed_at=offset).item.first_seen_at, OBSERVED)
        for clock in (datetime(2026, 1, 2), None, "2026-01-02"):
            with self.assertRaises(ContractError):
                self.normalize(observed_at=clock)
        self.assertIsNotNone(self.normalize(observed_at=datetime.max.replace(tzinfo=UTC)).item)

    def test_identity_runs_once_only_after_metadata_and_host_validation(self):
        identity = Mock(return_value="assigned-id")
        result = self.normalize(identity=identity)
        identity.assert_called_once_with("demo-a", "https://example.com/story", "synthetic-guid")
        self.assertEqual(result.item.id, "assigned-id")
        for entry in (
            replace(self.entry, source_id="other"),
            replace(self.entry, url="https://example.org/story"),
            replace(self.entry, guid="bad\nvalue"),
            replace(self.entry, published="not-a-date"),
        ):
            rejected_identity = Mock(return_value="assigned-id")
            self.assertIsNone(self.normalize(entry, identity=rejected_identity).item)
            rejected_identity.assert_not_called()

    def test_callback_failures_abort_without_echo_and_candidate_id_never_escapes(self):
        callbacks = [
            Mock(side_effect=RuntimeError("synthetic-private-value")),
            Mock(return_value="../invalid"),
            Mock(return_value=None),
            Mock(return_value="normalization-candidate"),
        ]
        for identity in callbacks:
            with self.assertRaises(ContractError) as caught:
                self.normalize(identity=identity)
            self.assertLess(len(str(caught.exception)), 100)
            self.assertNotIn("synthetic-private-value", str(caught.exception))
        with self.assertRaises(ContractError):
            self.normalize(identity=None)

    def test_guid_and_source_validation(self):
        self.assertIsNone(self.normalize(replace(self.entry, guid="  ")).item.guid)
        for guid in ([], False, "x" * 2049, "bad\u202evalue"):
            self.assertEqual(
                self.normalize(replace(self.entry, guid=guid)).rejection, "invalid_guid"
            )
        self.assertEqual(
            self.normalize(replace(self.entry, source_id="other")).rejection, "source_mismatch"
        )
        with self.assertRaises(ContractError):
            normalize_entry(None, self.source, observed_at=OBSERVED, identity=lambda *_: "id")

    def test_shared_parser_cases_have_the_declared_normalization_outcome(self):
        manifest = read_json("manifest.json")
        categories = {
            "reject_url": {"invalid_url"},
            "reject_date": {"invalid_date", "ambiguous_date"},
            "reject_future": {"future_date"},
            "reject_text": {"invalid_title"},
        }
        for case in manifest["cases"]:
            if "error" in case["expected"]:
                continue
            source = self.sources[case["source_id"]]
            parsed = parse_feed(read_bytes(case["path"]), source)
            for entry in parsed.entries:
                result = normalize_entry(
                    entry, source, observed_at=OBSERVED, identity=lambda *_: "fixture-id"
                )
                expected = case["expected"].get("normalization")
                if expected:
                    self.assertIn(result.rejection, categories[expected])
                else:
                    self.assertIsNotNone(result.item, case["id"])

    def test_no_network_or_clock_lookup_and_no_editorial_confirmation(self):
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("network prohibited")):
            result = self.normalize(replace(self.entry, title="Fictional official rumor"))
        self.assertEqual(result.item.claim_status, "reported")
        self.assertFalse(self.source.enabled)
        self.assertNotIn("Fictional", repr(result))

    def test_result_outcomes_are_exclusive_and_codes_bounded(self):
        for item, code in (
            (None, None),
            (None, []),
            (None, "synthetic" * 10_000),
            (self.normalize().item, "invalid_url"),
        ):
            with self.assertRaises(ContractError):
                NormalizationResult(item, code)


if __name__ == "__main__":
    unittest.main()
