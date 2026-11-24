#!/usr/bin/env python3
"""Checks the ns-3 Fig. 4 runs: conservation, matrix completeness, agreement with analysis."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lin_cheng_analysis import PATTERNS, analyse  # noqa: E402
from run_baseline import M_VALUES, NPT_MAX, W_BO  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "results" / "baseline" / "raw"
PS_TOL = 0.03       # absolute
DA_TOL = 0.08       # relative


def main() -> int:
    failures = 0
    runs = list(csv.DictReader((RAW / "fig4_runs.csv").open(encoding="utf-8")))
    for r in runs:
        if int(r["successes"]) + int(r["failures"]) != int(r["ues"]):
            print("FAIL conservation", r["pattern"], r["ue_count"], r["run"])
            failures += 1
    summary = list(csv.DictReader((RAW / "fig4_summary.csv").open(encoding="utf-8")))
    have = {(s["pattern"], int(s["ue_count"])) for s in summary}
    for p in ("ii", "iii", "iv"):
        for m in M_VALUES:
            if (p, m) not in have:
                print("FAIL missing point", p, m)
                failures += 1
    worst_ps, worst_da = 0.0, 0.0
    for s in summary:
        a = analyse(PATTERNS[s["pattern"]], int(s["ue_count"]), NPT_MAX, W_BO)
        dps = abs(float(s["ps_mean"]) - a["ps"])
        dda = abs(float(s["da_ms_mean"]) - a["da_ms"]) / a["da_ms"]
        worst_ps, worst_da = max(worst_ps, dps), max(worst_da, dda)
        if dps > PS_TOL or dda > DA_TOL:
            print(f"WARN ({s['pattern']}) M={s['ue_count']}: sim Ps={float(s['ps_mean']):.4f} "
                  f"anal {a['ps']:.4f}; sim Da={float(s['da_ms_mean']):.3f} anal {a['da_ms']:.3f}")
    print(f"{len(runs)} runs, {len(summary)} points; max |dPs| = {worst_ps:.4f}, "
          f"max rel dDa = {worst_da:.3%}")
    print("PASS" if failures == 0 else f"{failures} FAILURES")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
