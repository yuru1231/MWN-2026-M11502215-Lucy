#!/usr/bin/env python3
"""Validate the massive-UE experiment CSV files and configurations."""

from __future__ import annotations

import csv
import math
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "results" / "massive" / "raw"
OLD_FIELDS = {
    "experiment_id", "scenario", "seed", "run", "ue_count", "ra_resources",
    "one_way_delay_ms", "ro_period_ms", "max_attempts", "backoff_window_ms",
    "simulation_duration_ms", "attempted_ues", "successful_ues", "failed_ues",
    "unfinished_ues", "total_attempts", "total_preamble_transmissions",
    "collided_preamble_transmissions", "success_probability", "collision_probability",
    "mean_access_delay_ms", "p95_access_delay_ms", "mean_attempts",
}
NEW_FIELDS = {
    "arrival_model", "arrival_window_ms", "backoff_max_ms", "offered_ues",
    "activated_ues", "not_activated_ues", "mean_completion_time_ms",
    "p95_completion_time_ms",
}
EXPECTED = {
    "massive_exp1.csv": (120, {(1000, 48, 20, 8), (3000, 48, 20, 8), (5000, 48, 20, 8), (10000, 48, 20, 8)}),
    "massive_exp2a.csv": (90, {(5000, 32, 20, 8), (5000, 48, 20, 8), (5000, 64, 20, 8)}),
    "massive_exp2b.csv": (90, {(5000, 48, 10, 8), (5000, 48, 20, 8), (5000, 48, 40, 8)}),
    "massive_exp3.csv": (150, {(3000, 48, 20, 4), (3000, 48, 20, 8), (3000, 48, 20, 12), (3000, 48, 20, 16), (3000, 48, 20, 20)}),
}


def numeric_key(row: dict[str, str]) -> tuple[int, int, int, int]:
    return (
        int(row["ue_count"]),
        int(row["ra_resources"]),
        int(float(row["ro_period_ms"])),
        int(float(row["one_way_delay_ms"])),
    )


def check_file(name: str, expected_rows: int, expected_cases: set[tuple[int, int, int, int]]) -> None:
    path = RAW_DIR / name
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        rows = list(reader)
    if not OLD_FIELDS | NEW_FIELDS <= fields:
        raise AssertionError(f"{name}: missing schema fields {(OLD_FIELDS | NEW_FIELDS) - fields}")
    if len(rows) != expected_rows:
        raise AssertionError(f"{name}: expected {expected_rows} rows, found {len(rows)}")
    if {numeric_key(row) for row in rows} != expected_cases:
        raise AssertionError(f"{name}: experiment matrix differs from specification")

    for line_number, row in enumerate(rows, 2):
        attempted = int(row["attempted_ues"])
        successful = int(row["successful_ues"])
        failed = int(row["failed_ues"])
        unfinished = int(row["unfinished_ues"])
        attempts = int(row["total_attempts"])
        if attempted != successful + failed + unfinished:
            raise AssertionError(f"{name}:{line_number}: UE conservation failed")
        if int(row["activated_ues"]) != attempted or int(row["not_activated_ues"]) != 0:
            raise AssertionError(f"{name}:{line_number}: activation accounting failed")
        if attempts > attempted * int(row["max_attempts"]):
            raise AssertionError(f"{name}:{line_number}: maximum attempts exceeded")
        if unfinished != 0:
            raise AssertionError(f"{name}:{line_number}: 15-second horizon left unfinished UEs")
        if row["arrival_model"] != "uniform":
            raise AssertionError(f"{name}:{line_number}: incorrect arrival model")
        for field in ("success_probability", "collision_probability"):
            value = float(row[field])
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise AssertionError(f"{name}:{line_number}: invalid {field}")


def main() -> int:
    for name, (row_count, cases) in EXPECTED.items():
        check_file(name, row_count, cases)
        print(f"PASS {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
