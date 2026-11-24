#!/usr/bin/env python3
"""Plot the Fig. 4 reproduction: ns-3 simulation vs. analysis vs. published values.

Lines          = analytical model, eqs. (1)-(16), re-implemented in lin_cheng_analysis.py
Hollow markers = ns-3 simulation (mean of 30 runs; 95% CIs are smaller than the markers)
Black x        = values read from the published Fig. 4

CDFs are evaluated at u = 0, 1, ..., 12 ms (panel c) and m = 1..5 (panel d) and the
points are joined by straight lines, as in the published figure.

Outputs (results/baseline/figures/):
    fig4_reproduction.png   2x2 report figure
    slide_fig4_ab.png       panels (a)+(b), slide size
    slide_fig4_cd.png       panels (c)+(d), slide size
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lin_cheng_analysis import PATTERNS, analyse, cdf_attempts, cdf_delay  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
RES = PROJECT_DIR / "results" / "baseline"
RAW = RES / "raw"
FIG = RES / "figures"
DELTA_MS = 0.125 / 6

STYLE = {  # validated categorical slots 1-3; marker/linestyle as in the paper
    "ii": dict(color="#2a78d6", marker="o", ls="-"),
    "iii": dict(color="#1baf7a", marker="^", ls="--"),
    "iv": dict(color="#eb6834", marker="s", ls=":"),
}
INK = "#1f1f1c"
M_DENSE = sorted({int(round(10 ** (k / 40))) for k in range(0, 133)} | {2000})
NPT, WBO, M_CDF = 5, 120, 1000
U_MS = list(range(0, 13))          # CDF evaluation points for panel (c), ms


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load():
    """Analysis curves, simulation points and paper readings for every panel."""
    summary = read_csv(RAW / "fig4_summary.csv")
    hist = read_csv(RAW / f"fig4_hist_M{M_CDF}.csv")
    paper = read_csv(RES / "paper_fig4_readings.csv")
    data = {"anal": {}, "sim": {}, "paper": defaultdict(list)}
    for name in STYLE:
        p = PATTERNS[name]
        res = [analyse(p, m, NPT, WBO) for m in M_DENSE]
        r1000 = analyse(p, M_CDF, NPT, WBO)
        data["anal"][name] = {
            "a": (M_DENSE, [r["ps"] for r in res]),
            "b": (M_DENSE, [r["da_ms"] for r in res]),
            "c": (U_MS, cdf_delay(r1000, U_MS)),
            "d": (list(range(1, NPT + 1)), cdf_attempts(r1000, NPT)),
        }
        rows = [r for r in summary if r["pattern"] == name]
        sim = {}
        if rows:
            ms = [int(r["ue_count"]) for r in rows]
            sim["a"] = (ms, [float(r["ps_mean"]) for r in rows])
            sim["b"] = (ms, [float(r["da_ms_mean"]) for r in rows])
        slots, att = defaultdict(int), defaultdict(int)
        for h in hist:
            if h["pattern"] == name:
                (slots if h["kind"] == "slot" else att)[int(h["index"])] += int(h["count"])
        tot = sum(slots.values())
        if tot:
            sim["c"] = (U_MS, [sum(c for s, c in slots.items() if s <= int(u / DELTA_MS + 1e-9)) / tot
                               for u in U_MS])
            acc, f = 0, []
            for n in range(1, NPT + 1):
                acc += att[n]
                f.append(acc / tot)
            sim["d"] = (list(range(1, NPT + 1)), f)
        data["sim"][name] = sim
    for r in paper:
        data["paper"][r["panel"]].append((float(r["x"]), float(r["y"])))
    return data


def draw(ax, panel, data, scale=1.0, xlim=None, ylim=None):
    """Draw one panel: analysis lines under, ns-3 hollow markers over, paper x on top."""
    lw, ms, mew = 2.0 * scale, 7.5 * scale, 1.6 * scale
    for name, st in STYLE.items():
        x, y = data["anal"][name][panel]
        ax.plot(x, y, color=st["color"], ls=st["ls"], lw=lw, zorder=2)
        if panel in data["sim"][name]:
            sx, sy = data["sim"][name][panel]
            if xlim:
                keep = [i for i, v in enumerate(sx) if xlim[0] <= v <= xlim[1]]
                sx, sy = [sx[i] for i in keep], [sy[i] for i in keep]
            ax.plot(sx, sy, ls="none", marker=st["marker"], ms=ms, mew=mew, mec=st["color"],
                    mfc="white", zorder=3)
    pts = data["paper"].get(panel, [])
    if xlim:
        pts = [p for p in pts if xlim[0] <= p[0] <= xlim[1]]
    if pts:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], ls="none", marker="x", color=INK,
                ms=ms * 0.75, mew=mew * 1.1, zorder=4)
    ax.grid(True, color="#e2e2dc", linewidth=0.6, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)


def inset(ax, panel, data, rect, xlim, ylim, scale):
    """Zoomed, linear-axis view of the region where the curves separate."""
    ins = ax.inset_axes(rect)
    draw(ins, panel, data, scale=scale, xlim=xlim, ylim=ylim)
    ins.set_facecolor("#fbfbf9")
    for s in ("left", "bottom", "top", "right"):
        ins.spines[s].set_visible(True)
        ins.spines[s].set_color("#9a9a94")
    ins.tick_params(labelsize=8 * scale + 1, colors="#55554f")
    ins.set_title(f"zoom, linear M {xlim[0]}–{xlim[1]}", fontsize=8 * scale + 1, color="#55554f",
                  pad=3)
    ax.indicate_inset_zoom(ins, edgecolor="#9a9a94", alpha=0.8)
    return ins


def label(ax, panel):
    if panel == "a":
        ax.set(xscale="log", ylim=(0, 1.03), xlabel="M (number of UEs)", ylabel="$P_S$",
               title="(a) Access success probability")
    elif panel == "b":
        ax.set(xscale="log", ylim=(0, 5.6), xlabel="M (number of UEs)",
               ylabel=r"$\overline{D_a}$ (ms)", title="(b) Average access delay")
    elif panel == "c":
        ax.set(xlim=(0, 12), ylim=(0, 1.03), xticks=U_MS, xlabel="access delay u·Δ (ms)",
               ylabel="G[u]", title=f"(c) CDF of access delay, M = {M_CDF}")
    else:
        ax.set(xticks=range(1, NPT + 1), xlim=(0.8, NPT + 0.2), ylim=(0, 1.03),
               xlabel="number of transmissions m", ylabel="F[m]",
               title=f"(d) CDF of number of transmissions, M = {M_CDF}")


def zooms(ax, panel, data, scale):
    if panel == "a":
        inset(ax, "a", data, [0.07, 0.10, 0.50, 0.52], (800, 2000), (0.25, 1.03), scale)
    elif panel == "b":
        inset(ax, "b", data, [0.07, 0.40, 0.50, 0.52], (1000, 2000), (2.2, 5.4), scale)


def legend_handles(scale=1.0):
    h = [Line2D([], [], color=st["color"], ls=st["ls"], lw=2 * scale, marker=st["marker"],
                mfc="white", mec=st["color"], ms=7 * scale, mew=1.5 * scale, label=f"pattern ({n})")
         for n, st in STYLE.items()]
    h += [Line2D([], [], color="#6b6b66", lw=2 * scale, label="line: analysis (eqs. 1–16)"),
          Line2D([], [], color="#6b6b66", ls="none", marker="o", mfc="white", ms=7 * scale,
                 mew=1.5 * scale, label="hollow marker: ns-3 simulation"),
          Line2D([], [], color=INK, ls="none", marker="x", ms=6 * scale, mew=1.6 * scale,
                 label="×: published Fig. 4 (read)")]
    return h


def figure(panels, data, figsize, scale, out, top):
    plt.rcParams.update({"font.size": 10 * scale, "axes.titlesize": 11.5 * scale,
                         "axes.labelsize": 10.5 * scale, "xtick.labelsize": 9.5 * scale,
                         "ytick.labelsize": 9.5 * scale})
    nrow, ncol = (2, 2) if len(panels) == 4 else (1, len(panels))
    fig, axes = plt.subplots(nrow, ncol, figsize=figsize)
    for ax, panel in zip(getattr(axes, "flat", [axes]), panels):
        draw(ax, panel, data, scale=scale)
        label(ax, panel)
        zooms(ax, panel, data, scale)
    fig.legend(handles=legend_handles(scale), loc="upper center", ncol=6 if len(panels) == 4 else 3,
               frameon=False,
               fontsize=9.5 * scale, handlelength=2.6, columnspacing=1.6)
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(out, dpi=170 if len(panels) == 4 else 120, facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    data = load()
    figure("abcd", data, (13, 10), 1.0, FIG / "fig4_reproduction.png", top=0.965)
    figure("ab", data, (16, 6.4), 1.45, FIG / "slide_fig4_ab.png", top=0.86)
    figure("cd", data, (16, 6.4), 1.45, FIG / "slide_fig4_cd.png", top=0.86)


if __name__ == "__main__":
    main()
