"""
Diagram generators for the 1st-order Error-Feedback NS-SAR ADC model
implemented in ns_sar_ef_8bit_core.py. Two views, both parameter-driven:

  draw_diagram()          -- signal-flow block diagram (the algorithm)
  draw_circuit_diagram()  -- circuit-level realization (the schematic intent)

The circuit view needs component values the simulation does not carry: the
model only knows the abstract loop gain `k_ef`. derive_circuit() recovers the
physical parts from it using the passive-EF relation
    K_EF = G * A_CS,   A_CS = Cres / (CDAC + Cres)
so `Cres` follows from `k_ef`, `cdac` and a chosen dynamic-amp gain `g_damp`.
`g_damp` is a *drawing* input only -- it never affects the simulation, since
only the product K_EF enters the loop math. It just decides how the same K_EF
is split between amplifier gain and charge-sharing ratio.

The block diagram is NOT a schematic -- it is a signal-flow view of the
algorithm in EFNSSAR.step():

    u[n]     = vin_noisy + K_EF * err1          (Sigma1: summing junction)
    code,err = quantize(u)                      (N-bit SAR quantizer)
    err[n]   = u - vdac                         (Sigma2: residue subtractor)
    err1    <- err                               (z^-1 delay register)

Layout rules (keep the drawing readable when editing):
  - Every block/junction exposes named ports via _port(); wires must start
    and end exactly on a port so an arrowhead never runs through a symbol.
  - Wires are Manhattan-routed (orthogonal segments only) via _wire(), and
    the grid below is chosen so that no two wires cross.
  - A signal that fans out (u[n] feeds both the quantizer and Sigma2) gets
    an explicit junction dot via _dot(); a corner is never a fan-out.

Workflow (keeps the diagram in sync with the algorithm):
  - Parameter changes: NSSARParams fields (n_bits, osr, fs, k_ef, cdac, ...)
    are read live from the dataclass instance passed in, so the annotated
    values on the diagram always match whatever main() just simulated --
    no separate editing needed.
  - Architecture changes: BOTH layouts hard-code a single feedback tap
    (1st order, matching NTF(z) = 1 - K_EF*z^-1) and neither auto-infers
    topology. If the loop filter in ns_sar_ef_8bit_core.py gains more
    delay/gain taps, add matching (z^-1 -> gain) block pairs along the
    FEEDBACK_Y row of draw_diagram(), and a second (Cres -> D-Amp) stage
    along the FB_Y row of draw_circuit_diagram().

Both are called at the end of ns_sar_ef_8bit_core.main(), so running
`python3 ns_sar_ef_8bit_core.py` regenerates the performance plots and both
diagrams together. Can also be run standalone: `python3
generate_architecture_diagram.py`.
"""

import math
from dataclasses import dataclass
from pathlib import Path
import numpy as np
# NOTE: deliberately no matplotlib.use("Agg") here -- this module only ever
# savefig()s (which works on any backend), and forcing Agg at import time would
# also force it on importers like ns_sar_ef_8bit_core.py, silently breaking
# their interactive plt.show() window.
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch, Polygon

# --- palette: the project slide deck's navy/crimson theme -------------------
# All values come from slide_theme.py so the diagrams, the performance grid and
# scripts/adc_survey_plot.py read as one document. See that module for the
# dataviz validator result.
from slide_theme import (
    INK, ACCENT, SURFACE, MUTED, FAINT, S_TERTIARY,
    FILL_BLUE, EDGE_BLUE, FILL_RED, EDGE_RED, FILL_NEUT, EDGE_NEUT,
    apply_rc, deck_title,
)

WIRE = INK                                # signal wires + all ink
NOISE = S_TERTIARY                        # stochastic (noise) injections
BLK_FC, BLK_EC = FILL_BLUE, EDGE_BLUE     # ordinary signal-path blocks
QNT_FC, QNT_EC = FILL_RED, EDGE_RED       # the quantizer / comparator
GRP_EC = FAINT                            # dashed grouping outline

# --- type / stroke sizing ---------------------------------------------------
# These diagrams are meant to be dropped into a slide at reduced size, so type
# and stroke weights are deliberately large *relative to the drawing geometry*
# (that ratio, not the absolute point size, is what survives being scaled down).
#
# CONVENTION: every `fontsize=` value written in this module is an UNSCALED
# point size. Scaling happens exactly once, at the point of use: primitives
# (_box, _switch_h, _amp, _comparator) scale their `fontsize` argument
# internally, and every bare ax.text() call wraps its size in _fs().
#
# Raising TEXT_SCALE further will overflow boxes -- the block widths and grid
# spacings in both layouts below are hand-tuned for 1.6. Widen the boxes too.
TEXT_SCALE = 1.6
LINE_SCALE = 1.35


def _fs(pt: float) -> float:
    """Unscaled points -> slide-legible points."""
    return pt * TEXT_SCALE


def _lw(w: float) -> float:
    """Unscaled line width -> slide-legible line width."""
    return w * LINE_SCALE


def _box(ax, cx, cy, w, h, label, fc=BLK_FC, ec=BLK_EC, fontsize=10):
    """Rounded block centred on (cx, cy). Ports: L/R/T/B on the edge midpoints."""
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0,rounding_size=0.10",
        facecolor=fc, edgecolor=ec, linewidth=_lw(1.7), zorder=3))
    ax.text(cx, cy, label, ha="center", va="center", fontsize=_fs(fontsize),
            zorder=4, linespacing=1.45)
    return dict(kind="box", c=(cx, cy), w=w, h=h)


def _sum(ax, cx, cy, r=0.34):
    """Summing junction: circle with an internal cross. Ports: L/R/T/B."""
    ax.add_patch(Circle((cx, cy), r, facecolor="white", edgecolor=WIRE,
                         linewidth=_lw(1.7), zorder=3))
    k = r * 0.52
    ax.plot([cx - k, cx + k], [cy, cy], color=WIRE, lw=_lw(1.3), zorder=4)
    ax.plot([cx, cx], [cy - k, cy + k], color=WIRE, lw=_lw(1.3), zorder=4)
    return dict(kind="sum", c=(cx, cy), w=2 * r, h=2 * r)


def _port(node, side):
    """Point on the edge of `node` for the given side ('L','R','T','B')."""
    (cx, cy), w, h = node["c"], node["w"], node["h"]
    return {"L": (cx - w / 2, cy), "R": (cx + w / 2, cy),
            "T": (cx, cy + h / 2), "B": (cx, cy - h / 2)}[side]


def _dot(ax, x, y, color=WIRE, r=0.095):
    """Junction dot marking an explicit fan-out."""
    ax.add_patch(Circle((x, y), r, facecolor=color, edgecolor=color, zorder=5))


def _wire(ax, pts, color=WIRE, lw=1.7, arrow=True, ls="-", head=0.30):
    """Manhattan-routed polyline with a single arrowhead at the final point."""
    lw = _lw(lw)
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw,
            linestyle=ls, solid_capstyle="round", solid_joinstyle="miter", zorder=2)
    if not arrow:
        return
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    dx, dy = x1 - x0, y1 - y0
    dist = math.hypot(dx, dy)
    if dist < 1e-9:
        return
    ux, uy = dx / dist, dy / dist
    ax.add_patch(FancyArrowPatch(
        (x1 - ux * head, y1 - uy * head), (x1, y1), arrowstyle="-|>",
        mutation_scale=22, color=color, linewidth=lw, zorder=2))


def _hz(value, unit="Hz") -> str:
    """Auto-scale a frequency so 1 kS/s designs don't read as '0.00 kHz'."""
    for div, prefix in ((1e6, "M"), (1e3, "k"), (1.0, "")):
        if abs(value) >= div:
            scaled = value / div
            digits = 0 if scaled >= 100 else (1 if scaled >= 10 else 2)
            return f"{scaled:.{digits}f} {prefix}{unit}"
    return f"{value:.2f} {unit}"


# ---------------------------------------------------------------------------
# Circuit-level primitives (capacitors, switches, amps, ground)
# ---------------------------------------------------------------------------


def _cap_v(ax, x, y, gap=0.22, halfw=0.38):
    """Vertical capacitor (horizontal plates). Returns (top, bottom) terminals."""
    for sign in (+1, -1):
        ax.plot([x - halfw, x + halfw], [y + sign * gap / 2] * 2,
                color=WIRE, lw=_lw(2.4), solid_capstyle="butt", zorder=3)
    return (x, y + gap / 2), (x, y - gap / 2)


def _cap_h(ax, x, y, gap=0.22, halfh=0.38):
    """Horizontal capacitor (vertical plates). Returns (left, right) terminals."""
    for sign in (-1, +1):
        ax.plot([x + sign * gap / 2] * 2, [y - halfh, y + halfh],
                color=WIRE, lw=_lw(2.4), solid_capstyle="butt", zorder=3)
    return (x - gap / 2, y), (x + gap / 2, y)


def _switch_h(ax, x, y, label=None, w=0.62):
    """Open horizontal switch. Returns (left, right) terminals."""
    xl, xr = x - w / 2, x + w / 2
    ax.plot([xl, xr], [y, y], marker="o", ms=6.0, ls="none", color=WIRE, zorder=4)
    ax.plot([xl, xr - 0.06], [y, y + 0.30], color=WIRE, lw=_lw(1.9), zorder=4)
    if label:
        ax.text(x, y + 0.44, label, fontsize=_fs(11), ha="center", va="bottom")
    return (xl, y), (xr, y)


def _amp(ax, x, y, label, w=1.60, h=1.30, direction="left", fontsize=9):
    """Triangular amplifier. Returns (input, output) terminals.

    The label sits a sixth of the width in from the BASE, not at the centroid:
    at TEXT_SCALE=1.6 a centred label runs out through the apex.
    """
    if direction == "left":
        verts = [(x + w / 2, y + h / 2), (x + w / 2, y - h / 2), (x - w / 2, y)]
        term_in, term_out, tx = (x + w / 2, y), (x - w / 2, y), x + w / 6
    else:
        verts = [(x - w / 2, y + h / 2), (x - w / 2, y - h / 2), (x + w / 2, y)]
        term_in, term_out, tx = (x - w / 2, y), (x + w / 2, y), x - w / 6
    ax.add_patch(Polygon(verts, closed=True, facecolor=BLK_FC, edgecolor=BLK_EC,
                         lw=_lw(1.7), zorder=3))
    ax.text(tx, y, label, ha="center", va="center", fontsize=_fs(fontsize), zorder=4)
    return term_in, term_out


def _comparator(ax, x, y, w=1.70, h=2.00):
    """Comparator triangle pointing right. Returns (plus_in, minus_in, out)."""
    xl, xr = x - w / 2, x + w / 2
    ax.add_patch(Polygon([(xl, y + h / 2), (xl, y - h / 2), (xr, y)], closed=True,
                         facecolor=QNT_FC, edgecolor=QNT_EC, lw=_lw(1.8), zorder=3))
    plus, minus = (xl, y + 0.35), (xl, y - 0.35)
    ax.text(xl + 0.30, y + 0.35, "+", fontsize=_fs(12), ha="center", va="center", zorder=4)
    ax.text(xl + 0.30, y - 0.35, "−", fontsize=_fs(13), ha="center", va="center", zorder=4)
    return plus, minus, (xr, y)


def _gnd(ax, x, y, size=0.40):
    """Ground symbol hanging below (x, y)."""
    ax.plot([x, x], [y, y - size * 0.42], color=WIRE, lw=_lw(1.7), zorder=3)
    for i, frac in enumerate((1.0, 0.60, 0.26)):
        yy = y - size * 0.42 - i * size * 0.26
        ax.plot([x - size * frac * 0.5, x + size * frac * 0.5], [yy, yy],
                color=WIRE, lw=_lw(1.7), zorder=3)


# ---------------------------------------------------------------------------
# Map the abstract loop gain K_EF onto physical components
# ---------------------------------------------------------------------------


@dataclass
class CircuitRealization:
    """Physical SC realization of the model's abstract `k_ef`.

    The passive error-feedback path (Li et al., JSSC 2018, Fig. 10) builds the
    loop gain from a dynamic-amplifier gain G and a charge-sharing attenuation
    A_CS, so K_EF = G * A_CS with A_CS = Cres/(CDAC + Cres). Inverting that for
    Cres is what turns `k_ef` into a capacitor value the schematic can use.
    """
    n_bits: int
    cdac: float      # F, total CDAC
    cu: float        # F, unit capacitor
    cres: float      # F, residue-transfer capacitor
    a_cs: float      # charge-sharing attenuation
    g_damp: float    # dynamic-amplifier voltage gain
    k_ef: float      # = g_damp * a_cs
    a_cs_formula: str  # how A_CS relates to the caps, for the annotation box


def derive_circuit(params, g_damp: float = None) -> CircuitRealization:
    """Collect the circuit-level component values behind the model's `k_ef`.

    Prefers the model's OWN values whenever it exposes them -- the 2nd-order
    NSSARParams already carries `a_cs`, `g_damp` and `cres1`, and re-deriving
    those here would silently contradict the simulation. In particular the
    2nd-order loading rule is A_CS = Cres1/(CDAC + 2*Cres1) (two FIR caps on
    the node), so the single-tap inversion below would give the wrong Cres.

    Only when the model carries no circuit parameters at all do we fall back to
    inverting the single-tap relation K_EF = G * A_CS, A_CS = Cres/(CDAC+Cres).

    NOTE: `g_damp` does NOT affect the simulation -- only the product
    K_EF = G * A_CS enters the loop math, and `params.k_ef` already fixes that.
    G only decides how the same K_EF is split between amplifier gain and
    charge-sharing ratio, i.e. how big Cres has to be. Pass it explicitly only
    to explore that split; leave it None to report what the model actually uses.
    """
    a_cs = getattr(params, "a_cs", None)
    g = g_damp if g_damp is not None else getattr(params, "g_damp", None)

    if a_cs is None or g_damp is not None:
        # No model-side A_CS, or the caller is explicitly overriding G.
        g = g if g is not None else 30.0
        a_cs = params.k_ef / g
    if g is None:
        g = params.k_ef / a_cs

    if not 0.0 < a_cs < 1.0:
        raise ValueError(
            f"K_EF={params.k_ef} with G={g} gives A_CS={a_cs:.3f}, which is "
            "not physically realizable by charge sharing (needs 0 < A_CS < 1). "
            f"Raise g_damp above {params.k_ef}.")

    cres = getattr(params, "cres1", None)
    if cres is None or g_damp is not None:
        cres = params.cdac * a_cs / (1.0 - a_cs)

    # The loading rule differs by loop order: the paper's 2nd-order FIR puts
    # TWO Cres caps on the node, the single-tap fallback only one. Print
    # whichever actually produced `a_cs`, or the box will contradict itself.
    model_supplied = getattr(params, "cres1", None) is not None and g_damp is None
    return CircuitRealization(
        n_bits=params.n_bits,
        cdac=params.cdac,
        cu=params.cdac / (2 ** params.n_bits),
        cres=cres,
        a_cs=a_cs,
        g_damp=g,
        k_ef=params.k_ef,
        a_cs_formula=("= Cres/(CDAC+2*Cres)" if model_supplied
                      else "= Cres/(CDAC+Cres)"),
    )


def _farad(value: float) -> str:
    """Auto-scale a capacitance to pF / fF / aF."""
    for div, unit in ((1e-12, "pF"), (1e-15, "fF"), (1e-18, "aF")):
        if abs(value) >= div:
            return f"{value / div:.2f} {unit}"
    return f"{value:.3e} F"


def _v(v: float) -> str:
    """Voltage with sensible units. Local copy of ns_sar_ef_8bit_core.fmt_v --
    duplicated deliberately: that module imports THIS one, so importing back
    would be circular."""
    a = abs(v)
    if a >= 1.0:
        return f"{v:.4g} V"
    if a >= 1e-3:
        return f"{v * 1e3:.4g} mV"
    return f"{v * 1e6:.4g} uV"


def _format_params(p) -> str:
    rows = [
        ("N (SAR bits)", f"{p.n_bits}"),
        ("OSR", f"{p.osr}"),
        ("Fs", _hz(p.fs, "S/s")),
        ("Bandwidth", _hz(p.bandwidth)),
        ("K_EF", f"{p.k_ef:.4f}"),
        ("CDAC", f"{p.cdac*1e12:.2f} pF"),
        ("LSB", _v(p.lsb)),
        ("Full scale", _v(p.vfs)),
        ("kT/C noise", _v(p.sigma_sample) + "rms"),
        ("Comp. noise", _v(p.comparator_noise_rms) + "rms"),
    ]
    return "\n".join(f"{k:<13}= {v}" for k, v in rows)


def draw_diagram(params, out_path: Path):
    """Signal-flow block diagram of the 2nd-order EF NS-SAR (paper Fig. 4).

    Structure, right to left along the feedback path:
        residue -> D-Amp G -> z^-1 (Cres1) -> 0.5 z^-1 (Cres2||Cdelay)
    The two FIR tap outputs each pass through the charge-sharing gain A_CS
    and are summed with OPPOSITE signs, giving the loop filter
        H(z) = K_EF*(z^-1 - 0.5*z^-2),  K_EF = G*A_CS
    and hence NTF(z) = 1 - H(z) -- paper eq. (1).
    """
    apply_rc(plt)
    fig, ax = plt.subplots(figsize=(18, 9.3))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 9.3)
    ax.set_aspect("equal")
    ax.axis("off")

    a_cs = params.a_cs
    g_damp = getattr(params, "g_damp", params.k_ef / a_cs)

    # --- grid (chosen so that no two wires cross) --------------------------
    MAIN_Y = 6.30     # forward signal path
    EFSUM_Y = 4.70    # where the two A_CS branches merge
    RESID_Y = 4.40    # residue subtractor row
    ACS_Y = 3.05      # A_CS charge-sharing gain row
    FIR_Y = 1.40      # passive SC FIR delay row
    S1_X = 4.40       # main summing node column
    Q_X = 8.10        # quantizer / residue / D-Amp column
    TAP_X = 6.10      # u[n] fan-out toward the residue subtractor
    T1_X = 4.40       # e[n-1] branch (directly under the EF sum)
    T2_X = 1.05       # 0.5*e[n-2] branch
    NOISE_Y = 7.70
    INFO_X = 13.10    # annotation column, clear of the Dout label

    # --- blocks -----------------------------------------------------------
    gin = _box(ax, 2.30, MAIN_Y, 1.95, 0.95, f"1−2$A_{{CS}}$\n={1-2*a_cs:.3f}",
               fontsize=11)
    s1 = _sum(ax, S1_X, MAIN_Y)
    quant = _box(ax, Q_X, MAIN_Y, 3.20, 1.85,
                 f"{params.n_bits}-bit SAR\nQuantizer\n(comparator + CDAC)",
                 fc=QNT_FC, ec=QNT_EC, fontsize=11)
    s2 = _sum(ax, Q_X, RESID_Y)
    damp = _box(ax, Q_X, ACS_Y, 2.40, 1.00, f"D-Amp\nG = {g_damp:.0f}", fontsize=11)
    zd1 = _box(ax, 5.55, FIR_Y, 1.80, 1.00, "$z^{-1}$\n$C_{res1}$", fontsize=11)
    zd2 = _box(ax, 2.70, FIR_Y, 2.30, 1.00, "0.5 $z^{-1}$\n$C_{res2}\\|C_{delay}$",
               fontsize=11)
    acs1 = _box(ax, T1_X, ACS_Y, 1.35, 0.90, "$A_{CS}$", fontsize=11)
    acs2 = _box(ax, T2_X, ACS_Y, 1.35, 0.90, "$A_{CS}$", fontsize=11)
    sef = _sum(ax, S1_X, EFSUM_Y)

    # --- dashed grouping around the passive SC FIR ------------------------
    ax.add_patch(FancyBboxPatch(
        (0.30, 0.75), 6.45, 1.30, boxstyle="round,pad=0,rounding_size=0.12",
        facecolor="none", edgecolor=GRP_EC, linewidth=_lw(1.1),
        linestyle=(0, (5, 4)), zorder=1))
    # Caption sits BELOW the dashed group; putting it inside overlaps Cres1.
    ax.text(6.75, 0.62, "passive SC FIR  (no OTA, no integrator)", fontsize=_fs(9),
            style="italic", color=MUTED, ha="right", va="top")

    # --- forward path: Vin -> gain -> Sigma1 -> quantizer -> Dout ----------
    _wire(ax, [(0.35, MAIN_Y), _port(gin, "L")])
    # Discrete-time input: the whole block diagram lives in the sampled domain,
    # so the input is the sequence V_in[n], not a continuous-time waveform.
    ax.text(0.35, MAIN_Y + 0.34, "$V_{in}[n]$", fontsize=_fs(12), ha="left")
    _wire(ax, [_port(gin, "R"), _port(s1, "L")])
    _wire(ax, [_port(s1, "R"), _port(quant, "L")])
    _dot(ax, TAP_X, MAIN_Y)
    ax.text(5.30, MAIN_Y + 0.32, "u[n]", fontsize=_fs(10), ha="center", style="italic")

    _wire(ax, [_port(quant, "R"), (11.10, MAIN_Y)])
    ax.text(11.30, MAIN_Y, f"$D_{{out}}$\n[{params.n_bits-1}:0]",
            fontsize=_fs(11), ha="left", va="center", linespacing=1.4)

    # --- noise injections (dashed = stochastic, not a signal wire) --------
    # Text is nudged left of its arrow so it does not butt against the wider
    # comparator-noise block on the same baseline.
    _wire(ax, [(S1_X, NOISE_Y), _port(s1, "T")], color=NOISE, ls=(0, (4, 3)), lw=1.4)
    ax.text(S1_X - 0.80, NOISE_Y + 0.18, "kT/C sampling noise\n$\\sigma$ = %.1f µVrms"
            % (params.sigma_sample * 1e6),
            fontsize=_fs(9.5), ha="center", va="bottom", color=NOISE, linespacing=1.4)

    _wire(ax, [(Q_X, NOISE_Y), _port(quant, "T")], color=NOISE, ls=(0, (4, 3)), lw=1.4)
    ax.text(Q_X, NOISE_Y + 0.18,
            "comparator / D-Amp noise\n$\\sigma$ = %.1f µVrms  →  %.1f µVrms input-ref.\n"
            "(×%.3f from 1−2$A_{CS}$)"
            % (params.comparator_noise_rms * 1e6,
               params.comparator_noise_rms * 1e6 / (1 - 2 * a_cs), 1 / (1 - 2 * a_cs)),
            fontsize=_fs(9), ha="center", va="bottom", color=NOISE, linespacing=1.4)

    # --- residue extraction: e[n] = u[n] - Vdac ---------------------------
    _wire(ax, [(TAP_X, MAIN_Y), (TAP_X, RESID_Y), _port(s2, "L")])
    _wire(ax, [_port(quant, "B"), _port(s2, "T")])
    # LEFT of the wire and va-centred: the right side is taken by the Sigma2 '−'
    # sign (Q_X+0.32, RESID_Y+0.56), and the default 'baseline' va would push the
    # glyphs up into the quantizer box, whose bottom edge is at 5.375.
    ax.text(Q_X - 0.26, 5.15, "$V_{dac}$", fontsize=_fs(10), ha="right", va="center")

    # --- feedback: residue -> D-Amp -> FIR cascade ------------------------
    _wire(ax, [_port(s2, "B"), _port(damp, "T")])
    ax.text(Q_X + 0.26, 3.85, "e[n]", fontsize=_fs(10), ha="left", va="center",
            style="italic")
    _wire(ax, [_port(damp, "B"), (Q_X, FIR_Y), _port(zd1, "R")])
    _wire(ax, [_port(zd1, "L"), _port(zd2, "R")])
    _dot(ax, T1_X, FIR_Y)

    # --- FIR taps up through A_CS into the EF summing node ----------------
    _wire(ax, [(T1_X, FIR_Y), _port(acs1, "B")])
    _wire(ax, [_port(acs1, "T"), _port(sef, "B")])
    # Kept below the EF-sum '+' sign at (S1_X+0.32, EFSUM_Y-0.56).
    ax.text(T1_X + 0.24, 3.73, "G·e[n−1]", fontsize=_fs(9.5), ha="left", style="italic")

    _wire(ax, [_port(zd2, "L"), (T2_X, FIR_Y), _port(acs2, "B")])
    _wire(ax, [_port(acs2, "T"), (T2_X, EFSUM_Y), _port(sef, "L")])
    ax.text(T2_X + 0.24, 3.95, "0.5·G·e[n−2]", fontsize=_fs(9.5), ha="left",
            style="italic")

    # --- EF sum -> main summing node --------------------------------------
    # Right-aligned to the LEFT of the column: at TEXT_SCALE=1.6 this label is
    # ~2.7 units wide and would run into the quantizer if placed on the right.
    _wire(ax, [_port(sef, "T"), _port(s1, "B")])
    ax.text(S1_X - 0.60, 5.50, "$K_{EF}$(e[n−1] − 0.5 e[n−2])",
            fontsize=_fs(9.5), ha="right", va="center")

    # --- summing-junction signs -------------------------------------------
    ax.text(S1_X - 0.56, MAIN_Y + 0.28, "+", fontsize=_fs(13), ha="center", va="center")
    ax.text(S1_X + 0.32, MAIN_Y - 0.56, "+", fontsize=_fs(13), ha="center", va="center")
    ax.text(Q_X - 0.56, RESID_Y + 0.28, "+", fontsize=_fs(13), ha="center", va="center")
    ax.text(Q_X + 0.32, RESID_Y + 0.56, "−", fontsize=_fs(14), ha="center", va="center")
    ax.text(S1_X + 0.32, EFSUM_Y - 0.56, "+", fontsize=_fs(13), ha="center", va="center")
    ax.text(S1_X - 0.56, EFSUM_Y + 0.30, "−", fontsize=_fs(14), ha="center", va="center")

    # --- annotations -------------------------------------------------------
    ax.text(INFO_X, 9.05, _format_params(params), fontsize=_fs(9), ha="left",
            va="top", family="monospace", linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.55", facecolor=FILL_NEUT,
                      edgecolor=EDGE_NEUT))

    z = np.roots([1.0, -params.k_ef, 0.5 * params.k_ef])
    ax.text(INFO_X, 5.45,
            "STF(z) = 1\n"
            "NTF(z) = 1 − $K_{EF}(z^{-1}$ − 0.5$z^{-2})$   [eq. 1]\n"
            f"        = 1 − {params.k_ef:.3f}$z^{{-1}}$ + {0.5*params.k_ef:.3f}$z^{{-2}}$\n"
            f"$K_{{EF}}$ = G·$A_{{CS}}$ = {g_damp:.0f}×{a_cs:.4f} = {params.k_ef:.3f}\n"
            f"zeros at {z[0].real:.3f} ± {abs(z[0].imag):.3f}j,  |z| = {abs(z[0]):.3f}\n"
            "2nd-order noise shaping, optimized zeros",
            fontsize=_fs(9), ha="left", va="top", linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.55", facecolor=FILL_RED,
                      edgecolor=EDGE_RED))

    fig.tight_layout(rect=[0, 0, 1, 0.90])
    deck_title(fig, "2nd-Order Error-Feedback NS-SAR ADC",
               subtitle="Signal-flow block diagram — architecture of Li et al., "
                        "JSSC 2018 (Fig. 4);  auto-generated from NSSARParams",
               size=_fs(15))
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return out_path


def draw_circuit_diagram(params, out_path: Path, g_damp: float = None):
    """Circuit-level (single-ended) realization of the EF NS-SAR loop.

    ⚠️ TOPOLOGY LAG: this view still draws ONE feedback tap (φr → Cres → G → φf),
    i.e. the 1st-order path. The model in ns_sar_ef_8bit_core.py is now the
    paper's 2nd-order two-tap FIR (Cres1 → Cres2‖Cdelay). Component *values* and
    labels below are read from the model and are correct, but the drawn topology
    is one tap short -- add the second (Cres → charge-share) stage along FB_Y to
    bring it level with draw_diagram().

    Same layout discipline as draw_diagram(): ports, Manhattan wires, no
    crossings. The feedback path runs ABOVE the Vx rail specifically so the SAR
    control bus can return to the CDAC below it without any wire crossing.
    """
    cr = derive_circuit(params, g_damp)

    apply_rc(plt)
    fig, ax = plt.subplots(figsize=(18, 9.6))
    ax.set_xlim(0, 18)
    ax.set_ylim(0.4, 10.0)
    ax.set_aspect("equal")
    ax.axis("off")

    # --- grid -------------------------------------------------------------
    VX_Y = 7.20        # CDAC top plate / comparator input rail
    FB_Y = 9.00        # error-feedback row (above the rail)
    CAP_Y = 6.30       # CDAC capacitor row
    SW_Y = 5.10        # bottom-plate switch bank
    SAR_Y = 4.40       # SAR logic row
    RAIL_L, RAIL_R = 2.40, 11.70
    TAP_X = 9.30       # feedback tap off the rail
    CMP_X = 12.55      # comparator column: set so its left edge lands on RAIL_R

    # --- input sampling ----------------------------------------------------
    ax.text(0.30, VX_Y + 0.34, "$V_{in}$", fontsize=_fs(12), ha="left")
    _wire(ax, [(0.30, VX_Y), (1.29, VX_Y)], arrow=False)
    _switch_h(ax, 1.60, VX_Y, "$\\varphi_s$")
    _wire(ax, [(1.91, VX_Y), (RAIL_L, VX_Y)], arrow=False)

    # --- Vx rail -----------------------------------------------------------
    _wire(ax, [(RAIL_L, VX_Y), (RAIL_R, VX_Y)], arrow=False, lw=2.1)
    ax.text(6.10, VX_Y + 0.22, "$V_x$   (CDAC top plate = comparator input)",
            fontsize=_fs(9.5), ha="center", va="bottom", color=MUTED)

    # --- CDAC binary-weighted array ---------------------------------------
    n = params.n_bits
    cdac_cols = [
        (3.90, f"${2**(n-1)}\\,C_u$", f"$b_{{{n-1}}}$"),
        (5.10, f"${2**(n-2)}\\,C_u$", f"$b_{{{n-2}}}$"),
        (7.50, "$1\\,C_u$", "$b_0$"),
        (8.70, "$1\\,C_u$", "dummy"),
    ]
    for cx, weight, bit in cdac_cols:
        top, bot = _cap_v(ax, cx, CAP_Y)
        _wire(ax, [(cx, VX_Y), top], arrow=False)
        _wire(ax, [bot, (cx, SW_Y + 0.40)], arrow=False)
        ax.text(cx + 0.14, CAP_Y + 0.36, weight, fontsize=_fs(8.5), ha="left",
                va="center")
        ax.text(cx + 0.14, CAP_Y - 0.42, bit, fontsize=_fs(8.5), ha="left",
                va="center")
    ax.text(6.30, CAP_Y, "· · ·", fontsize=_fs(15), ha="center", va="center")

    _box(ax, 6.15, SW_Y, 5.90, 0.85,
         "bottom-plate switches   →   $V_{refp}$ / $V_{refn}$", fontsize=9.5)

    # reference rails under the switch bank
    _wire(ax, [(4.60, SW_Y - 0.43), (4.60, 4.05)], arrow=False)
    ax.text(4.60, 3.95, "$V_{refp}$", fontsize=_fs(9.5), ha="center", va="top")
    _wire(ax, [(7.60, SW_Y - 0.43), (7.60, 4.15)], arrow=False)
    _gnd(ax, 7.60, 4.15)
    ax.text(7.95, 4.05, "$V_{refn}$", fontsize=_fs(9.5), ha="left", va="center")

    # --- comparator --------------------------------------------------------
    plus, minus, cmp_out = _comparator(ax, CMP_X, 6.85)
    _wire(ax, [(10.50, minus[1]), minus], arrow=False)
    ax.text(10.35, minus[1], "$V_{cm}$", fontsize=_fs(10), ha="right", va="center")
    ax.text(CMP_X, 5.70, "comparator", fontsize=_fs(9.5), ha="center", va="top")

    # Noise arrow stops on the triangle's upper edge, not at a fixed offset.
    _wire(ax, [(CMP_X, 8.55), (CMP_X, 7.35)], color=NOISE, ls=(0, (4, 3)), lw=1.4)
    ax.text(CMP_X, 8.70, "comparator noise\n$\\sigma$ = %.1f µVrms"
            % (params.comparator_noise_rms * 1e6),
            fontsize=_fs(9), ha="center", va="bottom", color=NOISE, linespacing=1.4)

    # --- SAR logic ---------------------------------------------------------
    sar = _box(ax, CMP_X, SAR_Y, 3.10, 1.30,
               f"SAR logic\n({n}-bit register + FSM)", fontsize=9.5)
    _wire(ax, [cmp_out, (cmp_out[0], SAR_Y + 0.65)])

    _wire(ax, [_port(sar, "R"), (15.60, SAR_Y)])
    ax.text(15.78, SAR_Y, f"$D_{{out}}$[{n-1}:0]", fontsize=_fs(11), ha="left",
            va="center")

    # control bus back to the bottom-plate switches (dashed = digital control)
    _wire(ax, [_port(sar, "L"), (9.60, SAR_Y), (9.60, SW_Y), (9.10, SW_Y)],
          color=FAINT, ls=(0, (5, 3)), lw=1.4)
    ax.text(10.30, SAR_Y - 0.22, f"$b_{{{n-1}}}\\dots b_0$", fontsize=_fs(9),
            ha="center", va="top", color=FAINT)

    # --- kT/C sampling noise (annotated below the rail, left of the array) --
    _wire(ax, [(1.90, 5.75), (1.90, VX_Y - 0.12)], color=NOISE, ls=(0, (4, 3)), lw=1.4)
    ax.text(1.90, 5.58, "kT/C sampling noise\n$\\sigma$ = %.1f µVrms"
            % (params.sigma_sample * 1e6),
            fontsize=_fs(9), ha="center", va="top", color=NOISE, linespacing=1.4)

    # --- error-feedback path (above the rail, right -> left) ---------------
    ax.add_patch(FancyBboxPatch(
        (2.10, 8.30), 7.55, 1.50, boxstyle="round,pad=0,rounding_size=0.12",
        facecolor="none", edgecolor=GRP_EC, linewidth=_lw(1.1),
        linestyle=(0, (5, 4)), zorder=1))
    # Caption hangs off the group's RIGHT end: at TEXT_SCALE=1.6 a right-aligned
    # label at the left end would run off the canvas.
    ax.text(9.65, 8.02, "error-feedback path", fontsize=_fs(9), style="italic",
            color=MUTED, ha="right", va="top")

    _dot(ax, TAP_X, VX_Y)
    _wire(ax, [(TAP_X, VX_Y), (TAP_X, FB_Y), (8.91, FB_Y)], arrow=False)
    _switch_h(ax, 8.60, FB_Y, "$\\varphi_r$")
    cres_l, cres_r = _cap_h(ax, 7.50, FB_Y)
    _wire(ax, [(8.29, FB_Y), cres_r], arrow=False)
    ax.text(7.50, FB_Y + 0.50, "$C_{res}$", fontsize=_fs(10), ha="center", va="bottom")

    amp_in, amp_out = _amp(ax, 6.05, FB_Y, f"G = {cr.g_damp:.0f}", direction="left")
    _wire(ax, [cres_l, amp_in], arrow=False)
    _wire(ax, [amp_out, (4.81, FB_Y)], arrow=False)
    _switch_h(ax, 4.50, FB_Y, "$\\varphi_f$")
    _wire(ax, [(4.19, FB_Y), (RAIL_L, FB_Y), (RAIL_L, VX_Y)])

    # --- phase legend ------------------------------------------------------
    phases = (
        "$\\varphi_s$  sample     $V_{in}$ onto the CDAC top plate (kT/C sampled here)\n"
        f"$\\varphi_c$  convert    {n} comparator trials; SAR drives $b_{{{n-1}}}\\dots b_0$\n"
        "$\\varphi_r$  residue    e[n] left on $V_x$ is stored onto $C_{res}$\n"
        "$\\varphi_f$  feedback   $G\\,$e[n−1] charge-shared back onto $V_x$"
    )
    ax.text(0.40, 3.20, phases, fontsize=_fs(9.5), ha="left", va="top",
            linespacing=1.75,
            bbox=dict(boxstyle="round,pad=0.55", facecolor=FILL_NEUT,
                      edgecolor=EDGE_NEUT))

    # --- derived component values -----------------------------------------
    values = "\n".join([
        f"{'CDAC total':<12}= {_farad(cr.cdac)}   ({2**n}·Cu)",
        f"{'Cu':<12}= {_farad(cr.cu)}",
        f"{'Cres':<12}= {_farad(cr.cres)}",
        f"{'A_CS':<12}= {cr.a_cs:.4f}   {cr.a_cs_formula}",
        f"{'G (D-Amp)':<12}= {cr.g_damp:.1f}",
        f"{'K_EF':<12}= {cr.k_ef:.4f}   = G x A_CS",
        f"{'LSB':<12}= {params.lsb*1e6:.2f} uV",
        f"{'Full scale':<12}= {params.vfs*1e3:.2f} mV",
    ])
    ax.text(10.60, 3.35, values, fontsize=_fs(9), ha="left", va="top",
            family="monospace", linespacing=1.55,
            bbox=dict(boxstyle="round,pad=0.55", facecolor=FILL_RED,
                      edgecolor=EDGE_RED))

    fig.tight_layout(rect=[0, 0, 1, 0.90])
    deck_title(fig, "Error-Feedback NS-SAR ADC — Circuit-Level Realization",
               subtitle="Single-ended switched-capacitor view;  component values "
                        "read from NSSARParams  (K_EF = G × A_CS)",
               size=_fs(15))
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    from ns_sar_ef_8bit_core import NSSARParams

    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    p = NSSARParams()
    print(f"Saved: {draw_diagram(p, out_dir / 'architecture_diagram.png')}")
    print(f"Saved: {draw_circuit_diagram(p, out_dir / 'circuit_diagram.png')}")
