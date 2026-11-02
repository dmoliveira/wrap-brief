"""Complete validated logical state, not transport caches or publisher Git history."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import ClassVar

from wrap_brief.grouping.identity import canonical_url
from wrap_brief.models import (
    SCHEMA_VERSION,
    Cluster,
    ContractError,
    Item,
    Source,
    _check,
    _choice,
    _identifier,
    _Record,
    _shape,
    _text,
    _utc,
    _version,
    validate_references,
)

MAX_SNAPSHOT_BYTES = 16_777_216
MAX_RECORDS = 10_000


@dataclass(frozen=True, slots=True, repr=False)
class PollCheckpoint(_Record):
    """Logical source checkpoint only; no polling or generic/private header dictionary."""

    source_id: str
    last_attempt_at: datetime
    last_success_at: datetime | None = None
    etag: str | None = None
    last_modified: str | None = None
    entry_count: int | None = None
    oldest_published_at: datetime | None = None
    newest_published_at: datetime | None = None
    status: str = "error"
    schema_version: int = SCHEMA_VERSION

    _time_fields: ClassVar[tuple[str, ...]] = (
        "last_attempt_at",
        "last_success_at",
        "oldest_published_at",
        "newest_published_at",
    )

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.source_id, "source_id")
        _choice(self.status, {"ok", "not_modified", "error"}, "checkpoint_status")
        for name in self._time_fields:
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _utc(value, name))
        _check(self.last_attempt_at is not None, "last_attempt_at", "timestamp required")
        _check(
            self.last_success_at is None or self.last_success_at <= self.last_attempt_at,
            "last_success_at",
            "after attempt",
        )
        _check(
            self.status == "error" or self.last_success_at is not None,
            "checkpoint",
            "successful checkpoint needs a time",
        )
        for name, limit in (("etag", 512), ("last_modified", 128)):
            if getattr(self, name) is not None:
                _text(getattr(self, name), name, limit)
        _check(
            self.entry_count is None
            or (type(self.entry_count) is int and 0 <= self.entry_count <= 100),
            "entry_count",
            "invalid count",
        )
        window = self.oldest_published_at, self.newest_published_at
        _check(
            all(v is None for v in window) or all(v is not None for v in window),
            "feed_window",
            "incomplete window",
        )
        if window[0] is not None:
            _check(
                self.entry_count is not None and self.entry_count > 0 and window[0] <= window[1],
                "feed_window",
                "invalid window",
            )
        if self.last_success_at is None:
            _check(
                self.etag is None
                and self.last_modified is None
                and self.entry_count is None
                and window == (None, None),
                "checkpoint",
                "unvalidated success metadata",
            )


@dataclass(frozen=True, slots=True)
class Tombstone(_Record):
    item_id: str
    source_id: str
    removed_at: datetime
    schema_version: int = SCHEMA_VERSION

    _time_fields: ClassVar[tuple[str, ...]] = ("removed_at",)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.item_id, "item_id")
        _identifier(self.source_id, "source_id")
        object.__setattr__(self, "removed_at", _utc(self.removed_at, "removed_at"))


def _tuple_records(value: object, expected: type, field: str, limit: int) -> None:
    _check(
        isinstance(value, tuple) and len(value) <= limit, field, "bounded immutable tuple required"
    )
    _check(all(type(v) is expected for v in value), field, "invalid record type")


@dataclass(frozen=True, slots=True, repr=False)
class Snapshot:
    observed_at: datetime
    sources: tuple[Source, ...] = ()
    items: tuple[Item, ...] = ()
    clusters: tuple[Cluster, ...] = ()
    checkpoints: tuple[PollCheckpoint, ...] = ()
    tombstones: tuple[Tombstone, ...] = ()
    kind: str = "synthetic"
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _choice(self.kind, {"synthetic", "live"}, "kind")
        object.__setattr__(self, "observed_at", _utc(self.observed_at, "observed_at"))
        for name, expected, key, limit in (
            ("sources", Source, "id", 100),
            ("items", Item, "id", MAX_RECORDS),
            ("clusters", Cluster, "id", MAX_RECORDS),
            ("checkpoints", PollCheckpoint, "source_id", 100),
            ("tombstones", Tombstone, "item_id", MAX_RECORDS),
        ):
            records = getattr(self, name)
            _tuple_records(records, expected, name, limit)
            _check(
                len({getattr(v, key) for v in records}) == len(records),
                name,
                "duplicate identifier",
            )
            object.__setattr__(self, name, tuple(sorted(records, key=lambda v: getattr(v, key))))
        object.__setattr__(
            self,
            "sources",
            tuple(replace(s, allowed_hosts=tuple(sorted(s.allowed_hosts))) for s in self.sources),
        )
        object.__setattr__(
            self,
            "clusters",
            tuple(replace(c, member_ids=tuple(sorted(c.member_ids))) for c in self.clusters),
        )
        validate_references(self.sources, self.items, self.clusters)
        source_ids = {s.id for s in self.sources}
        item_ids = {i.id for i in self.items}
        _check(
            all(i.last_seen_at <= self.observed_at for i in self.items),
            "observed_at",
            "precedes item observation",
        )
        for checkpoint in self.checkpoints:
            _check(
                checkpoint.source_id in source_ids
                and checkpoint.last_attempt_at <= self.observed_at,
                "checkpoint",
                "unknown source or future observation",
            )
        for tombstone in self.tombstones:
            _check(
                tombstone.source_id in source_ids and tombstone.removed_at <= self.observed_at,
                "tombstone",
                "unknown source or future observation",
            )
            _check(tombstone.item_id not in item_ids, "tombstone", "full record must be removed")

    def __repr__(self) -> str:
        return "<Snapshot: validated private state>"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "observed_at": self.observed_at.isoformat().replace("+00:00", "Z"),
            **{
                name: [v.to_dict() for v in getattr(self, name)]
                for name in ("sources", "items", "clusters", "checkpoints", "tombstones")
            },
        }

    def to_json(self) -> bytes:
        data = json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        _check(len(data) <= MAX_SNAPSHOT_BYTES, "snapshot", "payload too large")
        return data

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.to_json()).hexdigest()

    @classmethod
    def from_dict(cls, value: object) -> Snapshot:
        required = {"schema_version", "kind", "observed_at", "sources", "items", "clusters"}
        data = _shape(value, required | {"checkpoints", "tombstones"}, required, "snapshot")
        _version(data["schema_version"])
        _check(isinstance(data["observed_at"], str), "observed_at", "timestamp required")
        try:
            observed = datetime.fromisoformat(data["observed_at"])
        except ValueError:
            raise ContractError("observed_at: invalid timestamp") from None
        records = {}
        for name, record, limit in (
            ("sources", Source, 100),
            ("items", Item, MAX_RECORDS),
            ("clusters", Cluster, MAX_RECORDS),
            ("checkpoints", PollCheckpoint, 100),
            ("tombstones", Tombstone, MAX_RECORDS),
        ):
            raw = data.get(name, [])
            _check(isinstance(raw, list) and len(raw) <= limit, name, "bounded array required")
            records[name] = tuple(record.from_dict(v) for v in raw)
        return cls(observed_at=observed, kind=data["kind"], **records)

    @classmethod
    def from_json(cls, value: bytes) -> Snapshot:
        _check(
            type(value) is bytes and len(value) <= MAX_SNAPSHOT_BYTES,
            "snapshot",
            "bounded bytes required",
        )
        try:
            data = json.loads(
                value.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_number,
            )
        except (UnicodeError, json.JSONDecodeError, RecursionError):
            raise ContractError("snapshot: invalid UTF-8 JSON") from None
        return cls.from_dict(data)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        _check(key not in result, "snapshot", "duplicate JSON key")
        result[key] = value
    return result


def _invalid_number(_value: str) -> None:
    raise ContractError("snapshot: non-finite JSON number")


def merge_items(
    existing: Sequence[Item], incoming: Sequence[Item], *, tombstones: Sequence[Tombstone] = ()
) -> tuple[Item, ...]:
    """Pure replay merge: no freshening publication, stale overwrites or tombstone revival."""
    for values, expected in ((existing, Item), (incoming, Item), (tombstones, Tombstone)):
        _check(
            isinstance(values, Sequence) and len(values) <= MAX_RECORDS,
            "merge",
            "bounded sequence required",
        )
        _check(all(type(v) is expected for v in values), "merge", "invalid record")
    removed = {}
    for tombstone in tombstones:
        _check(tombstone.item_id not in removed, "tombstone", "duplicate identifier")
        removed[tombstone.item_id] = tombstone
    merged: dict[str, Item] = {}
    for item in (*existing, *incoming):
        if item.id in removed:
            _check(
                item.source_id == removed[item.id].source_id, "merge", "tombstone source conflict"
            )
            continue
        old = merged.get(item.id)
        if old is None:
            merged[item.id] = item
            continue
        _check(
            old.source_id == item.source_id and canonical_url(old.url) == canonical_url(item.url),
            "merge",
            "identity conflict",
        )
        if old.updated_at is not None or item.updated_at is not None:
            if old.updated_at is None:
                base = item
            elif item.updated_at is None:
                base = old
            elif old.updated_at == item.updated_at:
                base = old if old.last_seen_at > item.last_seen_at else item
            else:
                base = old if old.updated_at > item.updated_at else item
        else:
            base = old if old.last_seen_at > item.last_seen_at else item
        publication = [v for v in (old.published_at, item.published_at) if v is not None]
        updates = [v for v in (old.updated_at, item.updated_at) if v is not None]
        status = (
            "removed"
            if "removed" in {old.status, item.status}
            else "retracted"
            if "retracted" in {old.status, item.status}
            else base.status
        )
        merged[item.id] = replace(
            base,
            first_seen_at=min(old.first_seen_at, item.first_seen_at),
            last_seen_at=max(old.last_seen_at, item.last_seen_at),
            published_at=min(publication) if publication else None,
            updated_at=max(updates) if updates else None,
            status=status,
        )
    _check(len(merged) <= MAX_RECORDS, "merge", "too many retained records")
    return tuple(merged[key] for key in sorted(merged))
