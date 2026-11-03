"""Exhaustive mixed-batch measurement, not a rights or independent-label approval gate."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from itertools import combinations

from wrap_brief.grouping.overrides import _canonical, _hash, _public_ref
from wrap_brief.grouping.stories import LeadEvidence, group_items
from wrap_brief.models import _check, _choice, _identifier, _text, _utc, _version
from wrap_brief.state.snapshot import Snapshot

CATEGORIES = frozenset(
    {
        "direct",
        "same_game_events",
        "review_preview",
        "localization",
        "rumor_confirmation",
        "syndication",
        "resurfacing",
        "tracking",
        "corrections",
        "editions",
        "versions",
        "ambiguity",
    }
)
MAX_SCENARIOS = 50
MAX_SCENARIO_ITEMS = 50
MAX_PAIRS = 10_000
MAX_CORPUS_BYTES = 4_194_304


@dataclass(frozen=True, slots=True, repr=False)
class GoldScenario:
    id: str
    category: str
    snapshot: Snapshot
    lead_evidence: tuple[LeadEvidence, ...]
    gold_groups: tuple[tuple[str, ...], ...]
    rationale: str
    labeling_ref: str
    reviewed_at: datetime
    schema_version: int = 1

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.id, "scenario_id")
        _choice(self.category, set(CATEGORIES), "category")
        _text(self.rationale, "rationale", 500)
        _public_ref(self.labeling_ref)
        object.__setattr__(self, "reviewed_at", _utc(self.reviewed_at, "reviewed_at"))
        _check(
            type(self.snapshot) is Snapshot and 2 <= len(self.snapshot.items) <= MAX_SCENARIO_ITEMS,
            "scenario",
            "bounded mixed-batch snapshot required",
        )
        state = Snapshot.from_json(self.snapshot.to_json())
        _check(
            not state.clusters and state.observed_at <= self.reviewed_at,
            "scenario",
            "ungrouped state and dated labels required",
        )
        _check(
            type(self.lead_evidence) is tuple
            and len(self.lead_evidence) == len(state.items)
            and all(type(value) is LeadEvidence for value in self.lead_evidence),
            "lead_evidence",
            "complete immutable evidence required",
        )
        policies = {value.item_id: LeadEvidence(**asdict(value)) for value in self.lead_evidence}
        ids = {item.id for item in state.items}
        _check(
            len(policies) == len(self.lead_evidence) and set(policies) == ids,
            "lead_evidence",
            "exactly one record per item required",
        )
        _check(
            type(self.gold_groups) is tuple and 0 < len(self.gold_groups) <= MAX_SCENARIO_ITEMS,
            "gold_groups",
            "bounded immutable partition required",
        )
        seen = set()
        for part in self.gold_groups:
            _check(
                type(part) is tuple and 0 < len(part) <= MAX_SCENARIO_ITEMS,
                "gold_groups",
                "nonempty immutable partition required",
            )
            for item_id in part:
                _identifier(item_id, "item_id")
            _check(
                len(set(part)) == len(part) and not seen.intersection(part),
                "gold_groups",
                "overlapping gold membership",
            )
            seen.update(part)
        _check(seen == ids, "gold_groups", "complete gold partition required")
        object.__setattr__(
            self, "gold_groups", tuple(sorted(tuple(sorted(part)) for part in self.gold_groups))
        )
        object.__setattr__(
            self,
            "lead_evidence",
            tuple(sorted(self.lead_evidence, key=lambda value: value.item_id)),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "category": self.category,
            "snapshot": self.snapshot.to_dict(),
            "lead_evidence": [asdict(value) for value in self.lead_evidence],
            "gold_groups": [list(part) for part in self.gold_groups],
            "rationale": self.rationale,
            "labeling_ref": self.labeling_ref,
            "reviewed_at": self.reviewed_at.isoformat().replace("+00:00", "Z"),
        }


@dataclass(frozen=True, slots=True)
class PairCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    def __post_init__(self) -> None:
        _check(
            all(
                type(value) is int and 0 <= value <= MAX_PAIRS
                for value in (self.tp, self.fp, self.fn, self.tn)
            ),
            "counts",
            "bounded nonnegative integers required",
        )
        _check(self.pairs <= MAX_PAIRS, "counts", "pair limit")

    @property
    def pairs(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    @property
    def numeric_target_met(self) -> bool:
        return (
            self.pairs >= 100
            and self.tp + self.fp > 0
            and 100 * self.tp >= 98 * (self.tp + self.fp)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "pairs": self.pairs,
            "positive_pairs": self.tp + self.fn,
            "negative_pairs": self.fp + self.tn,
            "predicted_merges": self.tp + self.fp,
            "precision": self.precision,
            "recall": self.recall,
        }


@dataclass(frozen=True, slots=True, repr=False)
class BenchmarkReport:
    dataset_kind: str
    corpus_ref: str
    scenario_count: int
    gold_group_count: int
    counts: PairCounts
    categories: tuple[tuple[str, PairCounts], ...]
    false_merges: tuple[tuple[str, str, str], ...]

    def __post_init__(self) -> None:
        _choice(self.dataset_kind, {"synthetic", "private_evaluation"}, "dataset_kind")
        _check(
            type(self.corpus_ref) is str
            and re.fullmatch(r"[a-f0-9]{64}", self.corpus_ref) is not None,
            "corpus_ref",
            "SHA-256 reference required",
        )
        _check(
            type(self.scenario_count) is int
            and 0 < self.scenario_count <= MAX_SCENARIOS
            and type(self.gold_group_count) is int
            and 0 < self.gold_group_count <= MAX_SCENARIOS * MAX_SCENARIO_ITEMS
            and type(self.counts) is PairCounts,
            "report",
            "bounded counts required",
        )
        _check(
            type(self.categories) is tuple
            and len(self.categories) == len(CATEGORIES)
            and all(
                type(row) is tuple and len(row) == 2 and type(row[1]) is PairCounts
                for row in self.categories
            ),
            "categories",
            "exhaustive immutable counts required",
        )
        for category, _ in self.categories:
            _choice(category, set(CATEGORIES), "category")
        _check(
            {row[0] for row in self.categories} == CATEGORIES,
            "categories",
            "missing or duplicate category",
        )
        _check(
            all(
                sum(getattr(row[1], key) for row in self.categories) == getattr(self.counts, key)
                for key in ("tp", "fp", "fn", "tn")
            ),
            "categories",
            "aggregate mismatch",
        )
        _check(
            type(self.false_merges) is tuple and len(self.false_merges) == self.counts.fp,
            "false_merges",
            "complete private diagnostics required",
        )
        for row in self.false_merges:
            _check(
                type(row) is tuple and len(row) == 3, "false_merges", "bounded identifiers required"
            )
            for value in row:
                _identifier(value, "pair_reference")
        _check(
            len(set(self.false_merges)) == len(self.false_merges),
            "false_merges",
            "duplicate diagnostic",
        )
        object.__setattr__(self, "categories", tuple(sorted(self.categories)))

    def summary(self) -> dict[str, object]:
        """Only aggregate fixed-category fields; private diagnostic pair identities are omitted."""
        return {
            "schema_version": 1,
            "dataset_kind": self.dataset_kind,
            "corpus_ref": self.corpus_ref,
            "scenario_count": self.scenario_count,
            "gold_group_count": self.gold_group_count,
            "counts": self.counts.to_dict(),
            "numeric_target_met": self.counts.numeric_target_met,
            "real_corpus_qualification": "not_assessed",
            "categories": {category: counts.to_dict() for category, counts in self.categories},
        }

    def to_json(self) -> bytes:
        return _canonical(self.summary())


def evaluate(
    scenarios: Sequence[GoldScenario], *, dataset_kind: str, observed_at: datetime
) -> BenchmarkReport:
    _choice(dataset_kind, {"synthetic", "private_evaluation"}, "dataset_kind")
    at = _utc(observed_at, "observed_at")
    _check(
        isinstance(scenarios, Sequence)
        and 0 < len(scenarios) <= MAX_SCENARIOS
        and all(type(value) is GoldScenario for value in scenarios),
        "scenarios",
        "bounded reviewed scenarios required",
    )
    _check(
        len({value.id for value in scenarios}) == len(scenarios),
        "scenarios",
        "duplicate identifier",
    )
    _check(all(value.reviewed_at <= at for value in scenarios), "reviewed_at", "future labels")
    total_pairs = sum(
        len(value.snapshot.items) * (len(value.snapshot.items) - 1) // 2 for value in scenarios
    )
    _check(total_pairs <= MAX_PAIRS, "scenarios", "pair limit")
    ordered = tuple(sorted((replace(value) for value in scenarios), key=lambda value: value.id))
    item_ids = [item.id for value in ordered for item in value.snapshot.items]
    _check(len(set(item_ids)) == len(item_ids), "scenarios", "reused item across scenarios")
    payload = {"dataset_kind": dataset_kind, "scenarios": [value.to_dict() for value in ordered]}
    _check(len(_canonical(payload)) <= MAX_CORPUS_BYTES, "scenarios", "corpus byte limit")
    totals = {key: 0 for key in ("tp", "fp", "fn", "tn")}
    categories = {category: dict(totals) for category in CATEGORIES}
    false_merges = []
    for scenario in ordered:
        predicted = group_items(
            scenario.snapshot.items, scenario.snapshot.sources, lead_evidence=scenario.lead_evidence
        )
        predicted_index = {key: n for n, group in enumerate(predicted) for key in group.member_ids}
        gold_index = {key: n for n, part in enumerate(scenario.gold_groups) for key in part}
        for left, right in combinations(sorted(gold_index), 2):
            actual = gold_index[left] == gold_index[right]
            merged = predicted_index[left] == predicted_index[right]
            key = "tp" if merged and actual else "fp" if merged else "fn" if actual else "tn"
            totals[key] += 1
            categories[scenario.category][key] += 1
            if key == "fp":
                false_merges.append((scenario.id, left, right))
    counts = PairCounts(**totals)
    _check(counts.pairs == total_pairs, "benchmark", "incomplete score")
    return BenchmarkReport(
        dataset_kind,
        _hash("wrap-brief:grouping-corpus:v1", payload),
        len(ordered),
        sum(len(value.gold_groups) for value in ordered),
        counts,
        tuple((category, PairCounts(**categories[category])) for category in sorted(CATEGORIES)),
        tuple(false_merges),
    )
