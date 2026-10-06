"""Plot A2 packet-size and inter-arrival distributions from ns-3 CSV traces."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def read_packet_trace() -> list[dict[str, str]]:
    with (RESULTS / "a2_packet_trace.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def save_pdf_cdf(values: np.ndarray, xlabel: str, title: str, stem: str, bins: int = 40) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)

    axes[0].hist(values, bins=bins, density=True, color="#3b82f6", edgecolor="white")
    axes[0].set_title(f"{title} PDF")
    axes[0].set_xlabel(xlabel)
    axes[0].set_ylabel("Density")

    sorted_values = np.sort(values)
    cdf = np.arange(1, len(sorted_values) + 1) / len(sorted_values)
    axes[1].plot(sorted_values, cdf, color="#dc2626", linewidth=2)
    axes[1].set_title(f"{title} CDF")
    axes[1].set_xlabel(xlabel)
    axes[1].set_ylabel("CDF")
    axes[1].grid(True, alpha=0.3)

    fig.savefig(RESULTS / f"{stem}.png", dpi=180)
    fig.savefig(RESULTS / f"{stem}.pdf")
    plt.close(fig)


def main() -> None:
    rows = read_packet_trace()
    downlink = [r for r in rows if r["direction"] == "downlink"]
    if len(downlink) < 2:
        raise SystemExit("Need at least two downlink packets in a2_packet_trace.csv")

    packet_sizes = np.array([int(r["size_bytes"]) for r in downlink], dtype=float)
    packet_times = np.array([float(r["time_s"]) for r in downlink], dtype=float)
    inter_arrivals_ms = np.diff(packet_times) * 1000.0

    save_pdf_cdf(packet_sizes, "Packet size (bytes)", "3GPP HTTP downlink packet size",
                 "packet_size_pdf_cdf")
    save_pdf_cdf(inter_arrivals_ms, "Inter-arrival time (ms)",
                 "3GPP HTTP downlink inter-arrival", "interarrival_pdf_cdf")

    with (RESULTS / "a2_distribution_summary.txt").open("w", encoding="utf-8") as f:
        f.write("A2 3GPP HTTP distribution summary\n")
        f.write(f"Downlink packets: {len(packet_sizes)}\n")
        f.write(f"Packet size mean bytes: {packet_sizes.mean():.3f}\n")
        f.write(f"Packet size median bytes: {np.median(packet_sizes):.3f}\n")
        f.write(f"Inter-arrival mean ms: {inter_arrivals_ms.mean():.6f}\n")
        f.write(f"Inter-arrival median ms: {np.median(inter_arrivals_ms):.6f}\n")

    print("Wrote packet_size_pdf_cdf and interarrival_pdf_cdf plots.")


if __name__ == "__main__":
    main()
