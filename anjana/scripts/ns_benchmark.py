"""
ns_benchmark.py — Noise-Shaping SAR ADC benchmark with sinc¹ vs sinc² decimation.

Reads raw N-bit SAR output codes from a data_logger CSV, applies both a
sinc¹ (moving average) and a sinc² (CIC order-2) decimation filter at the
configured OSR, then computes SNR/SNDR/ENOB/SFDR/THD/DNL/INL on each.

Why sinc² beats sinc¹ for a 1st-order NS-SAR:
  The analog integrator shapes quantisation noise as (1 - z⁻¹), concentrating
  it at high frequencies.  A sinc¹ (rectangular) filter suppresses noise by
  OSR (6 dB/oct), but for 1st-order shaping you need a sinc² (triangular /
  CIC-2) filter to get one extra order of roll-off and achieve the full
  ENOB ≈ N_RAW + 0.5·log2(OSR) + 0.5  bits.

Usage:
    python3 scripts/ns_benchmark.py

Requirements:
    pip install numpy pandas matplotlib
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from math import log2, ceil

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CSV_FILE       = None   # None → auto-select newest CSV under simulation/
OSR            = 4      # Oversampling ratio (must match sar_logic `osr` param)
N_BITS_RAW     = 3      # Raw SAR resolution (bits)
VREF           = 0.9    # Reference voltage (V)
DROP_SAMPLES   = 5      # Decimated samples to discard for settling
OUTPUT_PNG     = Path("scripts/ns_benchmark_results.png")

# ---------------------------------------------------------------------------
# CSV loading  (shared with csv_benchmark.py)
# ---------------------------------------------------------------------------

def _find_csv():
    dirs = [Path("simulation"), Path("simulations")]
    for d in dirs:
        if d.exists():
            csvs = sorted(d.rglob("*.csv"), key=lambda p: p.stat().st_mtime)
            if csvs:
                return csvs[-1]
    sys.exit("ERROR: no CSV files found under simulation/ or simulations/")


def load_csv(csv_path: Path):
    print(f"Loading : {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        sys.exit(f"ERROR: could not read CSV: {exc}")
    if df.empty:
        sys.exit("ERROR: CSV is empty.")

    df.columns = [c.strip().lower() for c in df.columns]
    time_col = "time"
    code_col = "decimalcode" if "decimalcode" in df.columns else "code"
    if time_col not in df.columns or code_col not in df.columns:
        sys.exit(f"ERROR: expected 'Time','DecimalCode', got: {list(df.columns)}")

    # Drop repeated header rows (data_logger re-writes header on re-init)
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
    df[code_col] = pd.to_numeric(df[code_col], errors="coerce")
    n_before = len(df)
    df = df.dropna().reset_index(drop=True)
    if len(df) < n_before:
        print(f"  Dropped  {n_before - len(df)} repeated-header row(s)")

    times = df[time_col].to_numpy(np.float64)
    codes = df[code_col].to_numpy(np.int64)
    print(f"  Samples  : {len(codes)}")
    print(f"  Code range: [{codes.min()}, {codes.max()}]")
    return times, codes


# ---------------------------------------------------------------------------
# Decimation filters
# ---------------------------------------------------------------------------

def sinc1_decimate(codes: np.ndarray, osr: int) -> np.ndarray:
    """
    sinc¹ — integer SUM over non-overlapping blocks of `osr` raw codes.

    Output range: [0, (2^N - 1) * osr]
    For N=3, OSR=4: [0, 28] → 29 discrete integer levels.

    Dividing (averaging) would collapse this back to [0, 7] and throw away
    all resolution gained by oversampling — so we keep the raw sum.
    """
    n_out = len(codes) // osr
    return codes[: n_out * osr].reshape(n_out, osr).sum(axis=1).astype(np.float64)


def sinc2_decimate(codes: np.ndarray, osr: int) -> np.ndarray:
    """
    sinc² — CIC order-2 decimation (triangular window), same output scale as sinc¹.

    Un-normalised kernel: [1, 2, ..., osr, ..., 2, 1]  (sum = osr²)
    Divide by osr (not osr²) to land on the same [0, (2^N-1)*osr] scale as sinc¹.

    Output range: [0, (2^N-1)*osr] in steps of 1/osr.
    For N=3, OSR=4: [0, 28] in steps of 0.25 → up to 113 distinguishable levels
    (vs 29 integer levels for sinc¹).  The finer grid is the payoff for the
    extra filter order — it represents the additional noise rejection.
    """
    ramp = np.arange(1, osr + 1, dtype=np.float64)
    kernel = np.concatenate([ramp, ramp[-2::-1]])   # [1,2,...,osr,...,2,1], sum=osr²

    # Convolve without normalising, then divide by osr only → range [0, (2^N-1)*osr]
    filtered = np.convolve(codes.astype(np.float64), kernel, mode="valid") / osr
    return filtered[::osr]


# ---------------------------------------------------------------------------
# ADC metrics (FFT-based)
# ---------------------------------------------------------------------------

LOBE_HALF = 3   # bins either side of fundamental / harmonic claimed as signal


def compute_metrics(dec_codes: np.ndarray, drop: int, label: str) -> dict:
    codes = dec_codes[drop:].astype(np.float64)

    # Truncate to largest power-of-2 for a clean, leakage-free FFT
    n_pow2 = 1 << (len(codes).bit_length() - 1)
    codes  = codes[:n_pow2]
    N      = n_pow2
    if N < 16:
        sys.exit(f"ERROR: too few decimated samples ({N}) after dropping {drop}.")

    # AC-coupled: remove DC
    codes_ac = codes - codes.mean()

    # No window — power-of-2 + coherent sampling gives clean bins already.
    # (Hann window shifts the fundamental power into neighbours and makes
    #  the lobe detection inconsistent with csv_benchmark.py.)
    spectrum = np.fft.rfft(codes_ac)
    pwr      = np.abs(spectrum) ** 2
    freqs    = np.fft.rfftfreq(N)       # normalised 0..0.5

    # Fundamental: highest power bin starting from bin 1 (skip only DC bin 0)
    sig_bin  = int(np.argmax(pwr[1:])) + 1
    f_in     = freqs[sig_bin]

    # Claim fundamental lobe (±LOBE_HALF bins)
    claimed = {0}
    for b in range(max(1, sig_bin - LOBE_HALF), min(len(pwr), sig_bin + LOBE_HALF + 1)):
        claimed.add(b)
    fund_pwr = sum(pwr[b] for b in claimed if b != 0)

    # Harmonics 2nd–5th: find nearest bin to h*f_in, claim ±LOBE_HALF
    harm_pwr  = 0.0
    harm_bins = []
    for h in range(2, 6):
        hf = h * f_in
        if hf >= 0.5:
            break
        hb = int(np.argmin(np.abs(freqs[1:] - hf))) + 1
        h_lobe = set(range(max(1, hb - LOBE_HALF), min(len(pwr), hb + LOBE_HALF + 1)))
        h_lobe -= claimed
        if not h_lobe:
            continue
        harm_pwr += sum(pwr[b] for b in h_lobe)
        claimed  |= h_lobe
        harm_bins.append(hb)

    noise_pwr = sum(pwr[b] for b in range(len(pwr)) if b not in claimed)

    total_noise = noise_pwr + harm_pwr
    snr  = 10 * np.log10(fund_pwr / noise_pwr)  if noise_pwr  > 0 else 999.0
    thd  = 10 * np.log10(harm_pwr / fund_pwr)   if harm_pwr   > 0 else -999.0
    sndr = 10 * np.log10(fund_pwr / total_noise) if total_noise > 0 else 999.0
    enob = (sndr - 1.76) / 6.02
    sfdr = 10 * np.log10(fund_pwr / max(harm_pwr, 1e-30))

    print(f"  [{label}] N={N}  fund_bin={sig_bin}  f_in={f_in:.4f}·fs"
          f"  SNDR={sndr:.1f} dB  ENOB={enob:.2f} b")

    return dict(
        label=label, codes=codes, N=N,
        freqs=freqs, pwr=pwr,
        fund_bin=sig_bin, harm_bins=harm_bins,
        fund_freq=f_in,
        snr=snr, thd=thd, sndr=sndr, enob=enob, sfdr=sfdr,
    )


# ---------------------------------------------------------------------------
# DNL / INL  (histogram method with arcsine correction)
# ---------------------------------------------------------------------------

def compute_dnl_inl(codes: np.ndarray, n_bits_raw: int, osr: int):
    """
    DNL/INL on the decimated output.

    Both sinc¹ and sinc² are on the [0, (2^N-1)*osr] scale.
    n_levels = (2^N - 1)*osr + 1  (e.g. 29 for N=3, OSR=4).
    Bin edges are at integer steps; sinc² non-integer values fall between
    bins, showing up as a smoother histogram with lower DNL.
    """
    code_max = (2 ** n_bits_raw - 1) * osr          # e.g. 28
    n_levels = code_max + 1                          # e.g. 29

    clipped = np.clip(np.round(codes).astype(int), 0, code_max)
    hist, _ = np.histogram(clipped, bins=n_levels,
                               range=(-0.5, code_max + 0.5))

    # Arcsine ideal distribution (sinusoidal input)
    centres = (np.arange(n_levels) + 0.5) / n_levels
    arcsine = 1.0 / (np.pi * np.sqrt(np.maximum(centres * (1 - centres), 1e-9)))
    arcsine /= arcsine.sum()
    ideal   = arcsine * len(clipped)

    with np.errstate(invalid="ignore", divide="ignore"):
        dnl = np.where(ideal > 0.5, (hist - ideal) / ideal, 0.0)
    inl = np.cumsum(dnl)
    return dnl, inl, clipped, n_levels, code_max


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_all(raw_codes, s1_out, s2_out, m1, m2, osr, n_bits_raw):
    code_max  = (2 ** n_bits_raw - 1) * osr   # e.g. 28 for N=3, OSR=4
    n_out_lvl = code_max + 1                   # e.g. 29

    fig = plt.figure(figsize=(24, 15))
    fig.suptitle(
        f"NS-SAR Benchmark  ·  {n_bits_raw}-bit raw SAR  ·  OSR = {osr}  ·  sinc¹ vs sinc²\n"
        f"Output scale: 0 – {code_max}  ({n_out_lvl} levels for sinc¹, "
        f"up to {osr * code_max + 1} for sinc²)",
        fontsize=13, fontweight="bold",
    )
    gs = fig.add_gridspec(3, 4, hspace=0.52, wspace=0.38)

    # ── Row 0: time-domain waveforms + ENOB bar chart ──────────────────────
    ax_raw = fig.add_subplot(gs[0, 0])
    ax_s1  = fig.add_subplot(gs[0, 1])
    ax_s2  = fig.add_subplot(gs[0, 2])
    ax_bar = fig.add_subplot(gs[0, 3])

    show = min(200, len(raw_codes))
    ax_raw.plot(raw_codes[:show], "k.", ms=2)
    ax_raw.set_title(f"Raw SAR codes  (first {show})")
    ax_raw.set_ylabel("Code [0–7]"); ax_raw.set_xlabel("Sample")
    ax_raw.set_ylim(-0.5, 2 ** n_bits_raw - 0.5)

    show_dec = min(60, len(s1_out))
    ax_s1.plot(s1_out[:show_dec], "b.-", ms=4, lw=0.8)
    ax_s1.set_title(f"sinc¹  ENOB = {m1['enob']:.2f} bits\n"
                    f"integer codes 0–{code_max}  ({n_out_lvl} levels)")
    ax_s1.set_ylabel(f"Code [0–{code_max}]"); ax_s1.set_xlabel("Dec. sample")
    ax_s1.set_ylim(-0.5, code_max + 0.5)

    ax_s2.plot(s2_out[:show_dec], "g.-", ms=4, lw=0.8)
    ax_s2.set_title(f"sinc²  ENOB = {m2['enob']:.2f} bits\n"
                    f"float codes 0–{code_max}  (step 1/{osr})")
    ax_s2.set_ylabel(f"Code [0–{code_max}]"); ax_s2.set_xlabel("Dec. sample")
    ax_s2.set_ylim(-0.5, code_max + 0.5)

    theory_enob = n_bits_raw + 0.5 * log2(osr) + 0.5
    colors = ["steelblue", "seagreen"]
    bars = ax_bar.bar(["sinc¹", "sinc²"], [m1["enob"], m2["enob"]], color=colors, width=0.4)
    ax_bar.axhline(theory_enob, color="red", ls="--", lw=1.2,
                   label=f"Theory  {theory_enob:.2f} b")
    ax_bar.axhline(n_bits_raw, color="gray", ls=":", lw=1.0,
                   label=f"Raw  {n_bits_raw} b")
    ax_bar.set_ylabel("ENOB (bits)"); ax_bar.set_title("ENOB Comparison")
    ax_bar.legend(fontsize=8)
    for bar, m in zip(bars, [m1, m2]):
        ax_bar.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.03,
                    f"{m['enob']:.2f}", ha="center", va="bottom", fontsize=9)

    # ── Row 1: power spectra ────────────────────────────────────────────────
    ax_sp1 = fig.add_subplot(gs[1, :2])
    ax_sp2 = fig.add_subplot(gs[1, 2:])

    def _plot_spectrum(ax, m, color):
        # Normalise so fundamental peak = 0 dBc
        pwr_norm   = m["pwr"] / m["pwr"][m["fund_bin"]]
        mag_db     = 10 * np.log10(np.maximum(pwr_norm, 1e-12))
        ax.plot(m["freqs"], mag_db, color=color, lw=0.7)
        ax.axvline(m["fund_freq"], color="orange", lw=1.0, ls="--",
                   label=f"fund  {m['fund_freq']:.4f}·fs")
        for b in m["harm_bins"]:
            ax.axvline(m["freqs"][b], color="red", lw=0.8, ls=":", alpha=0.6)
        ax.set_xlim(0, 0.5)
        ax.set_ylim(-100, 5)
        ax.set_xlabel("Normalised frequency  (×fs_dec)")
        ax.set_ylabel("Power (dBc, fund = 0 dB)")
        ax.set_title(
            f"{m['label']}  |  SNR {m['snr']:.1f} dB  "
            f"SNDR {m['sndr']:.1f} dB  SFDR {m['sfdr']:.1f} dB  "
            f"THD {m['thd']:.1f} dB"
        )
        ax.legend(fontsize=7)

    _plot_spectrum(ax_sp1, m1, "steelblue")
    _plot_spectrum(ax_sp2, m2, "seagreen")

    # ── Row 2: histograms + DNL/INL ─────────────────────────────────────────
    dnl1, inl1, ic1, nl1, cm1 = compute_dnl_inl(m1["codes"], n_bits_raw, osr)
    dnl2, inl2, ic2, nl2, cm2 = compute_dnl_inl(m2["codes"], n_bits_raw, osr)

    ax_h1  = fig.add_subplot(gs[2, 0])
    ax_di1 = fig.add_subplot(gs[2, 1])
    ax_h2  = fig.add_subplot(gs[2, 2])
    ax_di2 = fig.add_subplot(gs[2, 3])

    bins1 = np.arange(nl1 + 1) - 0.5
    bins2 = np.arange(nl2 + 1) - 0.5
    x1, x2 = np.arange(nl1), np.arange(nl2)

    ax_h1.hist(ic1, bins=bins1, color="steelblue", edgecolor="k", lw=0.3)
    ax_h1.set_title(f"sinc¹  histogram  ({nl1} bins, integer steps)")
    ax_h1.set_xlabel(f"Code [0–{cm1}]"); ax_h1.set_ylabel("Count")

    ax_di1.bar(x1, dnl1, color="steelblue", alpha=0.75, label="DNL")
    ax_di1.plot(x1, inl1, "r-o", ms=2, lw=0.9, label="INL")
    ax_di1.axhline(0, color="k", lw=0.5)
    ax_di1.set_title(
        f"sinc¹  DNL/INL  "
        f"|DNL|={np.max(np.abs(dnl1)):.2f}  |INL|={np.max(np.abs(inl1)):.2f} LSB"
    )
    ax_di1.set_xlabel(f"Code [0–{cm1}]"); ax_di1.set_ylabel("LSB")
    ax_di1.legend(fontsize=7)

    ax_h2.hist(ic2, bins=bins2, color="seagreen", edgecolor="k", lw=0.3)
    ax_h2.set_title(f"sinc²  histogram  ({nl2} bins, step 1/{osr})")
    ax_h2.set_xlabel(f"Code [0–{cm2}]"); ax_h2.set_ylabel("Count")

    ax_di2.bar(x2, dnl2, color="seagreen", alpha=0.75, label="DNL")
    ax_di2.plot(x2, inl2, "r-o", ms=2, lw=0.9, label="INL")
    ax_di2.axhline(0, color="k", lw=0.5)
    ax_di2.set_title(
        f"sinc²  DNL/INL  "
        f"|DNL|={np.max(np.abs(dnl2)):.2f}  |INL|={np.max(np.abs(inl2)):.2f} LSB"
    )
    ax_di2.set_xlabel(f"Code [0–{cm2}]"); ax_di2.set_ylabel("LSB")
    ax_di2.legend(fontsize=7)

    fig.savefig(OUTPUT_PNG, dpi=130, bbox_inches="tight")
    print(f"\nPlot saved → {OUTPUT_PNG}")
    plt.show()


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def print_summary(m1, m2, n_bits_raw, osr):
    theory = n_bits_raw + 0.5 * log2(osr) + 0.5
    hdr = f"  {'Metric':<10}  {'sinc¹':>10}  {'sinc²':>10}  {'Theory':>10}"
    sep = "  " + "-" * (len(hdr) - 2)
    print(f"\n{hdr}\n{sep}")
    rows = [
        ("SNR",  "dB",   m1["snr"],  m2["snr"],  None),
        ("SNDR", "dB",   m1["sndr"], m2["sndr"], None),
        ("ENOB", "bits", m1["enob"], m2["enob"], theory),
        ("THD",  "dB",   m1["thd"],  m2["thd"],  None),
        ("SFDR", "dB",   m1["sfdr"], m2["sfdr"], None),
    ]
    for name, unit, v1, v2, vt in rows:
        t_str = f"{vt:>9.2f} {unit}" if vt is not None else f"{'—':>10}"
        print(f"  {name:<10}  {v1:>9.2f} {unit}  {v2:>9.2f} {unit}  {t_str}")
    print(sep)
    gain = m2["enob"] - m1["enob"]
    print(f"  sinc² gain over sinc¹: {gain:+.2f} bits ENOB")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("NS-SAR Noise-Shaping Benchmark")
    print("=" * 50)
    print(f"  OSR        : {OSR}")
    print(f"  N_BITS_RAW : {N_BITS_RAW}")
    print(f"  VREF       : {VREF} V")

    csv_path = Path(CSV_FILE) if CSV_FILE else _find_csv()
    times, raw_codes = load_csv(csv_path)

    dt = np.median(np.diff(times))
    fs_raw = 1.0 / dt
    fs_dec = fs_raw / OSR
    print(f"\n  fs_raw  : {fs_raw/1e3:.2f} kHz  (one raw SAR code per period)")
    print(f"  fs_dec  : {fs_dec/1e3:.2f} kHz  (after ÷{OSR} decimation)")

    # Apply both filters
    s1_out = sinc1_decimate(raw_codes, OSR)
    s2_out = sinc2_decimate(raw_codes, OSR)
    print(f"\n  sinc¹ samples : {len(s1_out)}  (after decimation)")
    print(f"  sinc² samples : {len(s2_out)}  (after decimation, shorter due to 2R-1 kernel)")

    m1 = compute_metrics(s1_out, DROP_SAMPLES, label="sinc¹")
    m2 = compute_metrics(s2_out, DROP_SAMPLES, label="sinc²")

    print_summary(m1, m2, N_BITS_RAW, OSR)
    plot_all(raw_codes, s1_out, s2_out, m1, m2, OSR, N_BITS_RAW)


if __name__ == "__main__":
    main()
