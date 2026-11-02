"""Immutable public metadata contracts. No fetching, storage, or editorial inference."""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import MISSING, dataclass, fields
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import ClassVar, Self, TypeVar
from urllib.parse import parse_qsl, urlsplit

SCHEMA_VERSION = 1
_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,127}\Z")
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_SECRET_KEYS = {"token", "access_token", "api_key", "apikey", "password", "authorization", "auth"}
_CLAIMS = {"reported", "confirmed", "rumor"}
_BIDI_FORMATTING = {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"}
_DIRECTION_MARKS = {"\u061c", "\u200e", "\u200f"}


class ContractError(ValueError):
    """A bounded field/reason error that does not echo untrusted input values."""


def _check(condition: object, field: str, reason: str) -> None:
    if not condition:
        raise ContractError(f"{field}: {reason}")


def _safe_unicode(value: str, field: str) -> None:
    _check(
        not any(
            unicodedata.category(c) in {"Cc", "Cs", "Zl", "Zp"}
            or unicodedata.bidirectional(c) in _BIDI_FORMATTING
            or c in _DIRECTION_MARKS
            for c in value
        ),
        field,
        "control character or invalid Unicode",
    )


def _text(value: object, field: str, limit: int = 500) -> str:
    _check(isinstance(value, str), field, "text required")
    _check(0 < len(value) <= limit and value == value.strip(), field, "invalid text length/spacing")
    _safe_unicode(value, field)
    return value


def _identifier(value: object, field: str) -> None:
    _check(isinstance(value, str) and _ID.fullmatch(value), field, "invalid identifier")


def _version(value: object) -> None:
    _check(type(value) is int and value == SCHEMA_VERSION, "schema_version", "unsupported version")


def _choice(value: object, allowed: set[str], field: str) -> None:
    _check(isinstance(value, str) and value in allowed, field, "invalid choice")


def _utc(value: object, field: str) -> datetime:
    _check(isinstance(value, datetime), field, "datetime required")
    try:
        _check(
            value.tzinfo is not None and value.utcoffset() is not None, field, "timezone required"
        )
        return value.astimezone(UTC)
    except (OverflowError, ValueError):
        raise ContractError(f"{field}: invalid timezone-aware datetime") from None


def _host(value: object, field: str) -> str:
    host = _text(value, field, 253).lower()
    if host.endswith("."):
        host = host[:-1]
    _check("%" not in host, field, "invalid host")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            raise ContractError(f"{field}: invalid host") from None
        labels = host.split(".")
        _check(len(host) <= 253, field, "host too long")
        _check(len(labels) >= 2 and not labels[-1].isdecimal(), field, "public host required")
        _check(all(_LABEL.fullmatch(label) for label in labels), field, "invalid host")
        _check(
            labels[-1] not in {"localhost", "local", "internal", "home", "invalid", "test"},
            field,
            "local host prohibited",
        )
        return host
    _check(address.is_global, field, "non-public address prohibited")
    return str(address)


def _https_url(value: object, field: str, *, allow_fragment: bool = False) -> str:
    """Validate syntax/obvious local targets; DNS and redirects belong to the HTTP client."""
    url = _text(value, field, 2048)
    _check(not any(c.isspace() or c in "\\\"'<>`" for c in url), field, "invalid URL characters")
    try:
        parsed = urlsplit(url)
        _check(parsed.scheme == "https" and parsed.hostname, field, "absolute HTTPS URL required")
        _check(parsed.username is None and parsed.password is None, field, "credentials prohibited")
        _check(parsed.port in {None, 443}, field, "unsupported port")
        _check(allow_fragment or not parsed.fragment, field, "fragment prohibited")
        _host(parsed.hostname, field)
        query = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=100)
        _check(
            not any(k.lower().replace("-", "_") in _SECRET_KEYS for k, _ in query),
            field,
            "credential query prohibited",
        )
    except ContractError:
        raise
    except ValueError:
        raise ContractError(f"{field}: invalid URL") from None
    return url


def validate_https_url(value: object) -> str:
    """Validate a canonical public URL with a fixed, non-input-controlled error label."""
    return _https_url(value, "url")


def _reference(value: object, field: str) -> str:
    reference = _text(value, field, 2048)
    if reference.startswith("https://"):
        return _https_url(reference, field, allow_fragment=True)
    path = PurePosixPath(reference.split("#", 1)[0])
    _check(
        re.fullmatch(r"[A-Za-z0-9_./-]+(?:#[A-Za-z0-9_-]+)?", reference),
        field,
        "public reference required",
    )
    _check(
        path.parts
        and not path.is_absolute()
        and not reference.startswith(".")
        and not any(p.startswith(".") for p in path.parts),
        field,
        "unsafe reference",
    )
    return reference


def _shape(value: object, allowed: set[str], required: set[str], field: str) -> dict[str, object]:
    _check(isinstance(value, dict), field, "object required")
    _check(set(value) <= allowed and required <= set(value), field, "missing or unknown fields")
    return dict(value)


class _Record:
    __slots__ = ()
    id: str
    schema_version: int
    _time_fields: ClassVar[tuple[str, ...]] = ()
    _tuple_fields: ClassVar[tuple[str, ...]] = ()

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"schema_version": self.schema_version}
        for field in fields(self):
            if field.name == "schema_version":
                continue
            value = getattr(self, field.name)
            if isinstance(value, datetime):
                value = value.isoformat().replace("+00:00", "Z")
            elif isinstance(value, tuple):
                value = list(value)
            result[field.name] = value
        return result

    @classmethod
    def from_dict(cls, value: object) -> Self:
        definitions = fields(cls)
        allowed = {f.name for f in definitions}
        required = {
            f.name for f in definitions if f.default is MISSING and f.default_factory is MISSING
        }
        data = _shape(value, allowed, required | {"schema_version"}, "record")
        for name in cls._time_fields:
            if name in data and data[name] is not None:
                _check(isinstance(data[name], str), name, "ISO timestamp required")
                try:
                    data[name] = datetime.fromisoformat(data[name])
                except ValueError:
                    raise ContractError(f"{name}: invalid timestamp") from None
        for name in cls._tuple_fields:
            if name in data:
                _check(isinstance(data[name], list), name, "array required")
                data[name] = tuple(data[name])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class Source(_Record):
    id: str
    name: str
    site_url: str
    feed_url: str
    allowed_hosts: tuple[str, ...]
    attribution: str
    region: str = "global"
    enabled: bool = False
    approval_status: str = "unreviewed"
    approval_ref: str | None = None
    reviewed_at: datetime | None = None
    schema_version: int = SCHEMA_VERSION

    _time_fields: ClassVar[tuple[str, ...]] = ("reviewed_at",)
    _tuple_fields: ClassVar[tuple[str, ...]] = ("allowed_hosts",)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.id, "id")
        _text(self.name, "name", 100)
        _text(self.attribution, "attribution", 200)
        _text(self.region, "region", 32)
        _check(type(self.enabled) is bool, "enabled", "boolean required")
        _choice(
            self.approval_status,
            {"unreviewed", "needs_permission", "approved", "rejected"},
            "approval_status",
        )
        _check(
            isinstance(self.allowed_hosts, tuple) and 0 < len(self.allowed_hosts) <= 16,
            "allowed_hosts",
            "bounded tuple required",
        )
        hosts = tuple(_host(host, "allowed_hosts") for host in self.allowed_hosts)
        _check(len(hosts) == len(set(hosts)), "allowed_hosts", "duplicate host")
        object.__setattr__(self, "allowed_hosts", hosts)
        for field in ("site_url", "feed_url"):
            url = _https_url(getattr(self, field), field)
            _check(_host(urlsplit(url).hostname, field) in hosts, field, "host outside allowlist")
        if self.reviewed_at is not None:
            object.__setattr__(self, "reviewed_at", _utc(self.reviewed_at, "reviewed_at"))
        if self.approval_ref is not None:
            _reference(self.approval_ref, "approval_ref")
        if self.approval_status == "approved":
            _check(
                self.reviewed_at is not None and self.approval_ref is not None,
                "approval",
                "dated evidence required",
            )
        _check(
            not self.enabled or self.approval_status == "approved",
            "enabled",
            "source approval required",
        )


@dataclass(frozen=True, slots=True)
class Item(_Record):
    id: str
    source_id: str
    title: str
    url: str
    first_seen_at: datetime
    last_seen_at: datetime
    published_at: datetime | None = None
    updated_at: datetime | None = None
    guid: str | None = None
    status: str = "active"
    claim_status: str = "reported"
    schema_version: int = SCHEMA_VERSION

    _time_fields: ClassVar[tuple[str, ...]] = (
        "first_seen_at",
        "last_seen_at",
        "published_at",
        "updated_at",
    )

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.id, "id")
        _identifier(self.source_id, "source_id")
        _text(self.title, "title")
        validate_https_url(self.url)
        if self.guid is not None:
            _text(self.guid, "guid", 2048)
        _choice(
            self.status, {"active", "corrected", "retracted", "removed", "quarantined"}, "status"
        )
        _choice(self.claim_status, _CLAIMS, "claim_status")
        for field in self._time_fields:
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _utc(value, field))
        _check(
            self.first_seen_at is not None and self.last_seen_at is not None,
            "seen_at",
            "timestamps required",
        )
        _check(self.first_seen_at <= self.last_seen_at, "last_seen_at", "precedes first seen")
        if self.published_at is not None and self.updated_at is not None:
            _check(self.published_at <= self.updated_at, "updated_at", "precedes publication")


@dataclass(frozen=True, slots=True)
class Cluster(_Record):
    id: str
    member_ids: tuple[str, ...]
    lead_id: str | None
    topic: str = "other"
    confidence: str = "related"
    claim_status: str = "reported"
    correction_status: str = "none"
    override_ref: str | None = None
    schema_version: int = SCHEMA_VERSION

    _tuple_fields: ClassVar[tuple[str, ...]] = ("member_ids",)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.id, "id")
        _check(
            isinstance(self.member_ids, tuple) and 0 < len(self.member_ids) <= 100,
            "member_ids",
            "bounded tuple required",
        )
        for member in self.member_ids:
            _identifier(member, "member_ids")
        _check(len(set(self.member_ids)) == len(self.member_ids), "member_ids", "duplicate member")
        if self.lead_id is not None:
            _identifier(self.lead_id, "lead_id")
            _check(self.lead_id in self.member_ids, "lead_id", "not a cluster member")
        _text(self.topic, "topic", 50)
        _choice(self.confidence, {"exact", "related", "manual"}, "confidence")
        _choice(self.claim_status, _CLAIMS, "claim_status")
        _choice(self.correction_status, {"none", "corrected", "retracted"}, "correction_status")
        if self.override_ref is not None:
            _reference(self.override_ref, "override_ref")
        _check(
            self.confidence != "manual" or self.override_ref is not None,
            "override_ref",
            "manual provenance required",
        )


_R = TypeVar("_R", bound=_Record)


def _index(records: Sequence[_R], expected: type[_R], field: str) -> dict[str, _R]:
    _check(isinstance(records, Sequence), field, "record sequence required")
    result: dict[str, _R] = {}
    for record in records:
        _check(isinstance(record, expected), field, "invalid record")
        _check(record.id not in result, field, "duplicate identifier")
        result[record.id] = record
    return result


def validate_references(
    sources: Sequence[Source], items: Sequence[Item], clusters: Sequence[Cluster]
) -> None:
    """Validate cross-record identity/provenance, not grouping similarity or source licensing."""
    source_index = _index(sources, Source, "sources")
    item_index = _index(items, Item, "items")
    _index(clusters, Cluster, "clusters")
    for item in items:
        _check(item.source_id in source_index, "source_id", "unknown source")
        source = source_index[item.source_id]
        _check(
            _host(urlsplit(item.url).hostname, "url") in source.allowed_hosts,
            "url",
            "host outside source allowlist",
        )
    for cluster in clusters:
        _check(all(id in item_index for id in cluster.member_ids), "member_ids", "unknown item")
        available = [
            item_index[id]
            for id in cluster.member_ids
            if item_index[id].status in {"active", "corrected"}
        ]
        if cluster.lead_id is None:
            _check(not available, "lead_id", "visible items require a lead")
            continue
        lead = item_index[cluster.lead_id]
        _check(lead in available, "lead_id", "unavailable item cannot lead")
        _check(
            lead.claim_status != "rumor" or cluster.claim_status == "rumor",
            "claim_status",
            "rumor lead must be labeled",
        )
        _check(
            cluster.claim_status != "confirmed" or lead.claim_status == "confirmed",
            "claim_status",
            "unconfirmed lead",
        )
