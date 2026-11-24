#!/usr/bin/env python3
"""Aggregate A3 CSV results and generate report figures."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "results" / "raw"
FIGURE_DIR = PROJECT_DIR / "results" / "figures"


def read_rows(name: str) -> list[dict[str, str]]:
    with (RAW_DIR / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize(
    rows: list[dict[str, str]], group_key: str, value_keys: tuple[str, ...]
) -> list[dict[str, float]]:
    grouped: dict[float, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[float(row[group_key])].append(row)
    summaries: list[dict[str, float]] = []
    for group, group_rows in sorted(grouped.items()):
        summary = {group_key: group, "runs": float(len(group_rows))}
        for value_key in value_keys:
            values = [float(row[value_key]) for row in group_rows]
            summary[value_key] = mean(values)
            summary[f"{value_key}_ci95"] = (
                1.96 * stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0.0
            )
        summaries.append(summary)
    return summaries


def write_summary(name: str, rows: list[dict[str, float]]) -> None:
    with (RAW_DIR / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_validation() -> None:
    rows = read_rows("experiment_0_validation.csv")
    for row in rows:
        row["simulated_no_collision_probability"] = str(
            1.0 - float(row["collision_probability"])
        )
    summary = summarize(
        rows,
        "ue_count",
        (
            "analytical_no_collision_probability",
            "simulated_no_collision_probability",
        ),
    )
    for row in summary:
        row["absolute_error"] = abs(
            row["simulated_no_collision_probability"]
            - row["analytical_no_collision_probability"]
        )
    write_summary("experiment_0_summary.csv", summary)
    x = [row["ue_count"] for row in summary]
    plt.figure(figsize=(7, 4.5))
    plt.plot(x, [row["analytical_no_collision_probability"] for row in summary], "o-", label="Analytical")
    plt.errorbar(
        x,
        [row["simulated_no_collision_probability"] for row in summary],
        yerr=[row["simulated_no_collision_probability_ci95"] for row in summary],
        fmt="s--",
        capsize=4,
        label="ns-3 simulation (95% CI)",
    )
    plt.xlabel("Number of simultaneously contending UEs")
    plt.ylabel("Per-transmission no-collision probability")
    plt.xscale("log")
    plt.xlim(min(x) * 0.8, max(x) * 1.2)
    plt.ylim(-0.02, 1.05)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "figure_1_collision_validation.png", dpi=180)
    plt.close()


def plot_load() -> None:
    rows = read_rows("experiment_1_load.csv")
    summary = summarize(
        rows,
        "ue_count",
        (
            "success_probability",
            "collision_probability",
            "mean_access_delay_ms",
            "mean_attempts",
        ),
    )
    write_summary("experiment_1_summary.csv", summary)
    x = [row["ue_count"] for row in summary]
    plt.figure(figsize=(7, 4.5))
    plt.errorbar(
        x,
        [row["success_probability"] for row in summary],
        yerr=[row["success_probability_ci95"] for row in summary],
        fmt="o-",
        capsize=4,
    )
    plt.xlabel("Number of UEs")
    plt.ylabel("UE random access success probability")
    plt.xscale("log")
    plt.xlim(min(x) * 0.8, max(x) * 1.2)
    plt.ylim(-0.02, 1.05)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "figure_2_load_success.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7, 4.5))
    delay_values = [
        row["mean_access_delay_ms"]
        if row["success_probability"] > 0.0
        else math.nan
        for row in summary
    ]
    delay_errors = [
        row["mean_access_delay_ms_ci95"]
        if row["success_probability"] > 0.0
        else math.nan
        for row in summary
    ]
    plt.errorbar(
        x,
        delay_values,
        yerr=delay_errors,
        fmt="o-",
        capsize=4,
    )
    plt.xlabel("Number of UEs")
    plt.ylabel("Mean RA completion delay of successful UEs (ms)")
    plt.xscale("log")
    plt.xlim(min(x) * 0.8, max(x) * 1.2)
    for row in summary:
        if row["success_probability"] == 0.0:
            plt.text(
                row["ue_count"],
                min(value for value in delay_values if not math.isnan(value)),
                "No successful UEs",
                ha="right",
                va="bottom",
                rotation=90,
                fontsize=8,
            )
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "figure_3_load_delay.png", dpi=180)
    plt.close()


def plot_delay() -> None:
    rows = read_rows("experiment_2_delay.csv")
    summary = summarize(
        rows,
        "one_way_delay_ms",
        ("mean_access_delay_ms", "p95_access_delay_ms", "success_probability"),
    )
    write_summary("experiment_2_summary.csv", summary)
    x = [row["one_way_delay_ms"] for row in summary]
    plt.figure(figsize=(7, 4.5))
    plt.errorbar(
        x,
        [row["mean_access_delay_ms"] for row in summary],
        yerr=[row["mean_access_delay_ms_ci95"] for row in summary],
        fmt="o-",
        capsize=4,
        label="Mean",
    )
    plt.plot(x, [row["p95_access_delay_ms"] for row in summary], "s--", label="95th percentile")
    plt.xlabel("One-way UE-to-gNB propagation delay (ms)")
    plt.ylabel("RA completion delay (ms)")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "figure_4_propagation_delay.png", dpi=180)
    plt.close()


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plot_validation()
    plot_load()
    plot_delay()


if __name__ == "__main__":
    main()
