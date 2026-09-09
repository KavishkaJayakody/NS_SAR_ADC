"""
Slide-deck visual theme for the NS-SAR ADC Python figures.

Single source of truth for the palette shared by:
  - generate_architecture_diagram.py  (block + circuit-level diagrams)
  - ns_sar_ef_8bit_core.py            (performance panel grid)

The palette is the project slide deck's navy/crimson scheme -- the same values
`scripts/adc_survey_plot.py` uses, so every figure in the deck reads as one
system. If the deck changes, update BOTH files.

Validated with the dataviz skill's `validate_palette.js` on a light surface.
The performance grid overlays up to four curves in one panel, so the 4-hue set
is validated with `--pairs all` (not just adjacent) -- all six checks pass:

    node scripts/validate_palette.js "#2B36C4,#D6183B,#9B51E0,#0E8A6B" \
        --mode light --pairs all
    # worst all-pairs CVD dE 8.1 (deutan) / 13.7 (tritan)
    # worst normal-vision dE 20.2, all four >= 3:1 contrast

> The 8.1 deutan figure sits just above the dE 8 floor, so every series also
> carries a distinct marker + line style (secondary encoding). Keep that when
> editing -- colour alone is NOT sufficient separation at this margin.
>
> A 5th hue was tried and rejected: burnt orange #C2570A collides with the
> crimson (dE 3.6 deutan, 10.7 normal-vision -- a hard fail). If a 5th series
> is ever needed, fold it into an existing hue with a new line style, use small
> multiples, or drop a curve -- do NOT invent another colour.
"""

from matplotlib.lines import Line2D

# --- core ink / surface ----------------------------------------------------
INK = "#1B2A5E"        # slide navy — titles, axes, all body text
ACCENT = "#D6183B"     # slide crimson — title rule, emphasis
SURFACE = "#FFFFFF"
GRID = "#E4E7F0"       # recessive gridlines
MUTED = "#6B7699"      # secondary ink: captions, node labels
FAINT = "#A9B2CC"      # dashed groupings, control buses

# --- categorical series: fixed order, never cycled -------------------------
# Slot 0 = primary ("with NS"), 1 = comparison ("without"), 2 = noise/offset,
# 3 = the retuned/optimised variant.
SERIES = ["#2B36C4", "#D6183B", "#9B51E0", "#0E8A6B"]
S_PRIMARY, S_SECONDARY, S_TERTIARY, S_QUATERNARY = SERIES

# Reference lines (targets, ceilings, band edges, ideal asymptotes) are NOT
# data series -- they must stay recessive so they never compete with the
# curves. Draw them in these, dashed, never in a categorical hue.
REF = "#8A93B2"        # reference/target lines
REF_STRONG = "#5C6689"  # a reference line that carries the headline limit

# --- tinted fills for diagram blocks --------------------------------------
FILL_BLUE, EDGE_BLUE = "#EEF1FB", "#2B36C4"   # ordinary signal-path blocks
FILL_RED, EDGE_RED = "#FDECEF", "#D6183B"     # the quantizer / comparator
FILL_NEUT, EDGE_NEUT = "#F4F6FA", "#A9B2CC"   # annotation boxes

# --- type ------------------------------------------------------------------
FONT_STACK = ["Lato", "Source Sans Pro", "Open Sans", "Helvetica Neue",
              "Arial", "DejaVu Sans"]


def apply_rc(plt, base: float = 11.0):
    """Set global rcParams to the deck theme. Call once before building a figure."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": FONT_STACK,
        "font.size": base,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": INK,
        "axes.titlecolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.grid": False,
        "grid.color": GRID,
        "grid.linewidth": 0.9,
        "axes.linewidth": 1.1,
        "legend.frameon": False,
        "lines.linewidth": 2.0,       # dataviz: 2px lines
        "lines.markersize": 5.5,
        "axes.prop_cycle": plt.cycler(color=SERIES),
    })


def style_axes(ax, grid: str = "both", title: str | None = None,
               titlesize: float = 12.5):
    """Recessive axes: drop the top/right spines, mute the grid, navy ink."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK)
        ax.spines[side].set_linewidth(1.1)
    ax.tick_params(colors=INK, labelsize=9.5, width=1.0, length=4)
    if grid:
        ax.grid(True, which=grid, color=GRID, linewidth=0.9, alpha=1.0)
        ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=titlesize, color=INK,
                     fontweight="bold", pad=10)
    return ax


def deck_title(fig, title: str, subtitle: str | None = None,
               x0: float = 0.045, x1: float = 0.965, y: float = 0.965,
               size: float = 19.0, rule: bool = True):
    """Slide-style heading: navy bold title over a crimson rule.

    Mirrors the deck's section headings so a figure dropped onto a slide reads
    as part of the same document.
    """
    fig.suptitle(title, fontsize=size, color=INK, fontweight="bold",
                 x=x0, y=y, ha="left")
    if rule:
        fig.add_artist(Line2D([x0, x1], [y - 0.028, y - 0.028],
                              color=ACCENT, linewidth=3.0,
                              transform=fig.transFigure))
    if subtitle:
        fig.text(x0, y - 0.055, subtitle, fontsize=11.5, color=MUTED,
                 ha="left", va="top")
