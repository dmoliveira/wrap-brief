"""Current reviewed application controls, not feed-controlled editorial authority."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import ClassVar
from urllib.parse import urlsplit

from wrap_brief.grouping.stories import _feature
from wrap_brief.models import (
    Cluster,
    ContractError,
    Item,
    _check,
    _choice,
    _identifier,
    _Record,
    _reference,
    _shape,
    _utc,
    _version,
)
from wrap_brief.state.snapshot import (
    MAX_RECORDS,
    Snapshot,
    Tombstone,
    _invalid_number,
    _unique_object,
)

MAX_LEDGER_BYTES = 1_048_576
MAX_REVIEWS = 1_000
_AVAILABLE = {"active", "corrected"}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _hash(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\0" + _canonical(value)).hexdigest()


def _hash_field(value: object) -> None:
    _check(
        type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None,
        "metadata_ref",
        "SHA-256 reference required",
    )


def public_reference(value: object) -> str:
    """Syntax only: a reviewer must explicitly approve the reference for publication."""
    reference = _reference(value, "public_reference")
    if reference.startswith("https://"):
        parsed = urlsplit(reference)
        _check(
            not parsed.query and len(reference) <= 1_024,
            "public_reference",
            "query-free citation required",
        )
        _check(
            not parsed.fragment or re.fullmatch(r"[A-Za-z0-9_-]+", parsed.fragment) is not None,
            "public_reference",
            "simple fragment required",
        )
    else:
        _check(
            re.fullmatch(
                r"content/corrections/[a-z0-9][a-z0-9_-]{0,63}\.md(?:#[a-z0-9_-]+)?", reference
            )
            is not None,
            "public_reference",
            "reviewed correction reference required",
        )
    return reference


def metadata_reference(item: Item) -> str:
    """Bind claim-bearing publisher metadata, never observation clocks or incoming flags."""
    _check(type(item) is Item, "claim", "validated item required")
    data = item.to_dict()
    return _hash(
        "wrap-brief:claim-metadata:v1",
        {
            name: data[name]
            for name in ("id", "source_id", "title", "url", "guid", "published_at", "updated_at")
        },
    )


def _group_identifier(member_ids: tuple[str, ...]) -> str:
    return "editorial-group-v1-" + _hash(
        "wrap-brief:editorial-group:v1", {"member_ids": sorted(member_ids)}
    )


def _dated(value: object, field: str) -> datetime:
    _check(type(value) is str, field, "ISO timestamp required")
    try:
        return _utc(datetime.fromisoformat(value), field)
    except ValueError:
        raise ContractError(f"{field}: invalid timestamp") from None


@dataclass(frozen=True, slots=True, repr=False)
class ClaimEvidence(_Record):
    id: str
    source_id: str
    item_id: str
    claim_status: str
    metadata_ref: str
    reviewed_at: datetime
    evidence_ref: str
    schema_version: int = 1

    _time_fields: ClassVar[tuple[str, ...]] = ("reviewed_at",)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        for name in ("id", "source_id", "item_id"):
            _identifier(getattr(self, name), name)
        _choice(self.claim_status, {"reported", "confirmed", "rumor"}, "claim_status")
        _hash_field(self.metadata_ref)
        object.__setattr__(self, "reviewed_at", _utc(self.reviewed_at, "reviewed_at"))
        public_reference(self.evidence_ref)


@dataclass(frozen=True, slots=True, repr=False)
class CorrectionControl(_Record):
    id: str
    source_id: str
    action: str
    reviewed_at: datetime
    item_id: str | None = None
    metadata_ref: str | None = None
    public_notice_ref: str | None = None
    schema_version: int = 1

    _time_fields: ClassVar[tuple[str, ...]] = ("reviewed_at",)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.id, "id")
        _identifier(self.source_id, "source_id")
        _choice(self.action, {"correct", "retract", "erase_item", "exclude_source"}, "action")
        object.__setattr__(self, "reviewed_at", _utc(self.reviewed_at, "reviewed_at"))
        if self.item_id is not None:
            _identifier(self.item_id, "item_id")
        _check(
            (self.action == "exclude_source") == (self.item_id is None),
            "item_id",
            "action target mismatch",
        )
        if self.action == "correct":
            _hash_field(self.metadata_ref)
        else:
            _check(self.metadata_ref is None, "metadata_ref", "not retained for this action")
        if self.action in {"correct", "retract"}:
            public_reference(self.public_notice_ref)
        else:
            _check(
                self.public_notice_ref is None,
                "public_notice_ref",
                "erasure has no public item notice",
            )


@dataclass(frozen=True, slots=True, repr=False)
class ControlLedger:
    id: str
    revision: int
    reviewed_at: datetime
    claims: tuple[ClaimEvidence, ...] = ()
    controls: tuple[CorrectionControl, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.id, "id")
        _check(
            type(self.revision) is int and 0 < self.revision <= 2**63 - 1,
            "revision",
            "positive revision required",
        )
        object.__setattr__(self, "reviewed_at", _utc(self.reviewed_at, "reviewed_at"))
        for name, expected in (("claims", ClaimEvidence), ("controls", CorrectionControl)):
            values = getattr(self, name)
            _check(
                type(values) is tuple
                and len(values) <= MAX_REVIEWS
                and all(type(v) is expected for v in values),
                name,
                "bounded immutable reviews required",
            )
            _check(all(v.reviewed_at <= self.reviewed_at for v in values), name, "future review")
            object.__setattr__(self, name, tuple(sorted(values, key=lambda v: v.id)))
        reviews = (*self.claims, *self.controls)
        _check(
            len({review.id for review in reviews}) == len(reviews), "ledger", "duplicate review ID"
        )
        _check(
            len({value.item_id for value in self.claims}) == len(self.claims),
            "claims",
            "duplicate target",
        )
        targets = [(value.source_id, value.item_id) for value in self.controls]
        _check(len(set(targets)) == len(targets), "controls", "conflicting target")
        item_controls = [value for value in self.controls if value.item_id is not None]
        _check(
            len({value.item_id for value in item_controls}) == len(item_controls),
            "controls",
            "conflicting item source",
        )
        excluded = set(self.excluded_source_ids)
        erased = {value.item_id for value in self.controls if value.action == "erase_item"}
        _check(
            all(
                value.source_id not in excluded and value.item_id not in erased
                for value in self.claims
            ),
            "claims",
            "erased metadata must not be retained",
        )
        _check(
            all(value.source_id not in excluded for value in item_controls),
            "controls",
            "excluded source retains item control",
        )
        owners = {value.item_id: value.source_id for value in self.claims}
        _check(
            all(
                value.item_id not in owners or owners[value.item_id] == value.source_id
                for value in item_controls
            ),
            "ledger",
            "target source conflict",
        )
        self.to_json()

    @property
    def excluded_source_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(value.source_id for value in self.controls if value.action == "exclude_source")
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "kind": "editorial-controls",
            "id": self.id,
            "revision": self.revision,
            "reviewed_at": self.reviewed_at.isoformat().replace("+00:00", "Z"),
            "claims": [value.to_dict() for value in self.claims],
            "controls": [value.to_dict() for value in self.controls],
        }

    def to_json(self) -> bytes:
        data = _canonical(self.to_dict())
        _check(len(data) <= MAX_LEDGER_BYTES, "ledger", "payload limit")
        return data

    @property
    def digest(self) -> str:
        return _hash("wrap-brief:editorial-ledger:v1", self.to_dict())

    @classmethod
    def from_json(cls, value: bytes) -> ControlLedger:
        _check(
            type(value) is bytes and len(value) <= MAX_LEDGER_BYTES,
            "ledger",
            "bounded bytes required",
        )
        try:
            raw = json.loads(
                value.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_number,
            )
        except (UnicodeError, ValueError, RecursionError):
            raise ContractError("ledger: invalid JSON") from None
        fields = {"schema_version", "kind", "id", "revision", "reviewed_at", "claims", "controls"}
        data = _shape(raw, fields, fields, "ledger")
        _check(data.pop("kind") == "editorial-controls", "ledger", "unsupported kind")
        for name, record in (("claims", ClaimEvidence), ("controls", CorrectionControl)):
            _check(
                type(data[name]) is list and len(data[name]) <= MAX_REVIEWS,
                name,
                "bounded array required",
            )
            data[name] = tuple(record.from_dict(row) for row in data[name])
        data["reviewed_at"] = _dated(data["reviewed_at"], "reviewed_at")
        return cls(**data)


def _bound_review(item: Item, review: ClaimEvidence | CorrectionControl) -> None:
    _check(item.source_id == review.source_id, "review", "target source conflict")
    _check(metadata_reference(item) == review.metadata_ref, "review", "claim metadata needs review")
    _check(
        all(
            stamp is None or stamp <= review.reviewed_at
            for stamp in (item.published_at, item.updated_at)
        ),
        "review",
        "precedes publisher metadata",
    )


def _labels(members: tuple[Item, ...], lead_id: str | None) -> tuple[str, str]:
    lead = next((item for item in members if item.id == lead_id), None)
    claim = "reported" if lead is None else "rumor" if _feature(lead).rumor else lead.claim_status
    correction = (
        "retracted"
        if lead is None
        else "corrected"
        if any(item.status in {"corrected", "retracted", "removed"} for item in members)
        else "none"
    )
    return claim, correction


def _transform(snapshot: Snapshot, ledger: ControlLedger, observed_at: datetime) -> Snapshot:
    _check(
        snapshot.observed_at <= observed_at and ledger.reviewed_at <= observed_at,
        "observed_at",
        "precedes input or ledger review",
    )
    excluded = set(ledger.excluded_source_ids)
    controls = {value.item_id: value for value in ledger.controls if value.item_id is not None}
    claims = {value.item_id: value for value in ledger.claims}
    owners = {value.id: value.source_id for value in snapshot.items}
    owners.update({value.item_id: value.source_id for value in snapshot.tombstones})
    _check(
        all(
            value.item_id not in owners or owners[value.item_id] == value.source_id
            for value in (*ledger.claims, *ledger.controls)
            if value.item_id is not None
        ),
        "ledger",
        "target source conflict",
    )
    source_ids = {value.id for value in snapshot.sources}
    tombstones = {
        value.item_id: value for value in snapshot.tombstones if value.source_id not in excluded
    }
    _check(
        all(value.item_id not in tombstones for value in ledger.claims),
        "claims",
        "erased metadata must not be retained",
    )
    _check(
        all(
            value.item_id not in tombstones or value.action == "erase_item"
            for value in ledger.controls
        ),
        "controls",
        "erased item retains non-erasure control",
    )
    for control in ledger.controls:
        if control.action == "erase_item" and control.source_id in source_ids:
            existing = tombstones.get(control.item_id)
            stamp = (
                min(existing.removed_at, control.reviewed_at) if existing else control.reviewed_at
            )
            tombstones[control.item_id] = Tombstone(control.item_id, control.source_id, stamp)
    items = []
    for item in snapshot.items:
        if item.source_id in excluded or item.id in tombstones:
            continue
        control = controls.get(item.id)
        if control is not None and control.action == "retract":
            item = replace(item, status="retracted")
        if item.status in _AVAILABLE:
            if item.status == "corrected" or (control is not None and control.action == "correct"):
                _check(
                    control is not None and control.action == "correct",
                    "correction",
                    "current provenance required",
                )
                _bound_review(item, control)
                item = replace(item, status="corrected")
            evidence = claims.get(item.id)
            _check(evidence is not None, "claim", "current evidence required")
            _bound_review(item, evidence)
            item = replace(item, claim_status=evidence.claim_status)
        else:
            item = replace(item, claim_status="reported")
        items.append(item)
    current = {item.id: item for item in items}
    groups, seen = [], set()
    for group in snapshot.clusters:
        _check(
            group.confidence != "manual", "clusters", "manual overrides require a reviewed adapter"
        )
        members = tuple(current[key] for key in group.member_ids if key in current)
        _check(
            not seen.intersection(item.id for item in members),
            "clusters",
            "overlapping prior membership",
        )
        seen.update(item.id for item in members)
        if not members:
            continue
        available = {item.id for item in members if item.status in _AVAILABLE}
        lead = group.lead_id if group.lead_id in available else min(available, default=None)
        claim, correction = _labels(members, lead)
        groups.append(
            Cluster(
                _group_identifier(tuple(item.id for item in members)),
                tuple(item.id for item in members),
                lead,
                topic=_feature(members[0]).event,
                confidence=group.confidence,
                claim_status=claim,
                correction_status=correction,
            )
        )
    result = Snapshot(
        observed_at,
        tuple(
            replace(source, enabled=False) if source.id in excluded else source
            for source in snapshot.sources
        ),
        tuple(items),
        tuple(groups),
        tuple(value for value in snapshot.checkpoints if value.source_id not in excluded),
        tuple(tombstones.values()),
        kind=snapshot.kind,
    )
    result.to_json()
    return result


def _validated_inputs(snapshot: Snapshot, ledger: ControlLedger) -> tuple[Snapshot, ControlLedger]:
    _check(
        type(snapshot) is Snapshot and type(ledger) is ControlLedger,
        "editorial",
        "validated state and current ledger required",
    )
    return Snapshot.from_json(snapshot.to_json()), ControlLedger.from_json(ledger.to_json())


def _partition(snapshot: Snapshot, *, require_identifiers: bool = True) -> None:
    seen = set()
    by_id = {item.id: item for item in snapshot.items}
    for group in snapshot.clusters:
        _check(not seen.intersection(group.member_ids), "clusters", "overlapping partition")
        seen.update(group.member_ids)
        members = tuple(by_id[key] for key in group.member_ids)
        if require_identifiers:
            _check(
                group.id == _group_identifier(group.member_ids),
                "clusters",
                "derived identifier mismatch",
            )
        _check(
            group.confidence != "manual" and group.override_ref is None,
            "clusters",
            "manual metadata requires a reviewed adapter",
        )
        _check(
            group.topic == _feature(members[0]).event
            and all(_feature(item).event == group.topic for item in members),
            "clusters",
            "derived topic mismatch",
        )
        claim, correction = _labels(members, group.lead_id)
        _check(
            group.claim_status == claim and group.correction_status == correction,
            "clusters",
            "derived editorial label mismatch",
        )
    _check(seen == set(by_id), "clusters", "complete partition required")


@dataclass(frozen=True, slots=True, repr=False)
class ControlledBatch:
    state: Snapshot
    ledger: ControlLedger

    def __post_init__(self) -> None:
        state, ledger = _validated_inputs(self.state, self.ledger)
        _check(
            _transform(state, ledger, state.observed_at).to_json() == state.to_json(),
            "editorial",
            "state is not controlled",
        )

    @property
    def items(self) -> tuple[Item, ...]:
        return self.state.items

    @property
    def previous_clusters(self) -> tuple[Cluster, ...]:
        return self.state.clusters

    def finish(self, *, clusters: tuple[Cluster, ...]) -> EditorialResult:
        _check(
            type(clusters) is tuple
            and len(clusters) <= MAX_RECORDS
            and all(type(group) is Cluster for group in clusters),
            "clusters",
            "bounded immutable partition required",
        )
        candidate = replace(self.state, clusters=clusters)
        _partition(candidate, require_identifiers=False)
        rebound = tuple(
            replace(group, id=_group_identifier(group.member_ids)) for group in candidate.clusters
        )
        return EditorialResult(replace(candidate, clusters=rebound), self.ledger)


def apply_controls(
    snapshot: Snapshot, *, ledger: ControlLedger, observed_at: datetime
) -> ControlledBatch:
    """Use the current externally reviewed ledger, including on old-snapshot restoration."""
    snapshot, ledger = _validated_inputs(snapshot, ledger)
    return ControlledBatch(_transform(snapshot, ledger, _utc(observed_at, "observed_at")), ledger)


@dataclass(frozen=True, slots=True)
class EditorialNotice:
    kind: str
    reviewed_at: datetime
    public_ref: str
    item_id: str | None = None


@dataclass(frozen=True, slots=True, repr=False)
class EditorialResult:
    snapshot: Snapshot
    ledger: ControlLedger

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        snapshot, ledger = _validated_inputs(self.snapshot, self.ledger)
        governed = _transform(snapshot, ledger, snapshot.observed_at)
        _check(
            replace(snapshot, clusters=()).to_json() == replace(governed, clusters=()).to_json(),
            "editorial",
            "result not bound to current ledger",
        )
        _partition(snapshot)

    @property
    def notices(self) -> tuple[EditorialNotice, ...]:
        self.validate()
        visible = {item.id for item in self.snapshot.items if item.status in _AVAILABLE}
        items = {item.id: item for item in self.snapshot.items}
        notices = [
            EditorialNotice(
                value.claim_status, value.reviewed_at, value.evidence_ref, value.item_id
            )
            for value in self.ledger.claims
            if value.item_id in visible
        ]
        for control in self.ledger.controls:
            if control.action == "retract":
                notices.append(
                    EditorialNotice("retract", control.reviewed_at, control.public_notice_ref)
                )
            elif (
                control.action == "correct"
                and control.item_id in visible
                and items[control.item_id].status == "corrected"
            ):
                notices.append(
                    EditorialNotice(
                        "correct",
                        control.reviewed_at,
                        control.public_notice_ref,
                        control.item_id,
                    )
                )
        return tuple(
            sorted(
                notices,
                key=lambda notice: (
                    notice.reviewed_at,
                    notice.kind,
                    notice.item_id or "",
                    notice.public_ref,
                ),
            )
        )
