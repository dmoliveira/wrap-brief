"""Conservative pure event grouping with explicit editorial lead evidence."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from wrap_brief.grouping.identity import canonical_url
from wrap_brief.models import (
    Cluster,
    Item,
    Source,
    _check,
    _choice,
    _identifier,
    _reference,
    validate_references,
)

WINDOW = timedelta(hours=48)
MAX_ITEMS = 10_000
MAX_MEMBERS = 100
_STOP = frozenset(
    "a an the and or of for to in on at by from with is are was were new announces announced announcement reveals revealed release released launch date update updates patch firmware version review reviewed preview details during".split()
)
_GENERIC = frozenset(
    "nintendo switch direct game games news report reports story stories console system".split()
)
_EDITIONS = frozenset(
    {
        "deluxe",
        "standard",
        "definitive",
        "remastered",
        "remaster",
        "remake",
        "edition",
        "dlc",
        "demo",
    }
)
_PRIMARY_EVENTS = frozenset({"announcement", "release_date", "delay", "update", "direct"})


@dataclass(frozen=True, slots=True)
class LeadEvidence:
    item_id: str
    role: str = "coverage"
    quality: int = 0
    reference: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.item_id, "item_id")
        _choice(self.role, {"primary", "original", "coverage"}, "lead_role")
        _check(
            type(self.quality) is int and 0 <= self.quality <= 100,
            "quality",
            "bounded editorial score required",
        )
        if self.reference is not None:
            _reference(self.reference, "lead_reference")
        _check(
            self.role == "coverage" or self.reference is not None,
            "lead_reference",
            "role evidence required",
        )


@dataclass(frozen=True, slots=True)
class _Feature:
    tokens: frozenset[str]
    numbers: tuple[str, ...]
    editions: tuple[str, ...]
    quoted: frozenset[str]
    normalized: str
    event: str
    rumor: bool
    stamp: datetime
    url: str


@dataclass(slots=True)
class _Bucket:
    members: list[Item]
    previous_id: str | None = None
    identifier: str | None = None
    locked: bool = False


def _words(value: str) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFC", value).casefold())


def _event(words: frozenset[str]) -> str:
    if words & {"review", "reviewed"}:
        return "review"
    if words & {"preview", "previews"}:
        return "preview"
    if words & {"delay", "delayed", "postponed"}:
        return "delay"
    if "date" in words and words & {"release", "launch"}:
        return "release_date"
    if words & {"update", "updates", "patch", "firmware"}:
        return "update"
    if "direct" in words and words & {"airs", "broadcast", "scheduled", "presentation", "showcase"}:
        return "direct"
    if words & {"announced", "announces", "revealed", "reveals", "announcement"}:
        return "announcement"
    if words & {"earnings", "sales", "financial", "lawsuit", "layoffs"}:
        return "business"
    return "other"


def _feature(item: Item) -> _Feature:
    ordered = _words(item.title)
    words = frozenset(ordered)
    quoted = frozenset(
        " ".join(_words(p)) for p in re.findall(r'["“]([^"”]{1,200})["”]', item.title) if _words(p)
    )
    rumor = item.claim_status == "rumor" or (
        item.claim_status != "confirmed"
        and bool(words & {"rumor", "rumour", "unconfirmed", "leak", "leaked"})
    )
    return _Feature(
        words - _STOP,
        tuple(sorted(set(re.findall(r"\d+(?:[.:/-]\d+)*", item.title)))),
        tuple(sorted(words & _EDITIONS)),
        quoted,
        " ".join(ordered),
        _event(words),
        rumor,
        item.published_at or item.first_seen_at,
        canonical_url(item.url, tracking_parameters=frozenset()),
    )


def _compatible(a: _Feature, b: _Feature) -> bool:
    if (
        a.event != b.event
        or a.rumor != b.rumor
        or a.numbers != b.numbers
        or a.editions != b.editions
        or abs(a.stamp - b.stamp) > WINDOW
    ):
        return False
    if a.quoted and b.quoted and a.quoted != b.quoted:
        return False
    for left, right in ((a, b), (b, a)):
        if any(" " + phrase + " " not in " " + right.normalized + " " for phrase in left.quoted):
            return False
    if a.url == b.url:
        return True
    if len(a.tokens) < 2 or len(b.tokens) < 2 or not ((a.tokens & b.tokens) - _GENERIC):
        return False
    if a.event == "other":
        return a.tokens == b.tokens
    return len(a.tokens & b.tokens) / len(a.tokens | b.tokens) >= 0.85


def _fits(item: Item, bucket: _Bucket, features: dict[str, _Feature]) -> bool:
    return not bucket.locked and all(
        _compatible(features[item.id], features[member.id]) for member in bucket.members
    )


def _sort_key(item: Item, features: dict[str, _Feature]):
    return features[item.id].stamp, item.id


def _bucket_key(feature: _Feature, day: int):
    return feature.event, feature.rumor, feature.numbers, feature.editions, day


def _new_id(members: Sequence[Item], reserved: set[str]) -> str:
    payload = "\0".join(sorted(member.id for member in members)).encode("utf-8")
    for counter in range(MAX_ITEMS + 1):
        identifier = (
            "story-v1-"
            + hashlib.sha256(
                b"story-v1\0" + payload + b"\0" + str(counter).encode("ascii")
            ).hexdigest()
        )
        if identifier not in reserved:
            reserved.add(identifier)
            return identifier
    _check(False, "grouping", "identifier allocation limit")


def _lead(members: Sequence[Item], event: str, evidence: dict[str, LeadEvidence]) -> Item | None:
    available = [item for item in members if item.status in {"active", "corrected"}]
    if not available:
        return None

    def key(item: Item):
        policy = evidence[item.id]
        role = (
            0
            if policy.role == "primary" and event in _PRIMARY_EVENTS
            else 1
            if policy.role == "original"
            else 2
        )
        stamp = item.published_at or item.first_seen_at
        seconds = stamp.toordinal() * 86400 + stamp.hour * 3600 + stamp.minute * 60 + stamp.second
        return (
            role,
            -policy.quality,
            item.published_at is None,
            -seconds,
            -stamp.microsecond,
            item.id,
        )

    return min(available, key=key)


def group_items(
    items: Sequence[Item],
    sources: Sequence[Source],
    *,
    lead_evidence: Sequence[LeadEvidence],
    previous_clusters: Sequence[Cluster] = (),
) -> tuple[Cluster, ...]:
    """Group offline validated metadata conservatively, preserving every current item exactly once."""
    for value, expected, field in (
        (items, Item, "items"),
        (sources, Source, "sources"),
        (lead_evidence, LeadEvidence, "lead_evidence"),
        (previous_clusters, Cluster, "previous_clusters"),
    ):
        _check(
            isinstance(value, Sequence) and len(value) <= MAX_ITEMS,
            field,
            "bounded sequence required",
        )
        _check(all(type(v) is expected for v in value), field, "invalid record")
    validate_references(sources, items, [])
    by_id = {item.id: item for item in items}
    policies = {value.item_id: value for value in lead_evidence}
    _check(
        len(policies) == len(lead_evidence) and set(policies) == set(by_id),
        "lead_evidence",
        "exactly one record per item required",
    )
    previous = {group.id: group for group in previous_clusters}
    _check(len(previous) == len(previous_clusters), "previous_clusters", "duplicate identifier")
    _check(
        all(group.confidence != "manual" for group in previous_clusters),
        "previous_clusters",
        "manual overrides require a reviewed adapter",
    )
    features = {item.id: _feature(item) for item in items}
    assigned: set[str] = set()
    buckets: list[_Bucket] = []
    for group in sorted(previous_clusters, key=lambda g: g.id):
        retained = [by_id[id] for id in group.member_ids if id in by_id]
        _check(
            not (assigned & {i.id for i in retained}),
            "previous_clusters",
            "overlapping current membership",
        )
        parts: list[_Bucket] = []
        for item in sorted(retained, key=lambda i: _sort_key(i, features)):
            matches = [part for part in parts if _fits(item, part, features)]
            if len(matches) == 1:
                _check(len(matches[0].members) < MAX_MEMBERS, "grouping", "member limit")
                matches[0].members.append(item)
            else:
                parts.append(_Bucket([item], group.id, locked=len(matches) > 1))
            assigned.add(item.id)
        if parts:
            main = min(
                parts,
                key=lambda p: (
                    not any(i.id == group.lead_id for i in p.members),
                    -len(p.members),
                    tuple(sorted(i.id for i in p.members)),
                ),
            )
            main.identifier = group.id
            buckets.extend(parts)
    index: dict[tuple, list[_Bucket]] = {}
    for bucket in buckets:
        feature = features[bucket.members[0].id]
        index.setdefault(_bucket_key(feature, feature.stamp.date().toordinal()), []).append(bucket)
    for item in sorted(
        (i for i in items if i.id not in assigned), key=lambda i: _sort_key(i, features)
    ):
        feature = features[item.id]
        day = feature.stamp.date().toordinal()
        candidates = [
            b
            for offset in range(-2, 3)
            for b in index.get(_bucket_key(feature, day + offset), ())
            if _fits(item, b, features)
        ]
        if len(candidates) == 1:
            _check(len(candidates[0].members) < MAX_MEMBERS, "grouping", "member limit")
            candidates[0].members.append(item)
        else:
            bucket = _Bucket([item], locked=len(candidates) > 1)
            buckets.append(bucket)
            index.setdefault(_bucket_key(feature, day), []).append(bucket)
    reserved = set(previous)
    output = []
    for bucket in buckets:
        identifier = bucket.identifier or _new_id(bucket.members, reserved)
        members = tuple(sorted(bucket.members, key=lambda i: i.id))
        event = features[members[0].id].event
        lead = _lead(members, event, policies)
        claim = (
            "reported"
            if lead is None
            else "rumor"
            if features[lead.id].rumor
            else "confirmed"
            if lead.claim_status == "confirmed"
            else "reported"
        )
        correction = (
            "retracted"
            if lead is None
            else "corrected"
            if any(i.status in {"corrected", "retracted", "removed"} for i in members)
            else "none"
        )
        output.append(
            Cluster(
                identifier,
                tuple(i.id for i in members),
                lead.id if lead else None,
                topic=event,
                confidence="exact"
                if len(members) == 1 or len({features[i.id].url for i in members}) == 1
                else "related",
                claim_status=claim,
                correction_status=correction,
            )
        )
    result = tuple(sorted(output, key=lambda group: group.id))
    validate_references(sources, items, result)
    _check(
        sum(len(group.member_ids) for group in result) == len(items),
        "grouping",
        "partition coverage mismatch",
    )
    return result
