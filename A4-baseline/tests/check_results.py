#!/usr/bin/env python3
"""Check deterministic and conservation properties in generated CSV files."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


def check_file(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise AssertionError(f"{path} is empty")
    for line_number, row in enumerate(rows, start=2):
        attempted = int(row["attempted_ues"])
        terminal = (
            int(row["successful_ues"])
            + int(row["failed_ues"])
            + int(row["unfinished_ues"])
        )
        if attempted != terminal:
            raise AssertionError(f"{path}:{line_number}: UE conservation failed")
        if int(row["total_attempts"]) > attempted * int(row["max_attempts"]):
            raise AssertionError(f"{path}:{line_number}: maximum attempts exceeded")
        for field in ("success_probability", "collision_probability"):
            value = float(row[field])
            if not 0.0 <= value <= 1.0:
                raise AssertionError(f"{path}:{line_number}: {field} outside [0,1]")


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: check_results.py CSV [CSV ...]")
    for argument in sys.argv[1:]:
        check_file(Path(argument))
        print(f"PASS {argument}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
