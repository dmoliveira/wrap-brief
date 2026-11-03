"""Pure incremental source-state reduction; no requests, clock lookup, storage or publishing."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import datetime

from wrap_brief.grouping.identity import stable_item_id
from wrap_brief.ingest.http import ERRORS, MAX_BODY, MAX_REQUESTS, FetchResult
from wrap_brief.ingest.normalize import normalize_entry
from wrap_brief.ingest.parsers import FeedParseError, parse_feed
from wrap_brief.models import Cluster, ContractError, Item, _check, _identifier, _text, _utc
from wrap_brief.state.snapshot import MAX_RECORDS, PollCheckpoint, Snapshot, merge_items

_FETCH_CODES = ERRORS | {
    "poll_interval",
    "http_status",
    "rate_limit",
    "unsolicited_304",
    "redirect",
    "request_budget",
}


def _retain_controls(old: Item | None, incoming: Item) -> Item:
    """Feed defaults are not authority to lift reviewed restrictions or change claim evidence."""
    if old is None:
        return incoming
    metadata = ("title", "url", "published_at", "updated_at", "guid")
    unchanged = all(getattr(old, key) == getattr(incoming, key) for key in metadata)
    status = old.status if old.status != "active" else incoming.status
    claim = (
        old.claim_status
        if old.claim_status == "rumor" or (old.claim_status == "confirmed" and unchanged)
        else incoming.claim_status
    )
    return replace(incoming, status=status, claim_status=claim)


@dataclass(frozen=True, slots=True, repr=False)
class SourcePoll:
    source_id: str
    response: FetchResult


@dataclass(frozen=True, slots=True)
class PollOutcome:
    source_id: str
    status: str
    requests: int
    code: str | None = None
    physical_rows: int = 0
    accepted_rows: int = 0
    quarantined_rows: int = 0
    new_items: int = 0
    updated_items: int = 0
    warnings: tuple[str, ...] = ()
    retry_after_seconds: float | None = None

    @property
    def usable(self) -> bool:
        return self.status in {"ok", "not_modified"}


@dataclass(frozen=True, slots=True, repr=False)
class PollBatch:
    """Intermediate state, deliberately not an implicitly renderable grouped Snapshot."""

    previous: Snapshot
    observed_at: datetime
    items: tuple[Item, ...]
    checkpoints: tuple[PollCheckpoint, ...]
    outcomes: tuple[PollOutcome, ...]

    @property
    def health(self) -> str:
        if not self.outcomes:
            return "no_sources"
        if not any(outcome.usable for outcome in self.outcomes):
            return "blocked"
        if any(not outcome.usable or outcome.warnings for outcome in self.outcomes):
            return "degraded"
        return "healthy"

    @property
    def no_new(self) -> bool:
        return bool(self.outcomes) and all(
            outcome.usable and outcome.new_items == 0 for outcome in self.outcomes
        )

    @property
    def previous_clusters(self) -> tuple[Cluster, ...]:
        return self.previous.clusters

    @property
    def requires_regrouping(self) -> bool:
        return self.items != self.previous.items

    def require_publishable(self) -> None:
        """Source-health guard only; caller must also satisfy grouping/rights/release gates."""
        _check(self.health not in {"blocked", "no_sources"}, "polling", "no usable source success")

    def to_snapshot(self, *, clusters: tuple[Cluster, ...]) -> Snapshot:
        """Require an explicit complete current-item grouping; never reuse old groups implicitly."""
        _check(
            type(clusters) is tuple
            and len(clusters) <= MAX_RECORDS
            and all(type(group) is Cluster for group in clusters),
            "polling",
            "validated groups required",
        )
        _check(
            sum(len(group.member_ids) for group in clusters) <= MAX_RECORDS,
            "polling",
            "group membership limit",
        )
        members = [id for group in clusters for id in group.member_ids]
        _check(
            len(members) == len(set(members)) and set(members) == {item.id for item in self.items},
            "polling",
            "complete nonoverlapping grouping required",
        )
        candidate = replace(
            self.previous,
            observed_at=self.observed_at,
            items=self.items,
            clusters=clusters,
            checkpoints=self.checkpoints,
        )
        candidate.to_json()  # Enforce logical byte limit before any caller can persist it.
        return candidate


def _validate_response(response: FetchResult) -> None:
    _check(type(response) is FetchResult, "polling", "typed fetch result required")
    _check(
        type(response.status) is str
        and response.status in {"ok", "not_modified", "error", "deferred"},
        "polling",
        "invalid fetch status",
    )
    _check(
        type(response.requests) is int and 0 <= response.requests <= MAX_REQUESTS,
        "polling",
        "invalid request count",
    )
    if response.status in {"ok", "not_modified"}:
        _check(
            response.requests > 0
            and response.code is None
            and response.retry_after_seconds is None,
            "polling",
            "invalid successful result",
        )
        _check(
            (
                response.status == "ok"
                and type(response.body) is bytes
                and len(response.body) <= MAX_BODY
            )
            or (response.status == "not_modified" and response.body is None),
            "polling",
            "invalid successful body",
        )
        for value, limit in ((response.etag, 512), (response.last_modified, 128)):
            if value is not None:
                _text(value, "validator", limit)
        return
    _check(
        response.body is None and response.etag is None and response.last_modified is None,
        "polling",
        "unsuccessful result must not carry content",
    )
    _check(
        type(response.code) is str and response.code in _FETCH_CODES,
        "polling",
        "invalid failure code",
    )
    if response.status == "error":
        _check(
            response.retry_after_seconds is None
            and (response.requests > 0 or response.code == "timeout"),
            "polling",
            "invalid error result",
        )
    else:
        delay = response.retry_after_seconds
        try:
            valid_delay = delay is None or (
                type(delay) in {int, float} and math.isfinite(delay) and delay >= 0
            )
        except OverflowError:
            valid_delay = False
        _check(
            valid_delay,
            "polling",
            "invalid deferral delay",
        )
        _check(
            response.requests > 0
            or (response.code == "poll_interval" and delay is not None and delay > 0),
            "polling",
            "invalid unattempted deferral",
        )


def reduce_polls(
    previous: Snapshot,
    polls: tuple[SourcePoll, ...],
    *,
    expected_source_ids: tuple[str, ...],
    observed_at: datetime,
) -> PollBatch:
    """Advance independent sources after full validation; retained state never becomes no-news."""
    _check(type(previous) is Snapshot, "polling", "validated snapshot required")
    now = _utc(observed_at, "observed_at")
    _check(now >= previous.observed_at, "polling", "backward observation")
    _check(
        type(polls) is tuple
        and len(polls) <= 100
        and all(type(poll) is SourcePoll for poll in polls),
        "polling",
        "bounded typed poll tuple required",
    )
    _check(
        type(expected_source_ids) is tuple and len(expected_source_ids) <= 100,
        "polling",
        "bounded expected-source tuple required",
    )
    for id in expected_source_ids:
        _identifier(id, "source_id")
    source_index = {source.id: source for source in previous.sources}
    _check(
        len(set(expected_source_ids)) == len(expected_source_ids)
        and set(expected_source_ids) <= set(source_index),
        "polling",
        "unique known expected sources required",
    )
    for poll in polls:
        _identifier(poll.source_id, "source_id")
        _validate_response(poll.response)
    _check(
        len({poll.source_id for poll in polls}) == len(polls)
        and {poll.source_id for poll in polls} == set(expected_source_ids),
        "polling",
        "exact source result coverage required",
    )
    if previous.kind == "live":
        _check(
            all(
                source_index[id].enabled
                and source_index[id].approval_status == "approved"
                and source_index[id].reviewed_at <= now
                for id in expected_source_ids
            ),
            "polling",
            "live source approval required",
        )
    items = previous.items
    checkpoints = {checkpoint.source_id: checkpoint for checkpoint in previous.checkpoints}
    outcomes = []
    for poll in sorted(polls, key=lambda poll: poll.source_id):
        source = source_index[poll.source_id]
        response = poll.response
        old = checkpoints.get(source.id)

        def failure(
            status: str,
            code: str,
            *,
            physical: int = 0,
            quarantined: int = 0,
            response: FetchResult = response,
            source_id: str = source.id,
            old: PollCheckpoint | None = old,
        ) -> None:
            if response.requests:
                checkpoints[source_id] = (
                    replace(old, last_attempt_at=now, status="error")
                    if old
                    else PollCheckpoint(source_id, now)
                )
            outcomes.append(
                PollOutcome(
                    source_id,
                    status,
                    response.requests,
                    code,
                    physical_rows=physical,
                    quarantined_rows=quarantined,
                    retry_after_seconds=response.retry_after_seconds,
                )
            )

        if response.status in {"error", "deferred"}:
            failure(response.status, response.code)
            continue
        if response.status == "not_modified":
            if (
                old is None
                or old.last_success_at is None
                or (old.etag is None and old.last_modified is None)
            ):
                failure("error", "invalid_304")
                continue
            checkpoints[source.id] = replace(
                old,
                last_attempt_at=now,
                last_success_at=now,
                status="not_modified",
                etag=response.etag if response.etag is not None else old.etag,
                last_modified=response.last_modified
                if response.last_modified is not None
                else old.last_modified,
            )
            outcomes.append(PollOutcome(source.id, "not_modified", response.requests))
            continue
        try:
            feed = parse_feed(response.body, source)
        except FeedParseError as error:
            failure("error", "parse_" + error.code)
            continue
        physical = len(feed.entries) + len(feed.issues)
        before = {item.id: item for item in items if item.source_id == source.id}
        incoming = []
        quarantined = len(feed.issues)
        for entry in feed.entries:
            normalized = normalize_entry(entry, source, observed_at=now, identity=stable_item_id)
            if normalized.item is None:
                quarantined += 1
            else:
                incoming.append(_retain_controls(before.get(normalized.item.id), normalized.item))
        if physical and not incoming:
            failure("error", "all_quarantined", physical=physical, quarantined=quarantined)
            continue
        try:
            merged = merge_items(items, incoming, tombstones=previous.tombstones)
        except ContractError as error:
            # This fixed core-contract reason describes incompatible publisher metadata.
            # Identity/integrity and count-limit errors remain fatal for the whole batch.
            if str(error) != "updated_at: precedes publication":
                raise
            failure("error", "metadata_conflict", physical=physical, quarantined=physical)
            continue
        current = {item.id: item for item in merged if item.source_id == source.id}
        new_ids = set(current) - set(before)
        updated = sum(
            replace(before[id], first_seen_at=item.first_seen_at, last_seen_at=item.last_seen_at)
            != item
            for id, item in current.items()
            if id in before
        )
        dates = [item.published_at for item in incoming if item.published_at is not None]
        oldest, newest = (min(dates), max(dates)) if dates else (None, None)
        warnings = []
        if old is None or old.last_success_at is None:
            warnings.append("baseline_unknown")
        elif oldest is not None and oldest > old.last_success_at:
            warnings.append("possible_gap")
        if old is not None and old.entry_count is not None and physical < old.entry_count:
            warnings.append("feed_window_shrank")
        if incoming and not dates:
            warnings.append("publication_unknown")
        if physical == 100 and not (set(before) & {item.id for item in incoming}):
            warnings.append("saturated_no_overlap")
        if quarantined:
            warnings.append("quarantined_entries")
        checkpoints[source.id] = PollCheckpoint(
            source.id,
            now,
            now,
            response.etag,
            response.last_modified,
            physical,
            oldest,
            newest,
            status="ok",
        )
        items = merged
        outcomes.append(
            PollOutcome(
                source.id,
                "ok",
                response.requests,
                physical_rows=physical,
                accepted_rows=len(incoming),
                quarantined_rows=quarantined,
                new_items=len(new_ids),
                updated_items=updated,
                warnings=tuple(sorted(warnings)),
            )
        )
    return PollBatch(
        previous, now, items, tuple(checkpoints[id] for id in sorted(checkpoints)), tuple(outcomes)
    )
