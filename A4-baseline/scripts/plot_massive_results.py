#!/usr/bin/env python3
"""Aggregate massive-UE results and generate figures with 95% CIs."""

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
RAW_DIR = PROJECT_DIR / "results" / "massive" / "raw"
FIGURE_DIR = PROJECT_DIR / "results" / "massive" / "figures"
METRICS = (
    "success_probability",
    "collision_probability",
    "mean_access_delay_ms",
    "p95_access_delay_ms",
    "mean_completion_time_ms",
    "p95_completion_time_ms",
    "mean_attempts",
    "failed_ues",
    "unfinished_ues",
)


def read_rows(name: str) -> list[dict[str, str]]:
    with (RAW_DIR / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize(name: str, group_key: str) -> list[dict[str, float]]:
    groups: dict[float, list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(name):
        groups[float(row[group_key])].append(row)
    output: list[dict[str, float]] = []
    for group, rows in sorted(groups.items()):
        summary = {group_key: group, "runs": float(len(rows))}
        for metric in METRICS:
            values = [float(row[metric]) for row in rows]
            summary[metric] = mean(values)
            summary[f"{metric}_ci95"] = (
                1.96 * stdev(values) / math.sqrt(len(values)) if len(values) > 1 else 0.0
            )
        output.append(summary)
    path = RAW_DIR / name.replace(".csv", "_summary.csv")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    return output


def errorbar(axis, x, rows, metric: str, label: str, marker: str = "o") -> None:
    axis.errorbar(
        x,
        [row[metric] for row in rows],
        yerr=[row[f"{metric}_ci95"] for row in rows],
        marker=marker,
        capsize=3,
        label=label,
    )


def plot_experiment(
    rows: list[dict[str, float]],
    group_key: str,
    x_label: str,
    output_name: str,
    log_x: bool = False,
) -> None:
    x = [row[group_key] for row in rows]
    figure, axes = plt.subplots(2, 2, figsize=(10, 7.2))
    errorbar(axes[0, 0], x, rows, "success_probability", "Success")
    errorbar(axes[0, 0], x, rows, "collision_probability", "Collision", "s")
    axes[0, 0].set_ylabel("Probability")
    axes[0, 0].set_ylim(-0.02, 1.02)
    axes[0, 0].legend()

    errorbar(axes[0, 1], x, rows, "mean_access_delay_ms", "Mean")
    errorbar(axes[0, 1], x, rows, "p95_access_delay_ms", "P95", "s")
    axes[0, 1].set_ylabel("Successful-UE access delay (ms)")
    axes[0, 1].legend()

    errorbar(axes[1, 0], x, rows, "mean_attempts", "Mean attempts")
    axes[1, 0].set_ylabel("Attempts per activated UE")

    errorbar(axes[1, 1], x, rows, "failed_ues", "Failed UEs")
    errorbar(axes[1, 1], x, rows, "unfinished_ues", "Unfinished UEs", "s")
    axes[1, 1].set_ylabel("UE count")
    axes[1, 1].legend()

    for axis in axes.flat:
        axis.set_xlabel(x_label)
        axis.grid(alpha=0.3)
        if log_x:
            axis.set_xscale("log")
    figure.suptitle("Mean across 30 independent runs; error bars are 95% CIs")
    figure.tight_layout()
    figure.savefig(FIGURE_DIR / output_name, dpi=180)
    plt.close(figure)


def plot_completion_cdf() -> None:
    rows = read_rows("massive_exp1_completion_cdf.csv")
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["scenario"]].append(row)
    plt.figure(figsize=(7.2, 4.8))
    for scenario, group in sorted(groups.items(), key=lambda item: int(item[0].split("_")[1])):
        plt.plot(
            [float(row["access_delay_ms"]) for row in group],
            [float(row["cdf_probability"]) for row in group],
            label=scenario.replace("ue_", "") + " UEs",
        )
    plt.xlabel("Successful-UE access delay (ms)")
    plt.ylabel("Empirical CDF")
    plt.ylim(0.0, 1.0)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "figure_completion_time_cdf.png", dpi=180)
    plt.close()


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plot_experiment(
        summarize("massive_exp1.csv", "ue_count"),
        "ue_count",
        "Activated UEs",
        "figure_massive_ue_load.png",
        True,
    )
    plot_experiment(
        summarize("massive_exp2a.csv", "ra_resources"),
        "ra_resources",
        "Contention choices per RO",
        "figure_preamble_capacity.png",
    )
    plot_experiment(
        summarize("massive_exp2b.csv", "ro_period_ms"),
        "ro_period_ms",
        "RO period (ms)",
        "figure_ro_period.png",
    )
    plot_experiment(
        summarize("massive_exp3.csv", "one_way_delay_ms"),
        "one_way_delay_ms",
        "One-way propagation delay (ms)",
        "figure_ntn_delay.png",
    )
    plot_completion_cdf()


if __name__ == "__main__":
    main()
