"""Pure provisional-metadata normalization. Identity and clocks are supplied explicitly."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from wrap_brief.ingest.parsers import RawEntry
from wrap_brief.models import (
    ContractError,
    Item,
    Source,
    _safe_unicode,
    _text,
    _utc,
    validate_https_url,
    validate_references,
)

IdentityFactory = Callable[[str, str, str | None], str]
FUTURE_TOLERANCE = timedelta(minutes=5)
_CANDIDATE_ID = "normalization-candidate"
_TAG_LIKE = re.compile(r"<[A-Za-z/!]")
_REJECTIONS = {
    "source_mismatch",
    "invalid_title",
    "invalid_url",
    "invalid_guid",
    "invalid_date",
    "ambiguous_date",
    "future_date",
    "invalid_date_range",
}


@dataclass(frozen=True, slots=True, repr=False)
class NormalizationResult:
    item: Item | None
    rejection: str | None = None

    def __post_init__(self) -> None:
        valid = (
            self.item is None and isinstance(self.rejection, str) and self.rejection in _REJECTIONS
        ) or (isinstance(self.item, Item) and self.rejection is None)
        if not valid:
            raise ContractError("result: exactly one valid outcome required")

    def __repr__(self) -> str:
        outcome = "accepted" if self.item is not None else "rejected: " + self.rejection
        return f"<NormalizationResult {outcome}>"


class _Rejected(ValueError):
    pass


def _raw(value: object, code: str, limit: int, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or len(value) > limit:
        raise _Rejected(code)
    try:
        # Validate before strip/split so forbidden controls cannot silently disappear.
        _safe_unicode(value, "metadata")
    except ContractError:
        raise _Rejected(code) from None
    value = value.strip()
    if not value:
        if optional:
            return None
        raise _Rejected(code)
    return value


def normalize_url(value: object) -> str:
    """Trim safe boundary spacing/remove a fragment; never fetch, resolve, or reorder a URL."""
    try:
        url = _raw(value, "invalid_url", 4096)
        return validate_https_url(url.partition("#")[0])
    except (_Rejected, ContractError):
        raise ContractError("url: invalid public URL") from None


def _date(value: object, observed_at: datetime) -> datetime | None:
    value = _raw(value, "invalid_date", 128, optional=True)
    if value is None:
        return None
    try:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise _Rejected("ambiguous_date")
        parsed = _utc(parsed, "date")
    except _Rejected:
        raise
    except (ValueError, TypeError, OverflowError):
        raise _Rejected("invalid_date") from None
    if parsed - observed_at > FUTURE_TOLERANCE:
        raise _Rejected("future_date")
    return parsed


def normalize_entry(
    entry: RawEntry,
    source: Source,
    *,
    observed_at: datetime,
    identity: IdentityFactory,
) -> NormalizationResult:
    """Validate one row before invoking a trusted pure identity callback. No I/O or editorial inference."""
    if type(entry) is not RawEntry or not isinstance(source, Source) or not callable(identity):
        raise ContractError("normalizer: invalid programmer arguments")
    clock = _utc(observed_at, "observed_at")
    try:
        if _raw(entry.source_id, "source_mismatch", 128) != source.id:
            raise _Rejected("source_mismatch")
        title = " ".join(_raw(entry.title, "invalid_title", 4096).split())
        try:
            _text(title, "title")
        except ContractError:
            raise _Rejected("invalid_title") from None
        if _TAG_LIKE.search(title):
            # Quarantine ambiguous markup instead of silently rewriting a headline.
            raise _Rejected("invalid_title")
        try:
            url = normalize_url(entry.url)
        except ContractError:
            raise _Rejected("invalid_url") from None
        guid = _raw(entry.guid, "invalid_guid", 2048, optional=True)
        published = _date(entry.published, clock)
        updated = _date(entry.updated, clock)
        if published is not None and updated is not None and updated < published:
            raise _Rejected("invalid_date_range")
        candidate = Item(
            id=_CANDIDATE_ID,
            source_id=source.id,
            title=title,
            url=url,
            first_seen_at=clock,
            last_seen_at=clock,
            published_at=published,
            updated_at=updated,
            guid=guid,
        )
        try:
            validate_references([source], [candidate], [])
        except ContractError:
            raise _Rejected("invalid_url") from None
    except _Rejected as rejected:
        return NormalizationResult(None, str(rejected))
    try:
        identifier = identity(source.id, url, guid)
        if identifier == _CANDIDATE_ID:
            raise ContractError("identity: reserved identifier")
        result = replace(candidate, id=identifier)
    except Exception:
        # Callback bugs are fatal programmer errors, not silently rejected news rows.
        raise ContractError("identity: callback failed or returned an invalid identifier") from None
    return NormalizationResult(result)
