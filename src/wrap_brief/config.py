"""Bounded public source configuration; credentials and live backend state are not fields."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from wrap_brief.models import SCHEMA_VERSION, ContractError, Source, _check, _shape, _version

MAX_CONFIG_BYTES = 1_048_576
MAX_SOURCES = 100


@dataclass(frozen=True, slots=True)
class SourceRegistry:
    sources: tuple[Source, ...] = ()
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _check(
            isinstance(self.sources, tuple) and len(self.sources) <= MAX_SOURCES,
            "sources",
            "bounded tuple required",
        )
        _check(
            all(isinstance(source, Source) for source in self.sources), "sources", "invalid source"
        )
        _check(
            len({source.id for source in self.sources}) == len(self.sources),
            "sources",
            "duplicate identifier",
        )

    @property
    def enabled_sources(self) -> tuple[Source, ...]:
        return tuple(source for source in self.sources if source.enabled)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "sources": [source.to_dict() for source in self.sources],
        }

    @classmethod
    def from_dict(cls, value: object) -> SourceRegistry:
        data = _shape(value, {"schema_version", "sources"}, {"schema_version", "sources"}, "config")
        _version(data["schema_version"])
        sources = data["sources"]
        _check(
            isinstance(sources, list) and len(sources) <= MAX_SOURCES,
            "sources",
            "bounded array required",
        )
        return cls(tuple(Source.from_dict(source) for source in sources))


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _check(key not in result, "config", "duplicate JSON key")
        result[key] = value
    return result


def _invalid_number(_value: str) -> None:
    raise ContractError("config: non-finite JSON number prohibited")


def load_registry(path: Path) -> SourceRegistry:
    """Load a bounded UTF-8 JSON file explicitly; never resolve URLs or read environment secrets."""
    _check(isinstance(path, Path), "config", "Path required")
    try:
        _check(not path.is_symlink(), "config", "symlink prohibited")
        with path.open("rb") as stream:
            content = stream.read(MAX_CONFIG_BYTES + 1)
    except OSError:
        raise ContractError("config: cannot read configuration") from None
    _check(len(content) <= MAX_CONFIG_BYTES, "config", "file too large")
    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_number,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ContractError("config: invalid UTF-8 JSON") from None
    return SourceRegistry.from_dict(value)
