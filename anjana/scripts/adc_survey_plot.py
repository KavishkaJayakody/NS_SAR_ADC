#!/usr/bin/env python3
"""ADC survey plots — ENOB vs sampling rate and ENOB vs energy per conversion.

Data source: Boris Murmann's ADC survey (ISSCC + VLSI, 1997-present), cloned to
``ADC/`` from https://github.com/bmurmann/ADC-survey.

Only SAR, delta-sigma and flash designs are plotted; every other architecture
(pipeline, folding, VCO, time-based, ...) is dropped.

Read with openpyxl directly rather than ``pandas.read_excel`` — the local pandas
build refuses the installed openpyxl version.

Run:  python3 scripts/adc_survey_plot.py
Out:  scripts/adc_survey_enob_vs_fs.png
      scripts/adc_survey_enob_vs_energy.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from matplotlib.lines import Line2D

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
XLSX = REPO / "ADC" / "xls" / "ADCsurvey_latest.xlsx"
OUT_FS = REPO / "scripts" / "adc_survey_enob_vs_fs.png"
OUT_ENERGY = REPO / "scripts" / "adc_survey_enob_vs_energy.png"
SHEETS = ("ISSCC", "VLSI")

# Palette taken from the project slide deck (navy / royal blue / crimson),
# checked with the dataviz validator: all six checks pass.
INK = "#1B2A5E"       # slide navy — titles, axes, labels
ACCENT = "#D6183B"    # slide crimson — title rule
GRID = "#E4E7F0"
SURFACE = "#FFFFFF"

FAMILIES = [
    ("SAR", "#2B36C4"),
    ("Delta-Sigma", "#D6183B"),
    ("Flash", "#9B51E0"),
]
COLORS = dict(FAMILIES)
LABELS = {"Delta-Sigma": "$\\Delta\\Sigma$"}

FS_BASE = 22          # base font size; everything scales off this
FIGSIZE = (11, 8)

# Region ellipses: covariance ellipse per family, drawn at N_STD sigma.
SHOW_ELLIPSES = True
N_STD = 2.0           # ~86% of a 2-D normal
ELLIPSE_FILL_ALPHA = 0.10
ELLIPSE_EDGE_ALPHA = 0.55


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def classify(arch: str) -> str | None:
    """Map the survey's ~90 architecture strings onto the 3 plotted families.

    Returns None for everything else, which the caller drops. The pipeline
    check comes before SAR so that hybrids like "Pipe, SAR" are excluded
    rather than counted as SAR.
    """
    a = (arch or "").lower()
    if "sd" in a or "incremental" in a:
        return "Delta-Sigma"
    if "pipe" in a:
        return None
    if "sar" in a:
        return "SAR"
    if "flash" in a:
        return "Flash"
    return None


def load_survey(path: Path) -> dict[str, np.ndarray]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    fam, enob, fsnyq, energy = [], [], [], []

    for sheet in SHEETS:
        rows = wb[sheet].iter_rows(values_only=True)
        head = list(next(rows))
        i_arch = head.index("ARCHITECTURE")
        i_sndr = head.index("SNDR_plot [dB]")
        i_fs = head.index("fsnyq [Hz]")
        i_e = head.index("P/fsnyq [pJ]")

        for row in rows:
            if row[0] is None:
                continue
            family = classify(str(row[i_arch]))
            if family is None:
                continue
            sndr, fs, e = row[i_sndr], row[i_fs], row[i_e]
            if not isinstance(sndr, (int, float)) or not isinstance(fs, (int, float)):
                continue
            if not isinstance(e, (int, float)) or fs <= 0 or e <= 0:
                continue
            fam.append(family)
            enob.append((sndr - 1.76) / 6.02)
            fsnyq.append(float(fs))
            energy.append(float(e))

    wb.close()
    return {
        "family": np.array(fam),
        "enob": np.array(enob),
        "fsnyq": np.array(fsnyq),
        "energy": np.array(energy),
    }


# --------------------------------------------------------------------------
# Plot
# --------------------------------------------------------------------------
def region_ellipse(ax, x, y, colour: str) -> None:
    """Shade the covariance ellipse of one family.

    Built in (log10 x, y) space and mapped back with 10**, because the x axis
    is logarithmic — a ``matplotlib.patches.Ellipse`` in data coordinates would
    come out skewed. Drawn as an explicit polygon for the same reason.
    """
    if len(x) < 3:
        return
    pts = np.column_stack([np.log10(x), y])
    mu = pts.mean(axis=0)
    vals, vecs = np.linalg.eigh(np.cov(pts.T))
    transform = vecs @ np.diag(np.sqrt(np.maximum(vals, 0.0)) * N_STD)

    t = np.linspace(0.0, 2.0 * np.pi, 240)
    ell = np.column_stack([np.cos(t), np.sin(t)]) @ transform.T + mu
    ex, ey = 10.0 ** ell[:, 0], ell[:, 1]

    ax.fill(ex, ey, color=colour, alpha=ELLIPSE_FILL_ALPHA, linewidth=0, zorder=1)
    ax.plot(ex, ey, color=colour, alpha=ELLIPSE_EDGE_ALPHA, linewidth=2.4, zorder=1)


def make_figure(x, y, family, xlabel: str, title: str, xlim, out_png: Path):
    fig, ax = plt.subplots(figsize=FIGSIZE, facecolor=SURFACE)

    ax.set_facecolor(SURFACE)
    ax.set_xscale("log")
    ax.grid(True, which="major", color=GRID, linewidth=1.1, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK)
        ax.spines[side].set_linewidth(1.6)
    ax.tick_params(colors=INK, labelsize=FS_BASE, width=1.6, length=6)
    ax.set_xlabel(xlabel, fontsize=FS_BASE + 3, color=INK, labelpad=12)
    ax.set_ylabel("ENOB [bits]", fontsize=FS_BASE + 3, color=INK, labelpad=12)

    # Smallest family last so it is not buried under the dense ones.
    order = sorted(FAMILIES, key=lambda f: -int(np.count_nonzero(family == f[0])))
    for name, colour in order:
        m = family == name
        if SHOW_ELLIPSES:
            region_ellipse(ax, x[m], y[m], colour)
        ax.scatter(x[m], y[m], s=40, c=colour, alpha=0.55, linewidths=0, zorder=2)

    ax.set_xlim(*xlim)
    ax.set_ylim(2, 22)
    ax.set_yticks([5, 10, 15, 20])

    handles = [
        Line2D([], [], marker="o", linestyle="none", markersize=14,
               markerfacecolor=c, markeredgecolor="none",
               label=LABELS.get(n, n))
        for n, c in FAMILIES
    ]
    leg = fig.legend(
        handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.905),
        ncol=len(handles), frameon=False, fontsize=FS_BASE + 2,
        handletextpad=0.4, columnspacing=2.4,
    )
    for text in leg.get_texts():
        text.set_color(INK)

    fig.suptitle(title, fontsize=FS_BASE + 10, color=INK, fontweight="bold",
                 x=0.07, y=0.975, ha="left", va="top")
    fig.add_artist(Line2D([0.07, 0.96], [0.925, 0.925], color=ACCENT,
                          linewidth=2.4, transform=fig.transFigure))

    fig.tight_layout(rect=(0.01, 0.01, 0.99, 0.875))
    fig.savefig(out_png, dpi=300, facecolor=SURFACE)
    return fig


def main() -> None:
    if not XLSX.exists():
        raise SystemExit(
            f"survey data not found at {XLSX}\n"
            "clone it first:  git clone https://github.com/bmurmann/ADC-survey.git ADC"
        )

    d = load_survey(XLSX)

    make_figure(
        d["fsnyq"], d["enob"], d["family"],
        xlabel="Nyquist sampling rate  $f_{snyq}$  [Hz]",
        title="Resolution vs Speed",
        xlim=(2e2, 2e11),
        out_png=OUT_FS,
    )
    make_figure(
        d["energy"], d["enob"], d["family"],
        xlabel="Energy per conversion  $P/f_{snyq}$  [pJ]",
        title="Resolution vs Energy",
        xlim=(1e-1, 3e7),
        out_png=OUT_ENERGY,
    )

    counts = {n: int(np.count_nonzero(d["family"] == n)) for n, _ in FAMILIES}
    print(f"{len(d['enob'])} designs plotted  {counts}")
    print(f"  -> {OUT_FS}")
    print(f"  -> {OUT_ENERGY}")
    plt.show()


if __name__ == "__main__":
    main()
