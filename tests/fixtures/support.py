"""Small, bounded fixture readers/builders shared by offline test consumers."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
MAX_STATIC_BYTES = 65_536
MAX_RECIPE_BYTES = 4_194_304


def read_bytes(name: str) -> bytes:
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or "\\" in name
        or not path.parts
        or any(p.startswith(".") for p in path.parts)
    ):
        raise ValueError("Unsafe fixture path")
    candidate = ROOT / path
    if candidate.is_symlink() or not candidate.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Unsafe fixture path")
    with candidate.open("rb") as stream:
        data = stream.read(MAX_STATIC_BYTES + 1)
    if len(data) > MAX_STATIC_BYTES:
        raise ValueError("Static fixture is too large")
    return data


def read_json(name: str) -> dict[str, object]:
    value = json.loads(read_bytes(name).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Fixture object required")
    return value


def recipe_bytes(recipe: dict[str, object]) -> bytes:
    """Generate limit probes only from a small fixed recipe vocabulary; never eval data."""
    kind, size = recipe.get("kind"), recipe.get("size")
    if type(size) is not int or size < 0:
        raise ValueError("Invalid fixture recipe size")
    if kind == "bytes" and size <= MAX_RECIPE_BYTES:
        return b"x" * size
    if kind == "depth" and 2 <= size <= 128:
        return (
            b"<rss><channel>"
            + b"<node>" * (size - 2)
            + b"</node>" * (size - 2)
            + b"</channel></rss>"
        )
    if kind == "title" and size <= 8192:
        item = (
            b"<item><title>"
            + b"x" * size
            + b"</title><link>https://example.com/recipe</link></item>"
        )
    elif kind == "items" and size <= 1000:
        item = (
            b"<item><title>Synthetic recipe</title><link>https://example.com/recipe</link></item>"
            * size
        )
    else:
        raise ValueError("Unsupported or oversized fixture recipe")
    return b'<rss version="2.0"><channel>' + item + b"</channel></rss>"
