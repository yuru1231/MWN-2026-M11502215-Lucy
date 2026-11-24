#!/usr/bin/env python3
"""Run the independent massive-UE ns-3 experiment matrix."""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
from collections import defaultdict
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = PROJECT_DIR.parent
NS3_DIR = REPO_DIR / "ns-3-dev"
RAW_DIR = PROJECT_DIR / "results" / "massive" / "raw"
PROGRAM = "scratch/a3-ntn-ra/ntn-ra-sim"
WINDOWS_EXECUTABLE = (
    NS3_DIR
    / "build"
    / "scratch"
    / "a3-ntn-ra"
    / "ns3-dev-ntn-ra-sim-static.exe"
)
SEED = 20261108
COMMON = {
    "arrivalModel": "uniform",
    "arrivalWindowMs": 1000,
    "maxAttempts": 4,
    "backoffMaxMs": 80,
    "msgbProcessingMs": 2,
    "simulationDurationMs": 15000,
}


def ns3_command(arguments: dict[str, object]) -> list[str]:
    options = [f"--{key}={value}" for key, value in arguments.items()]
    if os.name == "nt":
        if not WINDOWS_EXECUTABLE.exists():
            raise FileNotFoundError(f"Build the simulator first: {WINDOWS_EXECUTABLE}")
        return [str(WINDOWS_EXECUTABLE), *options]
    return ["./ns3", "run", f"{PROGRAM} {' '.join(options)}"]


def run_case(
    arguments: dict[str, object], summary_path: Path, ue_path: Path
) -> tuple[dict[str, str], list[float]]:
    complete = dict(arguments)
    complete.update(
        {
            "outputFile": summary_path.as_posix(),
            "ueOutputFile": ue_path.as_posix(),
            "printSummary": "false",
        }
    )
    subprocess.run(ns3_command(complete), cwd=NS3_DIR, check=True)
    with summary_path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    delays: list[float] = []
    with ue_path.open(newline="", encoding="utf-8") as handle:
        for ue in csv.DictReader(handle):
            if ue["state"] == "RA_SUCCESS":
                delays.append(float(ue["access_delay_ms"]))
    return row, delays


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows generated for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = probability * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + fraction * (
        sorted_values[upper] - sorted_values[lower]
    )


def experiment_cases(name: str) -> list[tuple[str, dict[str, object]]]:
    if name == "exp1":
        return [
            (
                f"ue_{ue_count}",
                {"ueCount": ue_count, "raResources": 48, "roPeriodMs": 20, "oneWayDelayMs": 8},
            )
            for ue_count in (1000, 3000, 5000, 10000)
        ]
    if name == "exp2a":
        return [
            (
                f"resources_{resources}",
                {"ueCount": 5000, "raResources": resources, "roPeriodMs": 20, "oneWayDelayMs": 8},
            )
            for resources in (32, 48, 64)
        ]
    if name == "exp2b":
        return [
            (
                f"ro_{period}_ms",
                {"ueCount": 5000, "raResources": 48, "roPeriodMs": period, "oneWayDelayMs": 8},
            )
            for period in (10, 20, 40)
        ]
    if name == "exp3":
        return [
            (
                f"delay_{delay}_ms",
                {"ueCount": 3000, "raResources": 48, "roPeriodMs": 20, "oneWayDelayMs": delay},
            )
            for delay in (4, 8, 12, 16, 20)
        ]
    raise ValueError(name)


def run_experiment(name: str, runs: int, summary_path: Path, ue_path: Path) -> None:
    rows: list[dict[str, object]] = []
    delay_groups: dict[str, list[float]] = defaultdict(list)
    for scenario, varying in experiment_cases(name):
        for run in range(1, runs + 1):
            arguments = {
                **COMMON,
                **varying,
                "experimentId": f"massive_{name}",
                "scenario": scenario,
                "seed": SEED,
                "run": run,
            }
            row, delays = run_case(arguments, summary_path, ue_path)
            rows.append(row)
            delay_groups[scenario].extend(delays)
            print(f"{name}: {scenario}, run {run}/{runs}", flush=True)
    write_rows(RAW_DIR / f"massive_{name}.csv", rows)

    cdf_rows: list[dict[str, object]] = []
    for scenario, delays in delay_groups.items():
        delays.sort()
        for index in range(101):
            probability = index / 100.0
            cdf_rows.append(
                {
                    "experiment_id": f"massive_{name}",
                    "scenario": scenario,
                    "successful_ue_samples": len(delays),
                    "cdf_probability": probability,
                    "access_delay_ms": f"{percentile(delays, probability):.6f}",
                }
            )
    write_rows(RAW_DIR / f"massive_{name}_completion_cdf.csv", cdf_rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument(
        "--only", choices=("all", "exp1", "exp2a", "exp2b", "exp3"), default="all"
    )
    args = parser.parse_args()
    if args.runs < 2:
        parser.error("--runs must be at least 2")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = RAW_DIR / ".current-summary.csv"
    ue_path = RAW_DIR / ".current-ues.csv"
    selected = ("exp1", "exp2a", "exp2b", "exp3") if args.only == "all" else (args.only,)
    try:
        for name in selected:
            run_experiment(name, args.runs, summary_path, ue_path)
    finally:
        summary_path.unlink(missing_ok=True)
        ue_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
