"""
NS_SAR_ADC CSV Benchmark Script
Reads ADC output codes from the adc_csv_logger VerilogA module and evaluates
SNR, SNDR, ENOB, THD, SFDR, DNL, and INL.

CSV format (written by adc_csv_logger on every EOC rising edge):
    Time,DecimalCode
    1.234e-07,42
    ...

N_BITS is auto-detected from the code stream using two complementary
estimates:
  • N_bits_from_max  : ceil(log2(max_code + 1))
    → correct for LSB-aligned outputs  (e.g. 3-bit in din[2:0], max = 7)
  • N_bits_from_step : round(log2(2^BUS_WIDTH / GCD(code_step)))
    → correct for MSB-aligned outputs  (e.g. 3-bit in din[9:7], step = 128)
  N_BITS = min(both estimates), clamped to [1, BUS_WIDTH].

Requirements:
    pip install numpy matplotlib
"""

import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from functools import reduce
from math import gcd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CSV_FILE        = None    # absolute path string; None → newest CSV under simulation/
N_BITS_OVERRIDE = None    # e.g. 8  — overrides auto-detection
VREF_OVERRIDE   = 1.8    # e.g. 1.8 — overrides default 1.8 V
DROP_SAMPLES    = 5       # startup conversions to discard

BUS_WIDTH = 10            # hardcoded port width in adc_csv_logger
VGND      = 0.0

_REPO_ROOT = Path(__file__).parent.parent

# Module-level state — written by main(), read by analysis helpers
N_BITS = 8
VREF   = 1
T_SIM  = None

# ---------------------------------------------------------------------------
# CSV auto-discovery
# ---------------------------------------------------------------------------
def _find_csv() -> Path:
    if CSV_FILE is not None:
        p = Path(CSV_FILE)
        if not p.exists():
            sys.exit(f"ERROR: CSV_FILE not found: {p}")
        return p
    candidates = sorted(
        _REPO_ROOT.glob("simulation/**/*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        sys.exit(
            "ERROR: no .csv file found under simulation/.  "
            "Set CSV_FILE at the top of this script, or run a simulation first."
        )
    return candidates[0]


# ---------------------------------------------------------------------------
# CSV reader
# ---------------------------------------------------------------------------
def load_csv(csv_path: Path):
    """
    Load (time, raw_codes) from the two-column adc_csv_logger CSV.
    Returns (time: float64 array, codes: int64 array).
    """
    print(f"Loading: {csv_path}")
    try:
        with open(csv_path, newline="") as fh:
            reader = csv.reader(fh)
            raw_rows = list(reader)
    except Exception as exc:
        sys.exit(f"ERROR: could not read CSV: {exc}")

    if not raw_rows:
        sys.exit("ERROR: CSV file is empty or contains only a header row.")

    # Normalise header: lowercase + strip whitespace
    header = [c.strip().lower() for c in raw_rows[0]]
    time_col = "time"
    code_col = "decimalcode" if "decimalcode" in header else "code"

    if time_col not in header or code_col not in header:
        sys.exit(f"ERROR: expected columns 'Time' and 'DecimalCode', got: {header}")

    t_idx = header.index(time_col)
    c_idx = header.index(code_col)

    # Parse rows; skip repeated header lines (data_logger re-writes header on re-init)
    time_list, code_list = [], []
    n_dropped = 0
    for row in raw_rows[1:]:
        if len(row) <= max(t_idx, c_idx):
            n_dropped += 1
            continue
        try:
            t = float(row[t_idx])
            c = int(float(row[c_idx]))
            time_list.append(t)
            code_list.append(c)
        except ValueError:
            n_dropped += 1

    if n_dropped:
        print(f"  Dropped {n_dropped} non-numeric row(s) (repeated headers in CSV)")

    if not time_list:
        sys.exit("ERROR: no valid numeric rows found in CSV.")

    time  = np.array(time_list,  dtype=np.float64)
    codes = np.array(code_list,  dtype=np.int64)
    print(f"  Rows       : {len(time)}")
    print(f"  Time span  : {time[0]*1e9:.2f} – {time[-1]*1e9:.2f} ns")
    print(f"  Code range : {codes.min()} – {codes.max()}")
    return time, codes


# ---------------------------------------------------------------------------
# N_BITS auto-detection
# ---------------------------------------------------------------------------
def detect_n_bits(codes, bus_width=BUS_WIDTH):
    """
    Estimate ADC resolution from the integer code stream.

    Returns (n_bits, step_size, normalised_codes).
    normalised_codes are in [0, 2^n_bits − 1] regardless of original alignment.
    """
    max_code = int(np.max(codes))
    if max_code <= 0:
        return 1, 1, codes.astype(int)

    # Estimate 1 — from maximum observed code
    n_from_max = max(1, int(np.ceil(np.log2(max_code + 1))))
    n_from_max = min(n_from_max, bus_width)

    # Estimate 2 — from GCD of consecutive sorted-unique-code differences
    # GCD = step size = 2^(bus_width − N_BITS) for MSB-aligned buses
    unique_sorted = np.sort(np.unique(codes))
    diffs = np.diff(unique_sorted).astype(int)
    diffs = diffs[diffs > 0]
    if len(diffs) > 0:
        step = int(reduce(gcd, diffs.tolist()))
    else:
        step = 1
    total_codes   = (1 << bus_width) // max(step, 1)
    n_from_step   = int(round(np.log2(max(total_codes, 1))))
    n_from_step   = max(1, min(bus_width, n_from_step))

    n_bits = min(n_from_max, n_from_step)

    # Normalise: divide by step_size so codes span [0, 2^n_bits − 1]
    norm = np.clip((codes // step).astype(int), 0, (1 << n_bits) - 1)

    print(f"\nN_BITS detection:")
    print(f"  max code = {max_code}  →  N_bits_from_max  = {n_from_max}")
    print(f"  GCD step = {step}     →  N_bits_from_step = {n_from_step}")
    print(f"  N_BITS = min({n_from_max}, {n_from_step}) = {n_bits}")
    print(f"  Distinct codes observed : {len(unique_sorted)}  "
          f"(expected 2^{n_bits} = {1 << n_bits})")

    return n_bits, step, norm


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def _fmt_freq(f_hz):
    if f_hz >= 1e6:
        return f"{f_hz/1e6:.3f} MHz"
    elif f_hz >= 1e3:
        return f"{f_hz/1e3:.3f} kHz"
    return f"{f_hz:.3f} Hz"

def _freq_axis_scale(f_max_hz):
    if f_max_hz >= 1e6:
        return 1e6, "MHz"
    elif f_max_hz >= 1e3:
        return 1e3, "kHz"
    return 1.0, "Hz"


# ---------------------------------------------------------------------------
# Clipping histogram — IEEE 1241 sine amplitude / DC offset estimation
# ---------------------------------------------------------------------------
def estimate_amplitude_offset(codes, hist_count):
    n_codes = 2 ** N_BITS
    lsb = (VREF - VGND) / n_codes
    M = len(codes)
    H_min = float(hist_count[0])
    H_max = float(hist_count[n_codes - 1])
    V_1    = VGND + lsb
    V_last = VGND + (n_codes - 1) * lsb
    C1 = np.cos(np.pi * H_min / M)
    C2 = np.cos(np.pi * H_max / M)
    denom = C1 + C2
    if abs(denom) < 1e-12:
        return np.nan, np.nan
    A   = (V_last - V_1) / denom
    Vos = V_1 + A * C1
    return float(A), float(Vos)


# ---------------------------------------------------------------------------
# DNL / INL — histogram method with arcsine correction
# ---------------------------------------------------------------------------
def compute_inl_dnl(codes, amp, vos):
    n_codes = 2 ** N_BITS
    M = len(codes)
    lsb = (VREF - VGND) / n_codes
    count = np.bincount(codes, minlength=n_codes).astype(float)

    expected = np.full(n_codes, np.nan)
    for k in range(1, n_codes - 1):
        v_lo_k = VGND + k * lsb
        v_hi_k = VGND + (k + 1) * lsb
        lo = np.clip((v_lo_k - vos) / amp, -1.0, 1.0)
        hi = np.clip((v_hi_k - vos) / amp, -1.0, 1.0)
        expected[k] = M / np.pi * (np.arcsin(hi) - np.arcsin(lo))

    with np.errstate(divide="ignore", invalid="ignore"):
        dnl = np.where(expected > 0.5, (count - expected) / expected, np.nan)

    inl = np.nancumsum(np.nan_to_num(dnl, nan=0.0))
    return dnl, inl, count


# ---------------------------------------------------------------------------
# FFT-based spectrum analysis
# ---------------------------------------------------------------------------
def analyse_spectrum(t_samples, norm_codes):
    """
    Compute SNR, SNDR, ENOB, THD, SFDR, DNL, INL from the normalised code
    stream and its sample timestamps.
    """
    lsb = (VREF - VGND) / (2 ** N_BITS)
    v_samples = norm_codes * lsb

    f_s = 1.0 / float(np.mean(np.diff(t_samples))) if len(t_samples) > 1 else 1.0

    # Truncate to largest power-of-2 for clean FFT
    n_pow2 = 1 << (len(t_samples).bit_length() - 1)
    t_samples  = t_samples[:n_pow2]
    v_samples  = v_samples[:n_pow2]
    norm_codes = norm_codes[:n_pow2]
    N = n_pow2

    spectrum = np.fft.rfft(v_samples - np.mean(v_samples))
    power    = np.abs(spectrum) ** 2
    freqs    = np.fft.rfftfreq(N, d=1.0 / f_s)

    dc_bin  = 0
    sig_bin = int(np.argmax(power[1:])) + 1
    f_in    = freqs[sig_bin]

    claimed = {dc_bin, sig_bin}
    signal_power = power[sig_bin]

    harmonic_power = 0.0
    harmonics = []
    for h in range(2, 6):
        hf = h * f_in
        if hf >= f_s / 2:
            break
        hb = max(1, np.argmin(np.abs(freqs[1:] - hf)) + 1)
        if hb in claimed:
            continue
        hp = power[hb]
        harmonic_power += hp
        claimed.add(hb)
        harmonics.append((h, hf, hb, hp))

    noise_power = sum(power[b] for b in range(len(power)) if b not in claimed)

    snr  = 10 * np.log10(signal_power / noise_power)      if noise_power  > 0 else np.inf
    sndr = 10 * np.log10(signal_power / (noise_power + harmonic_power)) \
           if (noise_power + harmonic_power) > 0 else np.inf
    enob = (sndr - 1.76) / 6.02

    # SFDR
    noise_bins = [b for b in range(1, len(power)) if b not in claimed]
    sfdr = (10 * np.log10(signal_power / max(power[b] for b in noise_bins))
            if noise_bins else np.inf)

    hist_count = np.bincount(norm_codes, minlength=2 ** N_BITS).astype(float)
    amp, vos = estimate_amplitude_offset(norm_codes, hist_count)
    dnl, inl, hist_count = compute_inl_dnl(norm_codes, amp, vos)

    return dict(
        snr=snr, sndr=sndr, enob=enob, sfdr=sfdr,
        snr_ideal=6.02 * N_BITS + 1.76,
        f_s=f_s, f_in_detected=f_in, freqs=freqs, power=power,
        signal_bin=sig_bin, harmonics=harmonics,
        codes=norm_codes, v_quant=v_samples, n_samples=N,
        dnl=dnl, inl=inl, hist_count=hist_count,
        amp=amp, vos=vos,
    )


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
def print_summary(res, csv_path):
    sep = "=" * 52
    print(f"\n{sep}")
    print("  NS_SAR_ADC CSV BENCHMARK RESULTS")
    print(sep)
    print(f"  Source file     : {csv_path.name}")
    print(f"  Resolution      : {N_BITS} bits  (auto-detected)")
    print(f"  Vref            : {VREF:.4f} V")
    print(f"  Sampling rate   : {_fmt_freq(res['f_s'])}")
    print(f"  Sim duration    : {T_SIM*1e3:.3f} ms")
    print(f"  Input frequency : {_fmt_freq(res['f_in_detected'])} (FFT peak)")
    print(f"  FFT samples     : {res['n_samples']}")
    print("-" * 52)
    print(f"  SNR             : {res['snr']:>8.2f} dB  (ideal: {res['snr_ideal']:.2f} dB)")
    print(f"  SNDR            : {res['sndr']:>8.2f} dB")
    print(f"  ENOB            : {res['enob']:>8.2f} bits  (ideal: {N_BITS})")
    print(f"  SFDR            : {res['sfdr']:>8.2f} dB")
    dnl_peak = float(np.nanmax(np.abs(res['dnl'])))
    inl_peak = float(np.nanmax(np.abs(res['inl'])))
    print(f"  DNL (peak)      : {dnl_peak:>8.3f} LSB")
    print(f"  INL (peak)      : {inl_peak:>8.3f} LSB")
    amp_str = f"{res['amp']:.4f} V" if not np.isnan(res['amp']) else "N/A (no clipping)"
    vos_str = f"{res['vos']:.4f} V" if not np.isnan(res['vos']) else "N/A"
    print(f"  Amplitude (A)   : {amp_str}")
    print(f"  DC offset (Vos) : {vos_str}")
    print("-" * 52)
    delta  = N_BITS - res['enob']
    status = "PASS" if delta <= 0.5 else "FAIL"
    print(f"  STATUS          : {status}  (ENOB loss = {delta:.2f} bits)")
    print(f"{sep}\n")


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
def plot_results(t_samples, res, csv_path):
    from matplotlib.gridspec import GridSpec

    n_codes = 2 ** N_BITS
    lsb     = (VREF - VGND) / n_codes
    code_x  = np.arange(n_codes)

    dnl       = res["dnl"]
    inl       = res["inl"]
    dnl_valid = not np.all(np.isnan(dnl))
    dnl_peak  = float(np.nanmax(np.abs(dnl))) if dnl_valid else 0.0
    inl_peak  = float(np.nanmax(np.abs(inl))) if dnl_valid else 0.0

    fig = plt.figure(figsize=(22, 12))
    fig.suptitle(
        f"NS_SAR_ADC ({N_BITS}-bit)  —  CSV Benchmark  [{csv_path.name}]",
        fontsize=13, fontweight="bold", y=0.98,
    )
    gs = GridSpec(2, 3, figure=fig, hspace=0.36, wspace=0.26,
                  left=0.05, right=0.98, top=0.93, bottom=0.07)

    ax_time = fig.add_subplot(gs[0, 0])
    ax_dnl  = fig.add_subplot(gs[0, 1])
    ax_inl  = fig.add_subplot(gs[0, 2])
    ax_spec = fig.add_subplot(gs[1, 0])
    ax_hist = fig.add_subplot(gs[1, 1])
    ax_tbl  = fig.add_subplot(gs[1, 2])

    # [0,0] Time domain — one full Fin cycle
    samples_per_cycle = int(round(res["f_s"] / res["f_in_detected"])) if res["f_in_detected"] > 0 else 200
    n_show = min(samples_per_cycle, len(t_samples), len(res["v_quant"]))
    v_show = res["v_quant"][:n_show]
    t_show = t_samples[:n_show] * 1e6
    ax_time.step(t_show, v_show, where="post", color="tomato", lw=1.0)
    ax_time.set_xlabel("Time (µs)")
    ax_time.set_ylabel("Voltage (V)")
    ax_time.set_title(f"DAC Output — 1 cycle @ {_fmt_freq(res['f_in_detected'])}")
    ax_time.grid(True, alpha=0.3)
    ax_time.text(
        0.98, 0.97,
        f"Fs = {_fmt_freq(res['f_s'])}\n"
        f"Vref = {VREF:.4f} V\n"
        f"T sim = {T_SIM*1e3:.3f} ms\n"
        f"N = {res['n_samples']} samples",
        transform=ax_time.transAxes, fontsize=8, color="dimgray",
        ha="right", va="top", linespacing=1.6,
    )

    # [0,1] DNL — diverging colormap: blue=negative, white=zero, red=positive
    dnl_num  = np.nan_to_num(dnl)
    dnl_norm = np.clip(dnl_num / max(dnl_peak, 0.5), -1.0, 1.0)
    cmap_dnl = plt.cm.RdBu_r
    bar_colors = [cmap_dnl(0.5 + 0.5 * v) for v in dnl_norm]
    ax_dnl.bar(code_x, dnl_num, color=bar_colors, edgecolor="none", width=1.0)
    ax_dnl.axhline(0,    color="black", lw=0.8)
    ylim_dnl = max(0.6, dnl_peak * 1.4)
    ax_dnl.axhline( 0.5, color="#CC0000", lw=1.0, ls="--")
    ax_dnl.axhline(-0.5, color="#CC0000", lw=1.0, ls="--")
    ax_dnl.text(code_x[-1] * 1.01, 0.5, "  ±0.5 LSB", fontsize=7,
                color="#CC0000", va="center", clip_on=False)
    ax_dnl.set_xlabel("Output Code")
    ax_dnl.set_ylabel("DNL (LSB)")
    ax_dnl.set_title("DNL" if dnl_valid else "DNL  (insufficient samples)")
    ax_dnl.xaxis.set_major_locator(plt.MaxNLocator(nbins=10, integer=True))
    ax_dnl.set_ylim(-ylim_dnl, ylim_dnl)
    ax_dnl.grid(True, alpha=0.3, axis="y")
    if dnl_valid:
        ax_dnl.text(0.02, 0.97, f"Peak = {dnl_peak:.3f} LSB",
                    transform=ax_dnl.transAxes, fontsize=8, color="dimgray",
                    ha="left", va="top")

    # [0,2] INL
    ylim_inl  = max(0.6, inl_peak * 1.4)
    inl_colors = ["#E57373" if v >= 0 else "#64B5F6" for v in inl]
    ax_inl.bar(code_x, inl, color=inl_colors, edgecolor="none", width=1.0)
    ax_inl.axhline(0,    color="black", lw=0.8)
    ax_inl.axhline( 0.5, color="#CC0000", lw=1.0, ls="--")
    ax_inl.axhline(-0.5, color="#CC0000", lw=1.0, ls="--")
    ax_inl.text(code_x[-1] * 1.01, 0.5, "  ±0.5 LSB", fontsize=7,
                color="#CC0000", va="center", clip_on=False)
    ax_inl.set_xlabel("Output Code")
    ax_inl.set_ylabel("INL (LSB)")
    ax_inl.set_title("INL" if dnl_valid else "INL  (insufficient samples)")
    ax_inl.xaxis.set_major_locator(plt.MaxNLocator(nbins=10, integer=True))
    ax_inl.set_ylim(-ylim_inl, ylim_inl)
    ax_inl.grid(True, alpha=0.3)
    if dnl_valid:
        ax_inl.text(0.02, 0.97, f"Peak = {inl_peak:.3f} LSB",
                    transform=ax_inl.transAxes, fontsize=8, color="dimgray",
                    ha="left", va="top")

    # [1,0] Power spectrum
    freqs  = res["freqs"]
    pwr_db = 10 * np.log10(res["power"] / res["power"].max() + 1e-20)
    f_div, f_unit = _freq_axis_scale(freqs[-1])
    ax_spec.plot(freqs / f_div, pwr_db, color="royalblue", lw=0.8)
    ax_spec.set_xlabel(f"Frequency ({f_unit})")
    ax_spec.set_ylabel("Power (dB, norm.)")
    ax_spec.set_title("Output Power Spectrum")
    ax_spec.set_ylim(-100, 5)
    ax_spec.grid(True, alpha=0.3)
    ax_spec.text(0.98, 0.97,
                 f"Fin = {_fmt_freq(res['f_in_detected'])}\nSFDR = {res['sfdr']:.2f} dB",
                 transform=ax_spec.transAxes, fontsize=8, color="red",
                 ha="right", va="top")

    # [1,1] Code histogram
    ax_hist.bar(code_x, res["hist_count"], color="steelblue", edgecolor="none")
    ax_hist.set_xlabel("Output Code")
    ax_hist.set_ylabel("Count")
    ax_hist.set_title("Output Code Histogram")
    ax_hist.xaxis.set_major_locator(plt.MaxNLocator(nbins=10, integer=True))
    ax_hist.grid(True, alpha=0.3, axis="y")

    # [1, 2] Summary table
    ax_tbl.axis("off")
    amp_meas = f"{res['amp']:.4f} V"  if not np.isnan(res["amp"]) else "N/A"
    vos_meas = f"{res['vos']:.4f} V"  if not np.isnan(res["vos"]) else "N/A"
    delta  = N_BITS - res["enob"]
    status = "PASS" if delta <= 0.5 else "FAIL"
    rows = [
        ["SNR (dB)",         f"{res['snr']:.2f}",                     f"{res['snr_ideal']:.2f}"],
        ["SNDR (dB)",        f"{res['sndr']:.2f}",                    f"{res['snr_ideal']:.2f}"],
        ["ENOB (bits)",      f"{res['enob']:.2f}",                    f"{N_BITS:.2f}"],
        ["Amplitude (A)",    amp_meas,                                 "—"],
        ["DC offset (Vos)",  vos_meas,                                 "—"],
        ["Status",           status,                                   "PASS"],
    ]
    tbl = ax_tbl.table(
        cellText=rows, colLabels=["Metric", "Measured", "Ideal"],
        loc="upper center", cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9.5)
    tbl.scale(1.05, 1.72)
    for j in range(3):
        tbl[0, j].set_facecolor("#2E5FA3")
        tbl[0, j].set_text_props(color="white", fontweight="bold")
    status_color = "#4CAF50" if status == "PASS" else "#E53935"
    for j in range(3):
        tbl[len(rows), j].set_facecolor(status_color)
        tbl[len(rows), j].set_text_props(color="white", fontweight="bold")
    ax_tbl.text(0.5, 1.02, "Performance Summary", transform=ax_tbl.transAxes,
                fontsize=10, fontweight="bold", ha="center", va="bottom")

    # Separator + "Controls" header
    ax_tbl.plot([0.02, 0.98], [0.295, 0.295], transform=ax_tbl.transAxes,
                color="#BDBDBD", lw=0.9, clip_on=False)
    ax_tbl.text(0.5, 0.285, "Controls", transform=ax_tbl.transAxes,
                fontsize=7.5, ha="center", va="top",
                fontweight="bold", color="#455A64")

    # Two-column always-visible controls
    _ctrl_left = (
        "Click graph\n"
        "  → Expand to full view\n"
        "Click again  /  Esc\n"
        "  → Return to overview"
    )
    _ctrl_right = (
        "Scroll ↓ on graph  → X zoom in\n"
        "Scroll ↑ on graph  → X zoom out\n"
        "Scroll ↓ on Y lbl  → Y zoom in\n"
        "Scroll ↑ on Y lbl  → Y zoom out\n"
        "Zoom anchors at cursor position\n"
        "Zoom-out clamps to orig. range"
    )
    ax_tbl.text(0.03, 0.26, _ctrl_left, transform=ax_tbl.transAxes,
                fontsize=7.2, ha="left", va="top", family="monospace",
                color="#37474F", linespacing=1.45)
    ax_tbl.text(0.97, 0.26, _ctrl_right, transform=ax_tbl.transAxes,
                fontsize=7.2, ha="right", va="top", family="monospace",
                color="#37474F", linespacing=1.45)

    out = Path(__file__).parent / "csv_benchmark_results.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Plot saved: {out}")

    # ── Click-to-zoom interaction ───────────────────────────────────────────
    graph_axes = [ax_time, ax_dnl, ax_inl, ax_spec, ax_hist]
    saved_pos  = {ax: ax.get_position() for ax in graph_axes}
    saved_tbl  = ax_tbl.get_position()
    zoom       = {"active": False, "ax": None}

    def _restore():
        for ax in graph_axes:
            ax.set_position(saved_pos[ax])
            ax.set_visible(True)
        ax_tbl.set_position(saved_tbl)
        ax_tbl.set_visible(True)
        fig.suptitle(
            f"NS_SAR_ADC ({N_BITS}-bit)  —  CSV Benchmark  [{csv_path.name}]"
            "  |  click any graph to expand",
            fontsize=12, fontweight="bold", y=0.98,
        )
        zoom["active"] = False
        zoom["ax"]     = None
        fig.canvas.draw_idle()

    def _zoom_in(ax):
        for a in graph_axes:
            a.set_visible(a is ax)
        ax_tbl.set_visible(False)
        ax.set_position([0.08, 0.10, 0.86, 0.80])
        fig.suptitle(
            f"{ax.get_title()}  |  click again or press Esc to return",
            fontsize=12, fontweight="bold", y=0.98,
        )
        zoom["active"] = True
        zoom["ax"]     = ax
        fig.canvas.draw_idle()

    def _on_click(event):
        if event.inaxes is None or event.inaxes not in graph_axes:
            return
        if zoom["active"] and zoom["ax"] is event.inaxes:
            _restore()
        else:
            _zoom_in(event.inaxes)

    def _on_key(event):
        if event.key == "escape" and zoom["active"]:
            _restore()

    # Original limits — used to clamp zoom-out on both axes
    orig_xlims = {ax: ax.get_xlim() for ax in graph_axes}
    orig_ylims = {ax: ax.get_ylim() for ax in graph_axes}

    Y_MARGIN_PX = 72   # px left of axes spine that counts as "y-axis area"
    FACTOR      = 0.80 # 20 % per scroll tick

    def _on_scroll(event):
        # Determine target axes and whether to zoom x or y
        target_ax  = None
        zoom_axis  = None

        if event.inaxes in graph_axes:
            target_ax = event.inaxes
            zoom_axis = "x"
        else:
            # Cursor in the y-axis label area (left margin of any visible axes)
            for ax in graph_axes:
                if not ax.get_visible():
                    continue
                bb = ax.get_window_extent()
                if (bb.x0 - Y_MARGIN_PX <= event.x <= bb.x0 and
                        bb.y0 <= event.y <= bb.y1):
                    target_ax = ax
                    zoom_axis = "y"
                    break

        if target_ax is None:
            return

        # scroll up = zoom out, scroll down = zoom in
        scale = 1.0 / FACTOR if event.button == "up" else FACTOR

        if zoom_axis == "x":
            xdata = event.xdata
            if xdata is None:
                return
            xmin, xmax       = target_ax.get_xlim()
            orig_lo, orig_hi = orig_xlims[target_ax]
            new_span         = (xmax - xmin) * scale

            if new_span >= orig_hi - orig_lo:
                target_ax.set_xlim(orig_lo, orig_hi)
                fig.canvas.draw_idle()
                return

            rel    = (xdata - xmin) / (xmax - xmin)
            new_lo = xdata - rel * new_span
            new_hi = new_lo + new_span
            if new_lo < orig_lo:
                new_lo, new_hi = orig_lo, orig_lo + new_span
            if new_hi > orig_hi:
                new_hi, new_lo = orig_hi, orig_hi - new_span
            target_ax.set_xlim(new_lo, new_hi)

        else:  # y-axis zoom, anchored at cursor y position
            ymin, ymax       = target_ax.get_ylim()
            orig_lo, orig_hi = orig_ylims[target_ax]
            new_span         = (ymax - ymin) * scale

            if new_span >= orig_hi - orig_lo:
                target_ax.set_ylim(orig_lo, orig_hi)
                fig.canvas.draw_idle()
                return

            # Convert cursor display-pixel y → data coordinate
            bb    = target_ax.get_window_extent()
            y_rel = (event.y - bb.y0) / (bb.y1 - bb.y0)
            ydata = ymin + y_rel * (ymax - ymin)

            rel    = (ydata - ymin) / (ymax - ymin)
            new_lo = ydata - rel * new_span
            new_hi = new_lo + new_span
            if new_lo < orig_lo:
                new_lo, new_hi = orig_lo, orig_lo + new_span
            if new_hi > orig_hi:
                new_hi, new_lo = orig_hi, orig_hi - new_span
            target_ax.set_ylim(new_lo, new_hi)

        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", _on_click)
    fig.canvas.mpl_connect("key_press_event",    _on_key)
    fig.canvas.mpl_connect("scroll_event",       _on_scroll)
    fig.suptitle(
        f"NS_SAR_ADC ({N_BITS}-bit)  —  CSV Benchmark  [{csv_path.name}]"
        "  |  click any graph to expand",
        fontsize=12, fontweight="bold", y=0.98,
    )

    try:
        plt.show()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global N_BITS, VREF, T_SIM

    print("NS_SAR_ADC CSV Benchmark")
    print("-" * 45)

    csv_path = _find_csv()
    time, raw_codes = load_csv(csv_path)
    T_SIM = float(time[-1])

    # ── N_BITS detection ─────────────────────────────────────────────────
    if N_BITS_OVERRIDE is not None:
        N_BITS = N_BITS_OVERRIDE
        # Normalise using implied step size for the bus width
        step   = (1 << BUS_WIDTH) >> N_BITS
        norm   = np.clip((raw_codes // max(step, 1)).astype(int),
                         0, (1 << N_BITS) - 1)
        print(f"\nN_BITS = {N_BITS}  (manual override, step = {step})")
    else:
        N_BITS, step, norm = detect_n_bits(raw_codes)

    # ── VREF ─────────────────────────────────────────────────────────────
    VREF = VREF_OVERRIDE if VREF_OVERRIDE is not None else 1.8
    print(f"VREF   = {VREF} V  "
          f"({'manual override' if VREF_OVERRIDE is not None else 'default — set VREF_OVERRIDE to change'})")

    # ── Discard settling samples ──────────────────────────────────────────
    if len(time) <= DROP_SAMPLES:
        sys.exit(f"ERROR: only {len(time)} samples (need > {DROP_SAMPLES}).")
    time = time[DROP_SAMPLES:]
    norm = norm[DROP_SAMPLES:]

    f_s = 1.0 / float(np.mean(np.diff(time))) if len(time) > 1 else 1.0
    print(f"\nSamples after settling discard : {len(time)}")
    print(f"Sampling rate (Fs)             : {_fmt_freq(f_s)}")
    print(f"Simulation duration            : {T_SIM*1e3:.3f} ms")

    # ── Analysis & output ─────────────────────────────────────────────────
    res = analyse_spectrum(time, norm)
    print_summary(res, csv_path)
    plot_results(time, res, csv_path)


if __name__ == "__main__":
    main()
