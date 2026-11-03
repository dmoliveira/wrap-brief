"""Bounded hand-authored synthetic recipe loader, not a generic publisher-data loader."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from wrap_brief.grouping.benchmark import GoldScenario
from wrap_brief.grouping.identity import stable_item_id
from wrap_brief.grouping.stories import LeadEvidence
from wrap_brief.models import (
    ContractError,
    Item,
    Source,
    _check,
    _identifier,
    _shape,
    _utc,
    _version,
)
from wrap_brief.state.snapshot import Snapshot, _invalid_number, _unique_object

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures/scenarios.json"
MAX_BYTES = 65_536
LABEL_REF = "tests/benchmarks/README.md#labels"


def _date(value):
    _check(type(value) is str, "fixture", "ISO clock required")
    try:
        return _utc(datetime.fromisoformat(value), "fixture")
    except ValueError:
        raise ContractError("fixture: invalid clock") from None


def parse_fixture(raw: bytes) -> tuple[datetime, tuple[GoldScenario, ...]]:
    _check(type(raw) is bytes and len(raw) <= MAX_BYTES, "fixture", "bounded bytes required")
    try:
        data = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_number
        )
    except (UnicodeError, ValueError, RecursionError):
        raise ContractError("fixture: invalid JSON") from None
    keys = {"schema_version", "kind", "observed_at", "scenarios"}
    data = _shape(data, keys, keys, "fixture")
    _version(data["schema_version"])
    _check(data["kind"] == "synthetic", "fixture", "synthetic recipes only")
    at = _date(data["observed_at"])
    _check(
        type(data["scenarios"]) is list and 0 < len(data["scenarios"]) <= 50,
        "fixture",
        "bounded scenarios required",
    )
    scenarios = []
    for value in data["scenarios"]:
        keys = {"id", "category", "rationale", "gold_groups", "items"}
        value = _shape(value, keys, keys, "scenario")
        _identifier(value["id"], "scenario_id")
        _check(
            type(value["items"]) is list and 2 <= len(value["items"]) <= 50,
            "fixture",
            "bounded item recipe required",
        )
        sources, items, mapping = [], [], {}
        for row in value["items"]:
            row = _shape(
                row,
                {"id", "title", "url", "published_at", "updated_at", "claim_status", "status"},
                {"id", "title"},
                "recipe",
            )
            key = row["id"]
            _identifier(key, "item_id")
            _check(key not in mapping, "fixture", "duplicate recipe ID")
            source_id = "bench-" + key
            sources.append(
                Source(
                    source_id,
                    "Fictional benchmark channel " + key,
                    "https://example.com/",
                    f"https://example.com/benchmark/feed-{key}",
                    ("example.com",),
                    "Hand-authored fictional benchmark only",
                )
            )
            url = row.get("url", f"https://example.com/{value['id']}/{key}")
            published = row.get("published_at", "2026-01-04T10:00:00Z")
            updated = row.get("updated_at")
            current = Item(
                stable_item_id(source_id, url),
                source_id,
                row["title"],
                url,
                at,
                at,
                published_at=_date(published) if published is not None else None,
                updated_at=_date(updated) if updated is not None else None,
                status=row.get("status", "active"),
                claim_status=row.get("claim_status", "reported"),
            )
            items.append(current)
            mapping[key] = current.id
        parts = value["gold_groups"]
        _check(
            type(parts) is list
            and 0 < len(parts) <= 50
            and all(type(part) is list and 0 < len(part) <= 50 for part in parts),
            "gold_groups",
            "bounded arrays required",
        )
        _check(
            all(type(key) is str and key in mapping for part in parts for key in part),
            "gold_groups",
            "unknown recipe ID",
        )
        state = Snapshot(at, tuple(sources), tuple(items))
        scenarios.append(
            GoldScenario(
                value["id"],
                value["category"],
                state,
                tuple(LeadEvidence(item.id) for item in items),
                tuple(tuple(mapping[key] for key in part) for part in parts),
                value["rationale"],
                LABEL_REF,
                at,
            )
        )
    return at, tuple(scenarios)


def load_fixture() -> tuple[datetime, tuple[GoldScenario, ...]]:
    _check(
        not FIXTURE.is_symlink() and FIXTURE.resolve().is_relative_to(ROOT.resolve()),
        "fixture",
        "owned recipe required",
    )
    with FIXTURE.open("rb") as stream:
        return parse_fixture(stream.read(MAX_BYTES + 1))
