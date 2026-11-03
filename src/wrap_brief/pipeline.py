"""Pure synthetic execution envelopes and independently verifiable reader candidates."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime

from wrap_brief.grouping.stories import LeadEvidence, group_items
from wrap_brief.ingest.http import MAX_BODY, FetchResult
from wrap_brief.ingest.polling import PollBatch, SourcePoll, _validate_response, reduce_polls
from wrap_brief.models import ContractError, _check, _identifier, _shape, _utc
from wrap_brief.render.digest import MAX_HTML_BYTES, render_digest
from wrap_brief.state.snapshot import Snapshot, _invalid_number, _unique_object

MAX_PIPELINE_BYTES = 4_194_304
MAX_PIPELINE_ITEMS = 500
MAX_STYLESHEET_BYTES = 65_536
MAX_MANIFEST_BYTES = 16_384
LEAD_POLICY = "synthetic-lead-v1"
FILES = {
    "index.html": MAX_HTML_BYTES,
    "styles.css": MAX_STYLESHEET_BYTES,
    "manifest.json": MAX_MANIFEST_BYTES,
}
_RESPONSE_FIELDS = {
    "source_id",
    "status",
    "requests",
    "code",
    "body_base64",
    "etag",
    "last_modified",
    "retry_after_seconds",
}


class UnusableHealth(ValueError):
    pass


class CandidateMismatch(ValueError):
    pass


def _canonical(value: object, *, limit: int = MAX_PIPELINE_BYTES) -> bytes:
    data = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    _check(len(data) <= limit, "pipeline", "payload limit")
    return data


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reference(value: str, length: int) -> None:
    _check(
        type(value) is str and re.fullmatch(r"[a-f0-9]{" + str(length) + "}", value) is not None,
        "pipeline",
        "invalid reference",
    )


def _json(value: bytes) -> object:
    _check(
        type(value) is bytes and len(value) <= MAX_PIPELINE_BYTES,
        "pipeline",
        "bounded bytes required",
    )
    try:
        return json.loads(
            value.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_number
        )
    except (UnicodeError, ValueError, RecursionError):
        raise ContractError("pipeline: invalid JSON") from None


def _version(value: object, kind: str, expected_kind: str) -> None:
    _check(
        type(value) is int and value == 1 and kind == expected_kind,
        "pipeline",
        "unsupported envelope",
    )


def _fixture(snapshot: Snapshot) -> None:
    _check(
        type(snapshot) is Snapshot and snapshot.kind == "synthetic",
        "pipeline",
        "synthetic snapshot required",
    )
    _check(
        len(snapshot.items) <= MAX_PIPELINE_ITEMS and len(snapshot.to_json()) <= MAX_PIPELINE_BYTES,
        "pipeline",
        "fixture state limit",
    )
    _check(
        all(
            not source.enabled
            and all(
                host in {"example.com", "example.org", "example.net"}
                or host.endswith((".example", ".example.com", ".example.org", ".example.net"))
                for host in source.allowed_hosts
            )
            for source in snapshot.sources
        ),
        "pipeline",
        "disabled reserved fixtures required",
    )


@dataclass(frozen=True, slots=True, repr=False)
class PollPlan:
    observed_at: datetime
    expected_source_ids: tuple[str, ...]
    polls: tuple[SourcePoll, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", _utc(self.observed_at, "observed_at"))
        _check(
            type(self.expected_source_ids) is tuple and len(self.expected_source_ids) <= 100,
            "pipeline",
            "bounded expected sources required",
        )
        for source_id in self.expected_source_ids:
            _identifier(source_id, "source_id")
        _check(
            len(set(self.expected_source_ids)) == len(self.expected_source_ids),
            "pipeline",
            "duplicate source",
        )
        _check(
            type(self.polls) is tuple
            and len(self.polls) <= 100
            and all(type(poll) is SourcePoll for poll in self.polls),
            "pipeline",
            "bounded supplied results required",
        )
        for poll in self.polls:
            _identifier(poll.source_id, "source_id")
            _validate_response(poll.response)
        _check(
            len({poll.source_id for poll in self.polls}) == len(self.polls)
            and {poll.source_id for poll in self.polls} == set(self.expected_source_ids),
            "pipeline",
            "exact result coverage required",
        )
        _check(
            sum(len(poll.response.body or b"") for poll in self.polls) <= MAX_BODY,
            "pipeline",
            "aggregate body limit",
        )
        object.__setattr__(self, "expected_source_ids", tuple(sorted(self.expected_source_ids)))
        object.__setattr__(
            self, "polls", tuple(sorted(self.polls, key=lambda poll: poll.source_id))
        )

    def to_dict(self) -> dict[str, object]:
        rows = []
        for poll in self.polls:
            response = asdict(poll.response)
            body = response.pop("body")
            rows.append(
                {
                    "source_id": poll.source_id,
                    **response,
                    "body_base64": base64.b64encode(body).decode("ascii")
                    if body is not None
                    else None,
                }
            )
        return {
            "schema_version": 1,
            "kind": "synthetic-fetch-results",
            "observed_at": self.observed_at.isoformat().replace("+00:00", "Z"),
            "expected_source_ids": list(self.expected_source_ids),
            "responses": rows,
        }

    def to_json(self) -> bytes:
        return _canonical(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> PollPlan:
        fields = {"schema_version", "kind", "observed_at", "expected_source_ids", "responses"}
        data = _shape(value, fields, fields, "poll_plan")
        _version(data["schema_version"], data["kind"], "synthetic-fetch-results")
        _check(type(data["observed_at"]) is str, "pipeline", "explicit clock required")
        try:
            observed = datetime.fromisoformat(data["observed_at"])
        except ValueError:
            raise ContractError("pipeline: invalid clock") from None
        expected = data["expected_source_ids"]
        rows = data["responses"]
        _check(
            type(expected) is list
            and len(expected) <= 100
            and type(rows) is list
            and len(rows) <= 100,
            "pipeline",
            "bounded arrays required",
        )
        polls = []
        total = 0
        for row in rows:
            record = dict(_shape(row, _RESPONSE_FIELDS, _RESPONSE_FIELDS, "poll_result"))
            encoded = record.pop("body_base64")
            _check(
                encoded is None
                or (type(encoded) is str and len(encoded) <= 4 * ((MAX_BODY + 2) // 3)),
                "pipeline",
                "encoded body limit",
            )
            try:
                body = base64.b64decode(encoded, validate=True) if encoded is not None else None
            except (binascii.Error, ValueError):
                raise ContractError("pipeline: invalid body encoding") from None
            _check(body is None or len(body) <= MAX_BODY, "pipeline", "decoded body limit")
            total += len(body or b"")
            _check(total <= MAX_BODY, "pipeline", "aggregate body limit")
            source_id = record.pop("source_id")
            polls.append(SourcePoll(source_id, FetchResult(body=body, **record)))
        return cls(observed, tuple(expected), tuple(polls))

    @classmethod
    def from_json(cls, value: bytes) -> PollPlan:
        return cls.from_dict(_json(value))


def _batch_reference(batch: PollBatch) -> str:
    return _digest(
        _canonical(
            {
                "previous_ref": batch.previous.digest,
                "observed_at": batch.observed_at.isoformat().replace("+00:00", "Z"),
                "items": [item.to_dict() for item in batch.items],
                "checkpoints": [checkpoint.to_dict() for checkpoint in batch.checkpoints],
                "outcomes": [asdict(outcome) for outcome in batch.outcomes],
            }
        )
    )


@dataclass(frozen=True, slots=True, repr=False)
class Collection:
    previous: Snapshot
    plan: PollPlan
    code_ref: str
    batch_ref: str
    _batch: PollBatch = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _fixture(self.previous)
        _check(type(self.plan) is PollPlan, "pipeline", "validated poll plan required")
        _reference(self.code_ref, 40)
        _reference(self.batch_ref, 64)
        batch = reduce_polls(
            self.previous,
            self.plan.polls,
            expected_source_ids=self.plan.expected_source_ids,
            observed_at=self.plan.observed_at,
        )
        _check(
            len(batch.items) <= MAX_PIPELINE_ITEMS and _batch_reference(batch) == self.batch_ref,
            "pipeline",
            "result reference mismatch",
        )
        object.__setattr__(self, "_batch", batch)
        self.to_json()

    @property
    def batch(self) -> PollBatch:
        return self._batch

    def require_usable(self) -> None:
        _fixture(self.previous)
        try:
            self.batch.require_publishable()
        except ContractError:
            raise UnusableHealth("pipeline: unusable source health") from None

    @property
    def configuration_ref(self) -> str:
        return _digest(
            _canonical(
                {
                    "sources": [source.to_dict() for source in self.previous.sources],
                    "expected_source_ids": list(self.plan.expected_source_ids),
                    "lead_policy": LEAD_POLICY,
                }
            )
        )

    def to_json(self) -> bytes:
        return _canonical(
            {
                "schema_version": 1,
                "kind": "synthetic-collection",
                "previous": self.previous.to_dict(),
                "plan": self.plan.to_dict(),
                "code_ref": self.code_ref,
                "batch_ref": self.batch_ref,
            }
        )

    @property
    def digest(self) -> str:
        return _digest(self.to_json())

    @classmethod
    def from_json(cls, value: bytes) -> Collection:
        fields = {"schema_version", "kind", "previous", "plan", "code_ref", "batch_ref"}
        data = _shape(_json(value), fields, fields, "collection")
        _version(data["schema_version"], data["kind"], "synthetic-collection")
        return cls(
            Snapshot.from_dict(data["previous"]),
            PollPlan.from_dict(data["plan"]),
            data["code_ref"],
            data["batch_ref"],
        )


def collect(previous: Snapshot, plan: PollPlan, *, code_ref: str) -> Collection:
    """Collect supplied synthetic results; no clock lookup, transport, grouping or storage."""
    _fixture(previous)
    _check(type(plan) is PollPlan, "pipeline", "validated poll plan required")
    _reference(code_ref, 40)
    batch = reduce_polls(
        previous,
        plan.polls,
        expected_source_ids=plan.expected_source_ids,
        observed_at=plan.observed_at,
    )
    _check(len(batch.items) <= MAX_PIPELINE_ITEMS, "pipeline", "retained item limit")
    return Collection(previous, plan, code_ref, _batch_reference(batch))


def summary(collection: Collection, stage: str, *, dry_run: bool = False) -> dict[str, object]:
    _check(type(collection) is Collection, "pipeline", "validated collection required")
    _fixture(collection.previous)
    _check(
        stage in {"collect", "build", "check"} and type(dry_run) is bool,
        "pipeline",
        "invalid stage",
    )
    batch = collection.batch
    return {
        "schema_version": 1,
        "stage": stage,
        "synthetic": True,
        "not_deployed": True,
        "dry_run": dry_run,
        "health": batch.health,
        "no_new": batch.no_new,
        "expected_sources": len(batch.outcomes),
        "successful_sources": sum(outcome.usable for outcome in batch.outcomes),
        "failed_sources": sum(not outcome.usable for outcome in batch.outcomes),
        "items": len(batch.items),
        "new_items": sum(outcome.new_items for outcome in batch.outcomes),
        "updated_items": sum(outcome.updated_items for outcome in batch.outcomes),
        "warnings": sorted({warning for outcome in batch.outcomes for warning in outcome.warnings}),
    }


@dataclass(frozen=True, slots=True, repr=False)
class BuildResult:
    snapshot: Snapshot
    html: bytes
    stylesheet: bytes
    manifest: bytes

    def files(self) -> dict[str, bytes]:
        return {
            "index.html": self.html,
            "styles.css": self.stylesheet,
            "manifest.json": self.manifest,
        }


def build(collection: Collection, stylesheet: bytes) -> BuildResult:
    """Validate current source health, regroup completely, then render a synthetic candidate."""
    _check(type(collection) is Collection, "pipeline", "validated collection required")
    _fixture(collection.previous)
    collection.require_usable()
    _check(
        type(stylesheet) is bytes and 0 < len(stylesheet) <= MAX_STYLESHEET_BYTES,
        "pipeline",
        "bounded stylesheet required",
    )
    try:
        stylesheet.decode("utf-8")
    except UnicodeError:
        raise ContractError("pipeline: invalid stylesheet encoding") from None
    batch = collection.batch
    clusters = group_items(
        batch.items,
        batch.previous.sources,
        lead_evidence=tuple(LeadEvidence(item.id) for item in batch.items),
        previous_clusters=batch.previous_clusters,
    )
    snapshot = batch.to_snapshot(clusters=clusters)
    html = render_digest(snapshot).encode("utf-8")
    configuration_ref = _digest(
        _canonical(
            {
                "collection_configuration_ref": collection.configuration_ref,
                "stylesheet_ref": _digest(stylesheet),
                "lead_policy": LEAD_POLICY,
            }
        )
    )
    manifest = _canonical(
        {
            "schema_version": 1,
            "kind": "synthetic-candidate",
            "not_deployed": True,
            "observed_at": batch.observed_at.isoformat().replace("+00:00", "Z"),
            "code_ref": collection.code_ref,
            "configuration_ref": configuration_ref,
            "collection_ref": collection.digest,
            "previous_state_ref": collection.previous.digest,
            "batch_ref": collection.batch_ref,
            "state_ref": snapshot.digest,
            "health": summary(collection, "build"),
            "artifacts": {"index.html": _digest(html), "styles.css": _digest(stylesheet)},
        },
        limit=MAX_MANIFEST_BYTES,
    )
    return BuildResult(snapshot, html, stylesheet, manifest)


def check(
    collection: Collection, candidate: dict[str, bytes], stylesheet: bytes
) -> dict[str, object]:
    """Reproduce expected bytes in memory; self-rehashed or incomplete manifests are insufficient."""
    expected = build(collection, stylesheet)
    if type(candidate) is not dict or set(candidate) != set(FILES):
        raise CandidateMismatch("pipeline: candidate inventory mismatch")
    for name, data in candidate.items():
        if type(data) is not bytes or len(data) > FILES[name] or data != expected.files()[name]:
            raise CandidateMismatch("pipeline: candidate content mismatch")
    return summary(collection, "check")
