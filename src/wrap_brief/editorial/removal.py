"""Bounded operator removal reports; receipts are not physical or provider erasure proof."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from wrap_brief.editorial.controls import _canonical, _dated, public_reference
from wrap_brief.models import (
    ContractError,
    _check,
    _choice,
    _identifier,
    _Record,
    _shape,
    _utc,
    _version,
)
from wrap_brief.state.snapshot import _invalid_number, _unique_object

SURFACES = frozenset(
    {
        "private_records",
        "private_exports",
        "private_backups",
        "public_html",
        "public_json",
        "public_rss",
        "deployment_artifacts",
        "owned_caches",
    }
)
MAX_REPORT_BYTES = 32_768


@dataclass(frozen=True, slots=True, repr=False)
class SurfaceRemoval(_Record):
    surface: str
    status: str
    matched_before: int
    remaining: int
    checked_at: datetime
    evidence_ref: str
    schema_version: int = 1

    _time_fields: ClassVar[tuple[str, ...]] = ("checked_at",)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _choice(self.surface, set(SURFACES), "surface")
        _choice(self.status, {"removed", "not_configured", "pending", "failed"}, "status")
        for value in (self.matched_before, self.remaining):
            _check(
                type(value) is int and 0 <= value <= 1_000_000,
                "counts",
                "bounded nonnegative integer required",
            )
        _check(self.remaining <= self.matched_before, "counts", "inconsistent observation")
        if self.status == "removed":
            _check(
                self.matched_before > 0 and self.remaining == 0,
                "status",
                "removal needs before/after evidence",
            )
        elif self.status == "not_configured":
            _check(
                self.matched_before == self.remaining == 0,
                "status",
                "unconfigured surface has no matched objects",
            )
        object.__setattr__(self, "checked_at", _utc(self.checked_at, "checked_at"))
        public_reference(self.evidence_ref)


@dataclass(frozen=True, slots=True, repr=False)
class RemovalReport:
    id: str
    scope: str
    checked_at: datetime
    outcomes: tuple[SurfaceRemoval, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.id, "id")
        _choice(self.scope, {"owned_synthetic_sandbox", "operator_reported"}, "scope")
        object.__setattr__(self, "checked_at", _utc(self.checked_at, "checked_at"))
        _check(
            type(self.outcomes) is tuple
            and len(self.outcomes) == len(SURFACES)
            and all(type(value) is SurfaceRemoval for value in self.outcomes),
            "outcomes",
            "exhaustive immutable outcomes required",
        )
        _check(
            {value.surface for value in self.outcomes} == SURFACES,
            "outcomes",
            "missing or duplicate surface",
        )
        _check(
            all(value.checked_at <= self.checked_at for value in self.outcomes),
            "checked_at",
            "future surface check",
        )
        object.__setattr__(
            self, "outcomes", tuple(sorted(self.outcomes, key=lambda value: value.surface))
        )
        self.to_json()

    @property
    def resolved(self) -> bool:
        """Declared scope has no outstanding outcome; not_configured never means erased."""
        return all(value.status in {"removed", "not_configured"} for value in self.outcomes)

    def require_resolved(self) -> None:
        _check(self.resolved, "removal", "pending or failed surface")

    def to_json(self) -> bytes:
        data = _canonical(
            {
                "schema_version": self.schema_version,
                "id": self.id,
                "scope": self.scope,
                "checked_at": self.checked_at.isoformat().replace("+00:00", "Z"),
                "outcomes": [value.to_dict() for value in self.outcomes],
            }
        )
        _check(len(data) <= MAX_REPORT_BYTES, "removal", "report limit")
        return data

    @classmethod
    def from_json(cls, value: bytes) -> RemovalReport:
        _check(
            type(value) is bytes and len(value) <= MAX_REPORT_BYTES,
            "removal",
            "bounded bytes required",
        )
        try:
            raw = json.loads(
                value.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_number,
            )
        except (UnicodeError, ValueError, RecursionError):
            raise ContractError("removal: invalid JSON") from None
        fields = {"schema_version", "id", "scope", "checked_at", "outcomes"}
        data = _shape(raw, fields, fields, "removal")
        _check(
            type(data["outcomes"]) is list and len(data["outcomes"]) == len(SURFACES),
            "outcomes",
            "exhaustive array required",
        )
        data["outcomes"] = tuple(SurfaceRemoval.from_dict(row) for row in data["outcomes"])
        data["checked_at"] = _dated(data["checked_at"], "checked_at")
        return cls(**data)
