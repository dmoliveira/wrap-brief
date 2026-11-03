"""Pure reviewed split/merge/release adapter. Configuration validity is not authority."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from urllib.parse import urlsplit

from wrap_brief.grouping.stories import MAX_ITEMS, LeadEvidence, _cluster, _feature, group_items
from wrap_brief.models import (
    Cluster,
    ContractError,
    Item,
    Source,
    _check,
    _choice,
    _identifier,
    _Record,
    _reference,
    _shape,
    _utc,
    _version,
    validate_references,
)
from wrap_brief.state.snapshot import Snapshot, _invalid_number, _unique_object

MAX_PLAN_BYTES = 1_048_576
MAX_DECISIONS = 1_000
MAX_TARGETS = 100


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _hash(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\0" + _canonical(value)).hexdigest()


def grouping_reference(item: Item) -> str:
    _check(type(item) is Item, "override", "validated item required")
    data = item.to_dict()
    return _hash(
        "wrap-brief:grouping-metadata:v1",
        {
            key: data[key]
            for key in (
                "id",
                "source_id",
                "title",
                "url",
                "guid",
                "published_at",
                "updated_at",
                "claim_status",
            )
        },
    )


def _public_ref(value: object) -> str:
    reference = _reference(value, "override_reference")
    _check(
        len(reference) <= 1_024 and not urlsplit(reference).query,
        "override_reference",
        "bounded query-free public citation required",
    )
    return reference


def _date(value: object) -> datetime:
    _check(type(value) is str, "reviewed_at", "ISO timestamp required")
    try:
        return _utc(datetime.fromisoformat(value), "reviewed_at")
    except ValueError:
        raise ContractError("reviewed_at: invalid timestamp") from None


@dataclass(frozen=True, slots=True, repr=False)
class OverrideTarget(_Record):
    source_id: str
    item_id: str
    metadata_ref: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.source_id, "source_id")
        _identifier(self.item_id, "item_id")
        _check(
            type(self.metadata_ref) is str
            and re.fullmatch(r"[a-f0-9]{64}", self.metadata_ref) is not None,
            "metadata_ref",
            "SHA-256 reference required",
        )


@dataclass(frozen=True, slots=True, repr=False)
class GroupingDecision:
    id: str
    action: str
    targets: tuple[OverrideTarget, ...]
    reviewed_at: datetime
    evidence_ref: str
    partitions: tuple[tuple[str, ...], ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.id, "id")
        _choice(self.action, {"merge", "split", "release"}, "action")
        object.__setattr__(self, "reviewed_at", _utc(self.reviewed_at, "reviewed_at"))
        _public_ref(self.evidence_ref)
        _check(
            type(self.targets) is tuple
            and 0 < len(self.targets) <= MAX_TARGETS
            and all(type(value) is OverrideTarget for value in self.targets),
            "targets",
            "bounded immutable targets required",
        )
        ids = {value.item_id for value in self.targets}
        _check(len(ids) == len(self.targets), "targets", "duplicate identifier")
        _check(self.action == "release" or len(ids) >= 2, "targets", "multiple targets required")
        _check(
            type(self.partitions) is tuple and len(self.partitions) <= MAX_TARGETS,
            "partitions",
            "bounded immutable partitions required",
        )
        if self.action == "split":
            _check(len(self.partitions) >= 2, "partitions", "multiple partitions required")
            seen = set()
            for part in self.partitions:
                _check(
                    type(part) is tuple and 0 < len(part) <= MAX_TARGETS,
                    "partitions",
                    "nonempty immutable partition required",
                )
                for item_id in part:
                    _identifier(item_id, "item_id")
                _check(
                    len(set(part)) == len(part) and not seen.intersection(part),
                    "partitions",
                    "overlapping membership",
                )
                seen.update(part)
            _check(seen == ids, "partitions", "complete target partition required")
        else:
            _check(not self.partitions, "partitions", "unsupported for this action")
        object.__setattr__(
            self, "targets", tuple(sorted(self.targets, key=lambda value: value.item_id))
        )
        object.__setattr__(
            self, "partitions", tuple(sorted(tuple(sorted(part)) for part in self.partitions))
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "action": self.action,
            "reviewed_at": self.reviewed_at.isoformat().replace("+00:00", "Z"),
            "evidence_ref": self.evidence_ref,
            "targets": [target.to_dict() for target in self.targets],
            "partitions": [list(part) for part in self.partitions],
        }

    @classmethod
    def from_dict(cls, value: object) -> GroupingDecision:
        fields = {
            "schema_version",
            "id",
            "action",
            "reviewed_at",
            "evidence_ref",
            "targets",
            "partitions",
        }
        data = _shape(value, fields, fields, "decision")
        _check(
            type(data["targets"]) is list and len(data["targets"]) <= MAX_TARGETS,
            "targets",
            "bounded array required",
        )
        _check(
            type(data["partitions"]) is list and len(data["partitions"]) <= MAX_TARGETS,
            "partitions",
            "bounded array required",
        )
        _check(
            all(type(part) is list and len(part) <= MAX_TARGETS for part in data["partitions"]),
            "partitions",
            "bounded nested arrays required",
        )
        data["targets"] = tuple(OverrideTarget.from_dict(target) for target in data["targets"])
        data["partitions"] = tuple(tuple(part) for part in data["partitions"])
        data["reviewed_at"] = _date(data["reviewed_at"])
        return cls(**data)


@dataclass(frozen=True, slots=True, repr=False)
class GroupingPlan:
    id: str
    revision: int
    reviewed_at: datetime
    decisions: tuple[GroupingDecision, ...] = ()
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
        _check(
            type(self.decisions) is tuple
            and len(self.decisions) <= MAX_DECISIONS
            and all(type(value) is GroupingDecision for value in self.decisions),
            "decisions",
            "bounded immutable decisions required",
        )
        _check(
            len({value.id for value in self.decisions}) == len(self.decisions),
            "decisions",
            "duplicate identifier",
        )
        seen = set()
        for decision in self.decisions:
            _check(decision.reviewed_at <= self.reviewed_at, "reviewed_at", "future decision")
            targets = {value.item_id for value in decision.targets}
            _check(not seen.intersection(targets), "decisions", "overlapping targets")
            seen.update(targets)
        _check(len(seen) <= MAX_ITEMS, "targets", "total target limit")
        object.__setattr__(
            self, "decisions", tuple(sorted(self.decisions, key=lambda value: value.id))
        )
        self.to_json()

    def to_json(self) -> bytes:
        data = _canonical(
            {
                "schema_version": self.schema_version,
                "kind": "grouping-overrides",
                "id": self.id,
                "revision": self.revision,
                "reviewed_at": self.reviewed_at.isoformat().replace("+00:00", "Z"),
                "decisions": [value.to_dict() for value in self.decisions],
            }
        )
        _check(len(data) <= MAX_PLAN_BYTES, "plan", "payload limit")
        return data

    @classmethod
    def from_json(cls, value: bytes) -> GroupingPlan:
        _check(
            type(value) is bytes and len(value) <= MAX_PLAN_BYTES, "plan", "bounded bytes required"
        )
        try:
            raw = json.loads(
                value.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_number,
            )
        except (UnicodeError, ValueError, RecursionError):
            raise ContractError("plan: invalid JSON") from None
        fields = {"schema_version", "kind", "id", "revision", "reviewed_at", "decisions"}
        data = _shape(raw, fields, fields, "plan")
        _check(data.pop("kind") == "grouping-overrides", "plan", "unsupported kind")
        _check(
            type(data["decisions"]) is list and len(data["decisions"]) <= MAX_DECISIONS,
            "decisions",
            "bounded array required",
        )
        data["decisions"] = tuple(GroupingDecision.from_dict(value) for value in data["decisions"])
        data["reviewed_at"] = _date(data["reviewed_at"])
        return cls(**data)


def group_with_overrides(
    items: Sequence[Item],
    sources: Sequence[Source],
    *,
    lead_evidence: Sequence[LeadEvidence],
    plan: GroupingPlan,
    observed_at: datetime,
    previous_clusters: Sequence[Cluster] = (),
    fuzzy_enabled: bool = True,
) -> tuple[Cluster, ...]:
    """Apply only current explicit targets; configuration cannot change claims or availability."""
    at = _utc(observed_at, "observed_at")
    _check(
        type(plan) is GroupingPlan and type(fuzzy_enabled) is bool,
        "grouping",
        "validated plan and policy required",
    )
    plan = GroupingPlan.from_json(plan.to_json())
    _check(plan.reviewed_at <= at, "reviewed_at", "future plan")
    for values, expected, field in (
        (items, Item, "items"),
        (sources, Source, "sources"),
        (lead_evidence, LeadEvidence, "lead_evidence"),
        (previous_clusters, Cluster, "previous_clusters"),
    ):
        _check(
            isinstance(values, Sequence)
            and len(values) <= MAX_ITEMS
            and all(type(value) is expected for value in values),
            field,
            "bounded records required",
        )
    state = Snapshot.from_json(Snapshot(at, tuple(sources), tuple(items)).to_json())
    current = {item.id: item for item in state.items}
    policies = {value.item_id: LeadEvidence(**asdict(value)) for value in lead_evidence}
    _check(
        len(policies) == len(lead_evidence) and set(policies) == set(current),
        "lead_evidence",
        "exactly one record per item required",
    )
    previous = tuple(Cluster.from_dict(value.to_dict()) for value in previous_clusters)
    _check(
        len({group.id for group in previous}) == len(previous),
        "previous_clusters",
        "duplicate identifier",
    )
    assigned = set()
    for group in previous:
        retained = set(group.member_ids).intersection(current)
        _check(
            not assigned.intersection(retained),
            "previous_clusters",
            "overlapping retained membership",
        )
        assigned.update(retained)
    covered, locked = set(), set()
    for decision in plan.decisions:
        for target in decision.targets:
            covered.add(target.item_id)
            item = current.get(target.item_id)
            if item is None:
                continue
            _check(item.source_id == target.source_id, "override", "target source conflict")
            _check(
                grouping_reference(item) == target.metadata_ref, "override", "metadata needs review"
            )
            _check(
                all(
                    stamp is None or stamp <= decision.reviewed_at
                    for stamp in (item.published_at, item.updated_at)
                ),
                "reviewed_at",
                "precedes publisher metadata",
            )
            if decision.action != "release":
                locked.add(item.id)
    automatic_context = []
    for group in previous:
        retained = set(group.member_ids).intersection(current)
        if group.confidence == "manual":
            _check(
                retained <= covered,
                "previous_clusters",
                "current reviewed coverage required for manual context",
            )
            continue
        members = tuple(sorted(retained - locked))
        if not members:
            continue
        available = {key for key in members if current[key].status in {"active", "corrected"}}
        lead = group.lead_id if group.lead_id in available else min(available, default=None)
        automatic_context.append(
            Cluster(
                group.id,
                members,
                lead,
                claim_status=current[lead].claim_status if lead else "reported",
            )
        )
    automatic_items = tuple(item for item in state.items if item.id not in locked)
    output = list(
        group_items(
            automatic_items,
            state.sources,
            lead_evidence=tuple(policies[item.id] for item in automatic_items),
            previous_clusters=tuple(automatic_context),
            fuzzy_enabled=fuzzy_enabled,
        )
    )
    features = {item.id: _feature(item) for item in state.items}
    for decision in plan.decisions:
        if decision.action == "release":
            continue
        partitions = (
            decision.partitions
            if decision.action == "split"
            else (tuple(value.item_id for value in decision.targets),)
        )
        for part in partitions:
            members = tuple(current[key] for key in sorted(part) if key in current)
            if not members:
                continue
            events = {features[item.id].event for item in members}
            event = next(iter(events)) if len(events) == 1 else "other"
            identifier = "manual-group-v1-" + _hash(
                "wrap-brief:manual-group:v1",
                {"decision_id": decision.id, "member_ids": sorted(item.id for item in members)},
            )
            output.append(
                _cluster(
                    identifier,
                    members,
                    event,
                    policies,
                    features,
                    confidence="manual",
                    override_ref=decision.evidence_ref,
                )
            )
    result = tuple(sorted(output, key=lambda group: group.id))
    validate_references(state.sources, state.items, result)
    memberships = [key for group in result for key in group.member_ids]
    _check(
        len(memberships) == len(set(memberships)) == len(current)
        and set(memberships) == set(current),
        "grouping",
        "complete partition required",
    )
    return result
