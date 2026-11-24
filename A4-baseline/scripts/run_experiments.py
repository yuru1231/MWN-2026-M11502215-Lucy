#!/usr/bin/env python3
"""Run the reproducible ns-3 A3 experiment matrix."""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = PROJECT_DIR.parent
NS3_DIR = REPO_DIR / "ns-3-dev"
RAW_DIR = PROJECT_DIR / "results" / "raw"
PROGRAM = "scratch/a3-ntn-ra/ntn-ra-sim"
WINDOWS_EXECUTABLE = (
    NS3_DIR
    / "build"
    / "scratch"
    / "a3-ntn-ra"
    / "ns3-dev-ntn-ra-sim-static.exe"
)
VALIDATION_UE_COUNTS = (10, 20, 40, 80, 160)
LOAD_UE_COUNTS = (10, 20, 40, 80, 160, 320)


def ns3_command(arguments: dict[str, object]) -> list[str]:
    option_list = [f"--{key}={value}" for key, value in arguments.items()]
    if os.name == "nt":
        if not WINDOWS_EXECUTABLE.exists():
            raise FileNotFoundError(
                f"Build the simulator first: {WINDOWS_EXECUTABLE}"
            )
        return [str(WINDOWS_EXECUTABLE), *option_list]
    options = " ".join(option_list)
    run_spec = f"{PROGRAM} {options}"
    return ["./ns3", "run", run_spec]


def run_case(arguments: dict[str, object], temporary_csv: Path) -> dict[str, str]:
    complete_arguments = dict(arguments)
    complete_arguments.update(
        {
            "outputFile": temporary_csv.as_posix(),
            "printSummary": "false",
        }
    )
    subprocess.run(ns3_command(complete_arguments), cwd=NS3_DIR, check=True)
    with temporary_csv.open(newline="", encoding="utf-8") as handle:
        return next(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"No rows generated for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_validation(runs: int, temporary_csv: Path) -> None:
    rows: list[dict[str, str]] = []
    for ue_count in VALIDATION_UE_COUNTS:
        for run in range(1, runs + 1):
            row = run_case(
                {
                    "experimentId": "experiment_0",
                    "scenario": "analytical_validation",
                    "seed": 20261108,
                    "run": run,
                    "ueCount": ue_count,
                    "raResources": 32,
                    "maxAttempts": 1,
                    "roPeriodMs": 20,
                    "oneWayDelayMs": 8,
                    "msgbProcessingMs": 2,
                    "backoffWindowMs": 0,
                    "simulationDurationMs": 100,
                },
                temporary_csv,
            )
            probability = (1.0 - 1.0 / 32.0) ** (ue_count - 1)
            row["analytical_no_collision_probability"] = f"{probability:.15g}"
            rows.append(row)
    write_rows(RAW_DIR / "experiment_0_validation.csv", rows)


def run_load(runs: int, temporary_csv: Path) -> None:
    rows: list[dict[str, str]] = []
    for ue_count in LOAD_UE_COUNTS:
        for run in range(1, runs + 1):
            rows.append(
                run_case(
                    {
                        "experimentId": "experiment_1",
                        "scenario": "ue_load",
                        "seed": 20261108,
                        "run": run,
                        "ueCount": ue_count,
                        "raResources": 32,
                        "maxAttempts": 4,
                        "roPeriodMs": 20,
                        "oneWayDelayMs": 8,
                        "msgbProcessingMs": 2,
                        "backoffWindowMs": 40,
                        "simulationDurationMs": 10000,
                    },
                    temporary_csv,
                )
            )
    write_rows(RAW_DIR / "experiment_1_load.csv", rows)


def run_delay(runs: int, temporary_csv: Path) -> None:
    rows: list[dict[str, str]] = []
    for delay_ms in (4, 8, 12, 16, 20):
        for run in range(1, runs + 1):
            rows.append(
                run_case(
                    {
                        "experimentId": "experiment_2",
                        "scenario": "propagation_delay",
                        "seed": 20261108,
                        "run": run,
                        "ueCount": 20,
                        "raResources": 32,
                        "alternateResources": "true",
                        "maxAttempts": 4,
                        "roPeriodMs": 20,
                        "oneWayDelayMs": delay_ms,
                        "msgbProcessingMs": 2,
                        "backoffWindowMs": 40,
                        "simulationDurationMs": 10000,
                    },
                    temporary_csv,
                )
            )
    write_rows(RAW_DIR / "experiment_2_delay.csv", rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-runs", type=int, default=200)
    parser.add_argument("--experiment-runs", type=int, default=30)
    parser.add_argument(
        "--only",
        choices=("all", "validation", "load", "delay"),
        default="all",
    )
    args = parser.parse_args()
    if args.validation_runs < 2 or args.experiment_runs < 2:
        parser.error("run counts must be at least 2")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    temporary_csv = RAW_DIR / ".current-run.csv"
    actions = {
        "validation": lambda: run_validation(args.validation_runs, temporary_csv),
        "load": lambda: run_load(args.experiment_runs, temporary_csv),
        "delay": lambda: run_delay(args.experiment_runs, temporary_csv),
    }
    selected = actions if args.only == "all" else {args.only: actions[args.only]}
    try:
        for name, action in selected.items():
            print(f"Running {name} experiment", flush=True)
            action()
    finally:
        temporary_csv.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
