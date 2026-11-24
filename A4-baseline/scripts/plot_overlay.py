#!/usr/bin/env python3
"""Overlay the reproduction on the published Fig. 4, at the paper's own scale.

The page with Fig. 4 is taken from the paper PDF (a scanned page, 300 dpi). For each
panel the published axes were calibrated from their frame and grid lines (pixel
positions in CAL, fit error < 1 px). The reproduction is then drawn as a complete plot
of its own -- frame, ticks, tick labels, axis labels, legend -- on a transparent
canvas of the same pixel size as the paper crop, with its axes box on exactly the
paper's frame and the same axis limits. Stacked on the paper crop, the two frames and
all ticks coincide, which shows the scale is identical; the data can then be compared.

    filled markers  = ns-3 simulation (mean of 30 runs), same marker shapes as the paper
    pale wide line  = my analytical model, eqs. (1)-(16)

Outputs (results/baseline/figures/overlay/):
    paper_<p>.png          crop of the published panel (white background)
    layer_<p>.png          my plot, transparent background, same size and scale
    stacked_<p>.png        layer_<p> on paper_<p>, for checking
    stacked_fig4.png       the four stacked panels, 2 x 2

Usage: python scripts/plot_overlay.py [--pdf ref/lin_cheng_2023.pdf]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_rgba  # noqa: E402
from matplotlib.ticker import FormatStrFormatter  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_baseline import FIG, load  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUT = FIG / "overlay"
PAGE_INDEX = 7      # journal page 22253, which holds Fig. 4
DPI = 100           # output canvas: 1 px = 1 px of the 300-dpi page
K = 1.635           # paper figure: matplotlib defaults rendered at ~163.5 px/inch on the page

STYLE = {"ii": ("#1f77b4", "o"), "iii": ("#2ca02c", "^"), "iv": ("#d62728", "s")}

# Pixel calibration on the 2550x3300 page image.
#   crop : region exported (x0, y0, x1, y1)
#   frame: axes box (left, top, right, bottom), from the black frame lines
#   x    : ("log", px of 10^0, px per decade) | ("lin", px of v0, v0, px per unit)
#   y    : (px of value 0, px per unit), pixel y grows downward
CAL = {
    "a": dict(crop=(320, 195, 1275, 905), frame=(438.5, 231.5, 1249.5, 758.5),
              x=("log", 475.5, 223.33), y=(758.5, 527.0)),
    "b": dict(crop=(1265, 195, 2220, 905), frame=(1388.0, 231.5, 2198.5, 758.5),
              x=("log", 1425.0, 223.17), y=(736.5, 91.5)),
    "c": dict(crop=(320, 920, 1275, 1630), frame=(438.5, 958.5, 1249.5, 1485.5),
              x=("lin", 439.0, 0.0, 67.54), y=(1462.5, 480.0)),
    "d": dict(crop=(1265, 920, 2220, 1630), frame=(1381.5, 958.5, 2192.5, 1485.5),
              x=("lin", 1381.5, 1.0, 202.6), y=(1485.5, 526.5)),
}

LABELS = {  # as in the published figure
    "a": dict(xlabel="$M$", ylabel="$P_S$", yticks=[0, .2, .4, .6, .8, 1], fmt="%.1f"),
    "b": dict(xlabel="$M$", ylabel=r"$\overline{D_a}$ (ms)", yticks=[0, 1, 2, 3, 4, 5], fmt="%d"),
    "c": dict(xlabel=r"$u\cdot\Delta$    (unit: ms)", ylabel="$G\\;[u]$", title="$M$=1000",
              xticks=list(range(0, 13, 2)), yticks=[0, .2, .4, .6, .8, 1], fmt="%.1f"),
    "d": dict(xlabel="$m$", ylabel="$F\\;[m]$", title="$M$=1000", xticks=[1, 2, 3, 4, 5],
              yticks=[i / 10 for i in range(11)], fmt="%.1f"),
}
LEGEND = {  # my legend, placed where the published panel has no curves or legend
    "a": dict(loc="upper left", bbox_to_anchor=(0.015, 0.80)),
    "b": dict(loc="upper left", bbox_to_anchor=(0.015, 0.66)),
    "c": dict(loc="upper right", bbox_to_anchor=(0.995, 0.67)),
    "d": dict(loc="upper left", bbox_to_anchor=(0.005, 0.995)),
}


def px_to_data(panel: str, px: float, py: float) -> tuple[float, float]:
    c = CAL[panel]
    if c["x"][0] == "log":
        _, x0, dec = c["x"]
        x = 10 ** ((px - x0) / dec)
    else:
        _, x0, v0, per = c["x"]
        x = v0 + (px - x0) / per
    y0, per_y = c["y"]
    return x, (y0 - py) / per_y


def page_image(pdf: Path) -> Image.Image:
    cache = OUT / "paper_page.png"
    if cache.exists():
        return Image.open(cache).convert("RGB")
    from pypdf import PdfReader
    img = list(PdfReader(str(pdf)).pages[PAGE_INDEX].images)[0].image.convert("RGB")
    if img.size != (2550, 3300):
        raise SystemExit(f"unexpected page size {img.size}; calibration is for 2550x3300")
    img.save(cache)
    return img


def layer(panel: str, data) -> Path:
    c = CAL[panel]
    cx0, cy0, cx1, cy1 = c["crop"]
    fl, ft, fr, fb = c["frame"]
    w, h = cx1 - cx0, cy1 - cy0
    rc = {"font.size": 10 * K, "axes.linewidth": 0.8 * K,
          "xtick.major.size": 3.5 * K, "ytick.major.size": 3.5 * K,
          "xtick.minor.size": 2 * K, "ytick.minor.size": 2 * K,
          "xtick.major.width": 0.8 * K, "ytick.major.width": 0.8 * K,
          "xtick.minor.width": 0.6 * K, "ytick.minor.width": 0.6 * K,
          "xtick.major.pad": 3.5 * K, "ytick.major.pad": 3.5 * K,
          "axes.labelpad": 4 * K, "axes.titlepad": 6 * K, "mathtext.fontset": "dejavusans"}
    with plt.rc_context(rc):
        fig = plt.figure(figsize=(w / DPI, h / DPI), dpi=DPI)
        ax = fig.add_axes(((fl - cx0) / w, (cy1 - fb) / h, (fr - fl) / w, (fb - ft) / h))
        ax.patch.set_alpha(0)
        if c["x"][0] == "log":
            ax.set_xscale("log")
        x_lo, y_lo = px_to_data(panel, fl, fb)
        x_hi, y_hi = px_to_data(panel, fr, ft)
        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(y_lo, y_hi)
        lab = LABELS[panel]
        ax.set_yticks(lab["yticks"])
        ax.yaxis.set_major_formatter(FormatStrFormatter(lab["fmt"]))
        if "xticks" in lab:
            ax.set_xticks(lab["xticks"])
        ax.set_xlabel(lab["xlabel"])
        ax.set_ylabel(lab["ylabel"])
        if "title" in lab:
            ax.set_title(lab["title"])

        for name, (color, marker) in STYLE.items():
            x, y = data["anal"][name][panel]
            ax.plot(x, y, color=color, lw=6 * K, alpha=0.28, solid_capstyle="round",
                    label=f"({name}) my anal.")
        for name, (color, marker) in STYLE.items():
            if panel in data["sim"][name]:
                sx, sy = data["sim"][name][panel]
                ax.plot(sx, sy, ls="none", marker=marker, ms=7 * K, mew=0.9 * K,
                        mfc=to_rgba(color, 0.55), mec=color, label=f"({name}) my ns-3")
        h_, l_ = ax.get_legend_handles_labels()
        order = [3, 4, 5, 0, 1, 2]
        ax.legend([h_[i] for i in order], [l_[i] for i in order], ncol=2, fontsize=7.2 * K,
                  framealpha=0.85, handlelength=1.8, columnspacing=1.0, borderpad=0.4,
                  **LEGEND[panel])
        out = OUT / f"layer_{panel}.png"
        fig.savefig(out, dpi=DPI, transparent=True)
        plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, default=PROJECT_DIR / "ref" / "lin_cheng_2023.pdf")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("overlay_fig4*.png"):
        old.unlink()
    page = page_image(a.pdf)
    data = load()
    stacked = {}
    for p in "abcd":
        paper = page.crop(CAL[p]["crop"])
        paper.save(OUT / f"paper_{p}.png")
        lay = Image.open(layer(p, data)).convert("RGBA")
        assert lay.size == paper.size, (lay.size, paper.size)
        stacked[p] = Image.alpha_composite(paper.convert("RGBA"), lay).convert("RGB")
        stacked[p].save(OUT / f"stacked_{p}.png")
        print(f"panel {p}: paper_{p}.png + layer_{p}.png -> stacked_{p}.png, {paper.size}")
    w, h = stacked["a"].size
    grid = Image.new("RGB", (2 * w, 2 * h), "white")
    for i, p in enumerate("abcd"):
        grid.paste(stacked[p], ((i % 2) * w, (i // 2) * h))
    grid.save(OUT / "stacked_fig4.png")
    print("wrote", OUT / "stacked_fig4.png")


if __name__ == "__main__":
    main()
