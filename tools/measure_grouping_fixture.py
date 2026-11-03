"""Measure only committed fictional contract data; a valid score is not a passing gold gate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from benchmarks.support import load_fixture  # noqa: E402

from wrap_brief.grouping.benchmark import evaluate  # noqa: E402
from wrap_brief.models import ContractError  # noqa: E402


def main() -> None:
    try:
        at, scenarios = load_fixture()
        report = evaluate(scenarios, dataset_kind="synthetic", observed_at=at)
    except (ContractError, OSError, ValueError, TypeError, RecursionError):
        raise SystemExit(
            "Synthetic benchmark input failed; raw input details are withheld."
        ) from None
    print(report.to_json().decode("utf-8"))


if __name__ == "__main__":
    main()
