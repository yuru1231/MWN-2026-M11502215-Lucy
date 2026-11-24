#!/usr/bin/env python3
"""Run the ns-3 runs that reproduce Lin & Cheng (2023) Fig. 4 (Scenario I).

Matrix: patterns (ii), (iii), (iv) x M values, N_PTmax = 5, W_BO = 120,
RngSeed = 20261124, RngRun = 1..RUNS, SAMPLES one-shot samples per run.

Usage (Windows default executable, or pass --exe for a Linux/WSL build):
    python scripts/run_baseline.py [--runs 30] [--samples 1000] [--jobs 8]
"""

from __future__ import annotations

import argparse
import csv
import math
import subprocess
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = PROJECT_DIR.parent
DEFAULT_EXE = (
    REPO_DIR / "ns-3-dev" / "build" / "scratch" / "a4-beam-ra" / "ns3-dev-beam-ra-sim-static.exe"
)
RAW_DIR = PROJECT_DIR / "results" / "baseline" / "raw"

SEED = 20261124
PATTERNS = ("ii", "iii", "iv")
M_VALUES = (1, 2, 5, 10, 20, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000,
            1200, 1400, 1600, 1800, 2000)
NPT_MAX = 5
W_BO = 120
CDF_M = 1000


def one_run(exe: str, pattern: str, m: int, run: int, samples: int, tmp: Path) -> tuple[Path, Path | None]:
    out = tmp / f"{pattern}_{m}_{run}.csv"
    hist = tmp / f"{pattern}_{m}_{run}_hist.csv" if m == CDF_M else None
    args = [exe, f"--pattern={pattern}", f"--ueCount={m}", f"--nptMax={NPT_MAX}",
            f"--wbo={W_BO}", f"--samples={samples}", f"--seed={SEED}", f"--run={run}",
            f"--outputFile={out.as_posix()}"]
    if hist:
        args.append(f"--histFile={hist.as_posix()}")
    subprocess.run(args, check=True)
    return out, hist


def merge(paths: list[Path], target: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for p in paths:
        with p.open(newline="", encoding="utf-8") as fh:
            rows.extend(csv.DictReader(fh))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def summarize(rows: list[dict[str, str]], target: Path) -> None:
    groups: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        groups[(r["pattern"], int(r["ue_count"]))].append(r)
    fields = ["pattern", "ue_count", "runs", "samples_per_run", "ps_mean", "ps_ci95",
              "da_ms_mean", "da_ms_ci95", "collision_mean", "ps_per_tx_mean"]
    with target.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for (pat, m), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            out = {"pattern": pat, "ue_count": m, "runs": len(rs),
                   "samples_per_run": rs[0]["samples"]}
            for key, name in (("ps", "ps"), ("da_ms", "da_ms")):
                vals = [float(r[key]) for r in rs]
                mean = sum(vals) / len(vals)
                sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) if len(vals) > 1 else 0.0
                out[f"{name}_mean"] = f"{mean:.6f}"
                out[f"{name}_ci95"] = f"{1.96 * sd / math.sqrt(len(vals)):.6f}"
            out["collision_mean"] = f"{sum(float(r['collision_prob']) for r in rs) / len(rs):.6f}"
            out["ps_per_tx_mean"] = f"{sum(float(r['ps_per_tx']) for r in rs) / len(rs):.6f}"
            w.writerow(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exe", default=str(DEFAULT_EXE))
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--samples", type=int, default=3334)  # 30 x 3334 ~ 1e5, as in the paper
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--collect", action="store_true",
                    help="only merge raw/fig4_runs_<pattern>.csv and raw/fig4_hist_<pattern>.csv "
                         "copied back from another machine, then summarize")
    a = ap.parse_args()

    if a.collect:
        parts = sorted(RAW_DIR.glob("fig4_runs_*.csv"))
        hists = sorted(h for h in RAW_DIR.glob("fig4_hist_*.csv")
                       if h.name != f"fig4_hist_M{CDF_M}.csv")
        if not parts:
            raise SystemExit(f"no fig4_runs_<pattern>.csv files in {RAW_DIR}")
        rows = merge(parts, RAW_DIR / "fig4_runs.csv")
        if hists:
            merge(hists, RAW_DIR / f"fig4_hist_M{CDF_M}.csv")
        summarize(rows, RAW_DIR / "fig4_summary.csv")
        print(f"collected {len(rows)} runs from {len(parts)} files -> {RAW_DIR}")
        return

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        jobs = [(p, m, r) for p in PATTERNS for m in M_VALUES for r in range(1, a.runs + 1)]
        with ThreadPoolExecutor(a.jobs) as pool:
            results = list(pool.map(lambda j: one_run(a.exe, *j, a.samples, tmp), jobs))
        rows = merge([o for o, _ in results], RAW_DIR / "fig4_runs.csv")
        merge([h for _, h in results if h], RAW_DIR / f"fig4_hist_M{CDF_M}.csv")
    summarize(rows, RAW_DIR / "fig4_summary.csv")
    print(f"{len(rows)} runs -> {RAW_DIR}")


if __name__ == "__main__":
    main()
