"""
NS_SAR_ADC Benchmark Script
Reads Cadence Spectre binary PSF transient simulation results and evaluates
SNR, SNDR, ENOB, INL, and DNL for the SAR ADC.

Requirements:
    pip install numpy matplotlib
"""

import sys
import re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# The script auto-detects the testbench from available PSF signals.
# Override any of these only if auto-detection produces wrong results.
# ---------------------------------------------------------------------------

# ── Simulation directory ──────────────────────────────────────────────────
# Set to a specific folder name (e.g. "Sar_3_tb") to pin to one testbench.
# None → scan all known simulation directories and use the most-recently
#         modified PSF (i.e. whatever was just pulled from the server).
TB_NAME = None

# ── Manual overrides (leave None to auto-detect from PSF signals) ─────────
N_BITS_OVERRIDE         = None   # e.g. 3, 8, 10 — overrides signal-based detection
SAMPLE_SIGNAL_OVERRIDE  = None   # e.g. "I0.S"   — overrides signal-based detection
CYCLES_OVERRIDE         = None   # e.g. 5        — overrides signal-based detection
VREF_OVERRIDE           = None   # e.g. 1.0      — overrides PSF auto-detected VREF
INPUT_MODE              = "single"   # "single" | "differential"
VGND                    = 0.0
F_CLK                   = 100e6   # fallback if CLK not in PSF
F_IN                    = None    # always auto-detected from FFT peak
T_SIM                   = None    # always auto-detected from time vector

# Number of initial conversion cycles to discard (startup settling)
DROP_SAMPLES = 5

# ── Known simulation directories (searched newest-first when TB_NAME=None) ─
_KNOWN_SIM_DIRS = [
    "Sar_3_tb",
    "NS_SAR_V1_tb",
    "Differential_SAR_ADC_10bit_tb",
    "Differential_SAR_ADC_10bit_tb",
]

_REPO_ROOT = Path(__file__).parent.parent

def _find_psf_dir():
    """Return the PSF directory to use, searching newest-first if TB_NAME=None."""
    if TB_NAME is not None:
        d = _REPO_ROOT / "simulation" / TB_NAME / "spectre" / "schematic" / "psf"
        return d
    # Scan all known dirs; pick the one with the newest .sig file
    candidates = []
    for name in _KNOWN_SIM_DIRS:
        d = _REPO_ROOT / "simulation" / name / "spectre" / "schematic" / "psf"
        sig = d / "tran.tran.tran.sig"
        if sig.exists():
            candidates.append((sig.stat().st_mtime, d))
    if not candidates:
        # Last resort: any simulation/*/spectre/schematic/psf with a .sig
        for sig in sorted(
            (_REPO_ROOT / "simulation").glob("*/spectre/schematic/psf/tran.tran.tran.sig"),
            key=lambda p: p.stat().st_mtime, reverse=True
        ):
            return sig.parent
        import sys as _sys
        _sys.exit("ERROR: no PSF data found under simulation/. Run pull.sh first.")
    candidates.sort(reverse=True)
    return candidates[0][1]

PSF_DIR = _find_psf_dir()

# ── Signal-based circuit auto-detection ──────────────────────────────────
# Resolved after PSF is loaded (see _autodetect_config() in main()).
# Module-level defaults (overwritten by main after PSF is read):
N_BITS             = N_BITS_OVERRIDE or 8
SAMPLE_SIGNAL      = SAMPLE_SIGNAL_OVERRIDE       # None → CLK fallback
CYCLES_PER_CONVERSION = CYCLES_OVERRIDE or 1
VREF               = VREF_OVERRIDE or 1.0         # DAC reference voltage
VGND               = 0.0

def _autodetect_config(signal_names: list, vdac_max: float = None):
    """
    Infer N_BITS, SAMPLE_SIGNAL, CYCLES_PER_CONVERSION, and VREF from PSF
    signal names and (optionally) the measured DAC output max.

    Returns (n_bits, sample_signal_or_None, cycles, vref, label).
    vref is the DAC reference voltage (may differ from PSF VREF signal which
    can be an unrelated supply rail).
    """
    sigs = set(signal_names)

    # 10-bit top-level SAR (has I4.P1 sample node)
    if "I4.P1" in sigs:
        return 10, "I4.P1", 12, 1.8, "10-bit SAR (Differential_SAR_ADC_10bit_tb)"

    # 3-bit behavioural SAR (has I0.S sample switch)
    if "I0.S" in sigs:
        return 3, "I0.S", 5, 8.0, "3-bit SAR (Sar_3_tb)"

    # NS_SAR_V1 / flat DAC-only testbench — no instance hierarchy
    # Infer N_BITS and Vref from DAC_OUT max if available.
    if "DAC_OUT" in sigs:
        if vdac_max is not None and vdac_max > 0:
            # Try N = 3..10: check if vdac_max ≈ (2^N - 1)/2^N * Vref for common Vrefs
            for vref_cand in [1.0, 1.8, 3.3]:
                for n_cand in range(3, 11):
                    expected = (2**n_cand - 1) / 2**n_cand * vref_cand
                    if abs(vdac_max - expected) / vref_cand < 0.02:  # within 2%
                        label = (f"{n_cand}-bit NS_SAR behavioural model "
                                 f"(Vref={vref_cand}V, inferred from DAC_OUT max)")
                        return n_cand, None, 1, vref_cand, label
        return 8, None, 1, 1.0, "8-bit NS_SAR behavioural model (NS_SAR_V1)"

    # Unknown
    return (N_BITS_OVERRIDE or 8), SAMPLE_SIGNAL_OVERRIDE, (CYCLES_OVERRIDE or 1), 1.0, "unknown circuit"


def detect_n_bits_from_dac(vdac):
    """
    Estimate ADC resolution from the discrete quantisation levels in DAC_OUT.

    Algorithm:
      1. Build an 8192-bin histogram across the full DAC_OUT range.
         Settled DAC codes accumulate many samples → tall, narrow peaks.
         Transition samples (DAC switching between codes) are transient →
         low-count bins between peaks.
      2. Threshold at the 10th percentile of occupied-bin counts to separate
         peaks from transition bins.  Identify contiguous above-threshold
         clusters; each cluster = one valid output code.
      3. n_codes_observed → nearest power of 2 → N_BITS.
      4. LSB = median spacing between cluster centres (weighted by count).
      5. Vref = 2^N_BITS × LSB.

    Returns (n_bits, n_codes_observed, vref_est, lsb_est).
    Returns (None, 0, None, None) on failure.
    """
    v_lo = float(np.percentile(vdac, 0.5))
    v_hi = float(np.percentile(vdac, 99.5))
    vrange = v_hi - v_lo
    if vrange < 1e-9:
        return None, 0, None, None

    n_bins = 8192
    hist, bin_edges = np.histogram(vdac, bins=n_bins, range=(v_lo, v_hi))
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    # Threshold: 10th percentile of non-empty bin counts separates settled-code
    # peaks (many hits) from glide/transition bins (few hits).
    occupied = hist[hist > 0]
    if len(occupied) == 0:
        return None, 0, None, None
    threshold = float(np.percentile(occupied, 10))

    # Find contiguous above-threshold clusters
    above = hist >= threshold
    cluster_starts, cluster_ends = [], []
    in_cluster = False
    for i, a in enumerate(above):
        if a and not in_cluster:
            in_cluster = True
            cluster_starts.append(i)
        elif not a and in_cluster:
            in_cluster = False
            cluster_ends.append(i - 1)
    if in_cluster:
        cluster_ends.append(len(above) - 1)

    n_codes = len(cluster_starts)
    if n_codes < 2:
        return None, n_codes, None, None

    # Weighted centre of each cluster
    centres = []
    for s, e in zip(cluster_starts, cluster_ends):
        w = hist[s:e + 1].astype(float)
        c = bin_centers[s:e + 1]
        centres.append(float(np.average(c, weights=w)))
    centres = np.array(sorted(centres))

    # Nearest power of 2 to the observed code count
    n_bits = int(round(np.log2(n_codes)))
    n_bits = max(1, min(20, n_bits))

    lsb_est  = float(np.median(np.diff(centres)))
    vref_est = float((1 << n_bits) * lsb_est)

    return n_bits, n_codes, vref_est, lsb_est


# ---------------------------------------------------------------------------
# Binary PSF reader
# Discovered format: little-endian float64 vectors, 360-byte header,
# layout = [time, sig[0], sig[1], ..., sig[N-1]] in signal-index order.
# Signal indices are read from the companion .sig file.
# ---------------------------------------------------------------------------
_DAT_HEADER_BYTES = 360

def _parse_sig_file(sig_path: Path) -> dict:
    """
    Parse the ASCII .sig file to get signal name → index mapping and npts.
    Each data line looks like:
      NAME 0 1 320 0 <max_x> <min_y> <max_y> <npts> <index> <type> 0
    """
    signals = {}
    npts = None
    for line in sig_path.read_text(errors="replace").splitlines():
        parts = line.split()
        # data lines have >= 10 whitespace-separated tokens and a numeric 4th field
        if len(parts) < 10:
            continue
        try:
            _npts = int(parts[8])
            idx   = int(parts[9])
        except (ValueError, IndexError):
            continue
        name = parts[0]
        signals[name] = idx
        if npts is None:
            npts = _npts
    return signals, npts


def load_psf() -> dict:
    """
    Load all waveforms from the binary PSF .dat file.
    Returns a dict: signal_name -> numpy array (length npts).
    Also includes the special key 'time'.
    """
    dat_file = PSF_DIR / "tran.tran.tran.dat"
    sig_file = PSF_DIR / "tran.tran.tran.sig"

    for f in (dat_file, sig_file):
        if not f.exists():
            sys.exit(f"ERROR: file not found: {f}")

    signal_index, npts = _parse_sig_file(sig_file)
    if not signal_index or npts is None:
        sys.exit("ERROR: could not parse .sig file")

    file_gb = dat_file.stat().st_size / 1e9
    print(f"Loading: {dat_file}  ({file_gb:.2f} GB, memory-mapped)")

    stride = npts * 8  # bytes per vector (float64)
    expected = _DAT_HEADER_BYTES + (len(signal_index) + 1) * stride
    actual_size = dat_file.stat().st_size
    if actual_size < expected:
        sys.exit(f"ERROR: .dat file smaller than expected ({actual_size} < {expected})")

    def read_vec(slot):
        offset = _DAT_HEADER_BYTES + slot * stride
        return np.memmap(dat_file, dtype="<f8", mode="r", offset=offset, shape=(npts,))

    # slot 0 = time, slot idx+1 = signal with that index
    data = {"time": read_vec(0)}
    for name, idx in signal_index.items():
        data[name] = read_vec(idx + 1)

    return data


def list_signals(data: dict):
    names = [k for k in data if k != "time"]
    print(f"\nAvailable signals ({len(names)}):")
    for n in sorted(names):
        v = data[n]
        print(f"  {n:20s}  [{v.min():.3f}, {v.max():.3f}] V")
    return names


# ---------------------------------------------------------------------------
# Clock frequency auto-detection from CLK signal
# ---------------------------------------------------------------------------
_CLK_MIN_CYCLES = 100  # minimum CLK cycles required for an accurate measurement

def detect_clk_frequency(time, clk_sig):
    """
    Determine CLK frequency accurately from the dominant half-period across
    all threshold crossings.

    Why a log-scale histogram, not span or median:
      A SAR ADC clock is not continuous — it has long idle gaps between
      conversions (gap >> T/2) and may have ringing near transitions
      (gap << T/2).  The span method f = N/(2*t_span) is corrupted by idle
      time.  The simple median is pulled down by ringing bursts.

      Solution: bucket all crossing gaps on a log scale.  Idle gaps and
      ringing gaps land in different bins; the true T/2 is the dominant peak.
      The mean of all gaps within ±30 % of that peak gives an accurate
      half-period averaged over ≥ _CLK_MIN_CYCLES cycles.

    Returns frequency in Hz, or None on failure.
    """
    v_lo = float(np.percentile(clk_sig, 5))
    v_hi = float(np.percentile(clk_sig, 95))
    swing = v_hi - v_lo
    if swing < 0.1:
        return None  # signal is flat — not a real clock

    threshold = 0.5 * (v_lo + v_hi)

    # All threshold crossings — both rising and falling edges
    above = clk_sig >= threshold
    edge_idx = np.where(np.diff(above.astype(np.int8)) != 0)[0]
    if len(edge_idx) < 2:
        return None

    # Drop duplicate timestamps (coarse PSF saves can repeat a timestamp)
    t_edges = time[edge_idx]
    t_edges = t_edges[np.concatenate(([True], np.diff(t_edges) > 0))]
    if len(t_edges) < 2:
        return None

    gaps = np.diff(t_edges)           # all half-period candidates
    gaps = gaps[gaps > 0]
    if len(gaps) < 2:
        return None

    # Log-scale histogram to find the dominant (true) half-period.
    # The number of bins scales with the dataset but is capped at 300 to
    # avoid over-fragmentation on short simulations.
    n_bins = max(50, min(300, len(gaps) // 3))
    log_gaps = np.log10(gaps)
    hist, bin_edges = np.histogram(log_gaps, bins=n_bins)
    peak_bin = int(np.argmax(hist))
    log_half = 0.5 * (bin_edges[peak_bin] + bin_edges[peak_bin + 1])
    half_period_est = 10.0 ** log_half

    # Keep only gaps within ±30 % of the dominant peak (rejects ringing and
    # idle gaps) and average them for the most accurate half-period estimate.
    lo, hi = 0.70 * half_period_est, 1.30 * half_period_est
    valid_gaps = gaps[(gaps >= lo) & (gaps <= hi)]

    n_cycles = len(valid_gaps) / 2.0
    if n_cycles < _CLK_MIN_CYCLES:
        print(f"  WARNING: only {n_cycles:.0f} consistent CLK cycles found in PSF "
              f"(need ≥ {_CLK_MIN_CYCLES} for accurate frequency measurement).  "
              f"Extend the simulation time or check the CLK source.")

    if len(valid_gaps) == 0:
        return None

    half_period = float(np.mean(valid_gaps))
    return 1.0 / (2.0 * half_period)


# ---------------------------------------------------------------------------
# Cycles-per-conversion estimation from CLK + DAC_OUT
# ---------------------------------------------------------------------------
def estimate_cycles_per_conversion(time, vdac, clk_sig, verbose=True):
    """
    Estimate CLK cycles per ADC conversion using only CLK and DAC_OUT.

    Algorithm:
      1. Detect CLK rising edges; measure Fclk from their median spacing.
      2. Sample DAC_OUT at every CLK rising edge.
      3. Find large DAC transitions (> 10 % of full-scale range) — these mark
         the MSB trial at the start of each new conversion.
      4. Cluster adjacent transition indices (MSB settling can span 1-2 CLK
         cycles) and take the first edge of each cluster as the boundary.
      5. Median CLK gap between successive boundaries = cycles per conversion.

    Returns
    -------
    cycles       : int   or None on failure
    f_clk        : float (Hz) or None on failure
    t_boundaries : 1-D float array — timestamps of detected conversion starts
                   (empty array on failure)
    """
    v_lo = float(np.percentile(clk_sig, 5))
    v_hi = float(np.percentile(clk_sig, 95))
    if (v_hi - v_lo) < 0.1:
        if verbose:
            print("  estimate_cycles_per_conversion: CLK swing < 0.1 V — skipped")
        return None, None, np.array([])

    # Frequency via both-edge half-period method (matches detect_clk_frequency)
    f_clk_measured = detect_clk_frequency(time, clk_sig)
    if f_clk_measured is None:
        if verbose:
            print("  estimate_cycles_per_conversion: CLK frequency detection failed")
        return None, None, np.array([])

    # Rising-edge indices only — used as clock-cycle counters for boundary spacing
    threshold = 0.5 * (v_lo + v_hi)
    below  = clk_sig < threshold
    rising = np.where(np.diff(below.astype(np.int8)) == -1)[0]
    if len(rising) < 4:
        if verbose:
            print(f"  estimate_cycles_per_conversion: only {len(rising)} CLK rising edges found")
        return None, None, np.array([])

    t_edges = time[rising]

    # Sample DAC_OUT at each CLK rising edge
    vdac_at_clk = np.interp(t_edges, time, vdac)

    # Large DAC step threshold: 10 % of full-scale range
    vrange = float(np.percentile(vdac, 99) - np.percentile(vdac, 1))
    if vrange < 1e-6:
        if verbose:
            print("  estimate_cycles_per_conversion: DAC_OUT flat — skipped")
        return None, None, np.array([])
    step_thresh = 0.10 * vrange
    dv = np.abs(np.diff(vdac_at_clk))
    large_step_idx = np.where(dv > step_thresh)[0]

    if len(large_step_idx) < 2:
        if verbose:
            print(f"  estimate_cycles_per_conversion: only {len(large_step_idx)} large "
                  f"DAC step(s) found (threshold={step_thresh:.4f} V) — not enough "
                  f"conversions to measure period")
        return None, None, np.array([])

    # Cluster consecutive indices (multi-CLK MSB settling); keep first of each
    clusters = [[large_step_idx[0]]]
    for idx in large_step_idx[1:]:
        if idx - clusters[-1][-1] <= 2:
            clusters[-1].append(idx)
        else:
            clusters.append([idx])
    boundary_edge_indices = np.array([c[0] for c in clusters])

    if len(boundary_edge_indices) < 2:
        if verbose:
            print("  estimate_cycles_per_conversion: fewer than 2 conversion boundaries")
        return None, None, np.array([])

    clk_gaps = np.diff(boundary_edge_indices)
    median_gap = float(np.median(clk_gaps))
    # Keep only gaps within ±20 % of median to exclude startup/end outliers
    consistent = clk_gaps[np.abs(clk_gaps - median_gap) <= 0.20 * median_gap]
    if len(consistent) == 0:
        consistent = clk_gaps
    cycles = int(round(float(np.median(consistent))))

    t_boundaries = t_edges[boundary_edge_indices]

    if verbose:
        print(f"  DAC_OUT analysis → {cycles} CLK cycles/conversion  "
              f"({len(boundary_edge_indices)} boundaries detected, "
              f"{len(consistent)} consistent gaps, "
              f"Fclk={_fmt_freq(f_clk_measured)})")

    return cycles, f_clk_measured, t_boundaries


# ---------------------------------------------------------------------------
# ADC output sample detection
# ---------------------------------------------------------------------------
def extract_adc_samples(time, vdac, sample_sig):
    """
    Find the settled VDAC value at the end of each conversion cycle.

    Uses rising edges of sample_sig to detect conversion boundaries.
    The threshold is set to the midpoint of the signal's actual swing
    so it works for both 0/1.8 V digital signals and analog nodes like
    I4.P1 that sit at intermediate voltages (e.g. 0.25 – 1.9 V).

    VDAC is interpolated at each rising-edge timestamp.  The first
    DROP_SAMPLES edges are discarded to allow startup settling.
    """
    v_lo = float(np.percentile(sample_sig, 5))
    v_hi = float(np.percentile(sample_sig, 95))
    threshold = 0.5 * (v_lo + v_hi)

    below  = sample_sig < threshold
    rising = np.where(np.diff(below.astype(np.int8)) == -1)[0]

    print(f"Sample signal: lo={v_lo:.3f} V  hi={v_hi:.3f} V  "
          f"threshold={threshold:.3f} V  edges={len(rising)}")

    if len(rising) <= DROP_SAMPLES:
        sys.exit(
            f"ERROR: only {len(rising)} rising edges found in sample signal "
            f"(need > {DROP_SAMPLES}).  Check SAMPLE_SIGNAL in config."
        )

    t_out = time[rising[DROP_SAMPLES:]]
    v_out = np.interp(t_out, time, vdac)
    return t_out, v_out


def extract_adc_samples_from_dac_clk(time, vdac, clk_sig):
    """
    Extract ADC output samples using CLK + DAC_OUT, without a dedicated SAMPLE_SIGNAL.

    Sampling strategy — midpoint of the last CLK cycle:
      CYCLES_PER_CONVERSION = N (integer) means each conversion occupies exactly
      N × T_CLK.  The DAC_OUT is fully settled after all bit trials and holds
      steady through the final cycle before the next MSB reset.

      Sample point for conversion i:
          t_sample[i] = t_boundary[i] + (N − 0.5) × T_CLK

      (N − 0.5) places the sample at the centre of the last clock cycle —
      maximum margin from the preceding bit-trial switching (at cycle N−1) and
      from the next conversion's MSB transition (at cycle N).

    Returns (t_out, v_out) after discarding DROP_SAMPLES startup conversions.
    """
    # ── Detect CLK rising edges ──────────────────────────────────────────
    v_lo = float(np.percentile(clk_sig, 5))
    v_hi = float(np.percentile(clk_sig, 95))
    threshold = 0.5 * (v_lo + v_hi)
    below  = clk_sig < threshold
    rising = np.where(np.diff(below.astype(np.int8)) == -1)[0]
    t_edges = time[rising]

    # ── Find conversion boundaries from large DAC_OUT steps ─────────────
    vdac_at_clk = np.interp(t_edges, time, vdac)
    vrange      = float(np.percentile(vdac, 99) - np.percentile(vdac, 1))
    step_thresh = 0.10 * vrange
    dv          = np.abs(np.diff(vdac_at_clk))
    large_step_idx = np.where(dv > step_thresh)[0]

    clusters = [[large_step_idx[0]]]
    for idx in large_step_idx[1:]:
        if idx - clusters[-1][-1] <= 2:
            clusters[-1].append(idx)
        else:
            clusters.append([idx])
    boundary_indices = np.array([c[0] for c in clusters])
    t_boundaries = t_edges[boundary_indices]

    # ── Place sample at midpoint of last CLK cycle ───────────────────────
    t_clk   = 1.0 / F_CLK
    t_settle_offset = (CYCLES_PER_CONVERSION - 0.5) * t_clk
    t_out   = t_boundaries + t_settle_offset
    # Clamp to simulation range before interpolating
    t_out   = np.clip(t_out, time[0], time[-1])
    v_out   = np.interp(t_out, time, vdac)

    print(f"DAC+CLK sampling: {len(t_out)} conversions, "
          f"sampled at cycle {CYCLES_PER_CONVERSION - 0.5:.1f} / {CYCLES_PER_CONVERSION} "
          f"(T_offset = {t_settle_offset*1e9:.2f} ns, "
          f"discarding first {DROP_SAMPLES} for settling)")

    if len(t_out) <= DROP_SAMPLES:
        sys.exit(
            f"ERROR: only {len(t_out)} conversions found via DAC+CLK analysis "
            f"(need > {DROP_SAMPLES}).  Check CLK and DAC_OUT signals."
        )

    return t_out[DROP_SAMPLES:], v_out[DROP_SAMPLES:]


# ---------------------------------------------------------------------------
# INL / DNL from histogram (sine-wave correction)
# ---------------------------------------------------------------------------
def compute_inl_dnl(codes, amp, vos):
    """
    Compute DNL and INL using the histogram method with true sine parameters.

    For each middle code k (1 … 2^N − 2):
        expected[k] = (M / π) · (arcsin((v_hi − Vos) / A) − arcsin((v_lo − Vos) / A))
        DNL[k]      = (count[k] − expected[k]) / expected[k]   [LSBs]

    Code 0 and code 2^N−1 are the clipping bins; their DNL is set to NaN
    because the clipping-histogram method already used those counts to derive
    A and Vos — they carry no independent linearity information.

    INL is the cumulative sum of the valid (middle-code) DNL values.
    Returns dnl, inl (both length 2**N_BITS, in LSBs), and the raw count array.
    """
    n_codes = 2 ** N_BITS
    M = len(codes)
    lsb = (VREF - VGND) / n_codes

    count = np.bincount(codes, minlength=n_codes).astype(float)

    # Ideal expected hits per middle code under arcsine (sine-wave) distribution
    expected = np.full(n_codes, np.nan)
    for k in range(1, n_codes - 1):          # middle codes only
        v_lo = VGND + k * lsb
        v_hi = VGND + (k + 1) * lsb
        lo = np.clip((v_lo - vos) / amp, -1.0, 1.0)
        hi = np.clip((v_hi - vos) / amp, -1.0, 1.0)
        expected[k] = M / np.pi * (np.arcsin(hi) - np.arcsin(lo))

    # DNL[k] = (count[k] − expected[k]) / expected[k]
    # Endpoints (code 0, code 2^N−1) remain NaN — excluded from clipping model
    with np.errstate(divide="ignore", invalid="ignore"):
        dnl = np.where(expected > 0.5, (count - expected) / expected, np.nan)

    # INL = cumulative sum of DNL (endpoint codes contribute 0 via nan_to_num)
    inl = np.nancumsum(np.nan_to_num(dnl, nan=0.0))

    return dnl, inl, count


# ---------------------------------------------------------------------------
# Clipping histogram — sine amplitude and DC offset estimation (IEEE 1241)
# ---------------------------------------------------------------------------
def estimate_amplitude_offset(codes, hist_count):
    """
    Estimate the true sine-wave amplitude (A) and DC offset (Vos) from the
    clipping histogram using the cosine method.

      H_min  = hits in code 0       (lower rail clipping)
      H_max  = hits in code 2^N−1   (upper rail clipping)
      M      = total samples

      C1  = cos(π · H_min / M)
      C2  = cos(π · H_max / M)
      A   = (V_last − V_1) / (C1 + C2)
      Vos = V_1 + A · C1

    V_1 and V_last are the inner transition voltages (boundaries of the first
    and last code bins), i.e. 1 LSB and (2^N − 1) LSBs from VGND.
    """
    n_codes = 2 ** N_BITS
    lsb = (VREF - VGND) / n_codes
    M = len(codes)

    H_min = float(hist_count[0])            # hits at minimum code (lower clipping)
    H_max = float(hist_count[n_codes - 1])  # hits at maximum code (upper clipping)

    # Inner code-transition voltages
    V_1    = VGND + lsb                       # transition code 0 → code 1
    V_last = VGND + (n_codes - 1) * lsb      # transition code N−2 → code N−1

    C1 = np.cos(np.pi * H_min / M)
    C2 = np.cos(np.pi * H_max / M)

    denom = C1 + C2
    if abs(denom) < 1e-12:
        return np.nan, np.nan  # degenerate: no clipping on either rail

    A   = (V_last - V_1) / denom
    Vos = V_1 + A * C1
    return float(A), float(Vos)


# ---------------------------------------------------------------------------
# FFT-based SNR analysis
# ---------------------------------------------------------------------------
def analyse_spectrum(t_samples, v_samples):
    """
    Compute SNR, SNDR, ENOB, INL, DNL from sampled ADC output codes
    using an FFT and histogram.  Returns a results dict.
    """
    # Sampling frequency from actual sample timestamps (before any truncation)
    f_s = 1.0 / np.mean(np.diff(t_samples)) if len(t_samples) > 1 else F_CLK / CYCLES_PER_CONVERSION

    # Truncate to the largest power-of-2 ≤ available samples for FFT efficiency
    # and to avoid spectral leakage from non-integer number of cycles.
    n_pow2 = 1 << (len(t_samples).bit_length() - 1)
    t_samples = t_samples[:n_pow2]
    v_samples = v_samples[:n_pow2]
    N = n_pow2

    # Quantize VDAC to the nearest ADC code.  The raw Spectre waveform values
    # are floating-point analog voltages; using them directly for FFT gives
    # sub-LSB "precision" that doesn't exist in the real ADC and inflates SNR
    # beyond the theoretical Nyquist limit.  Snap to integer codes first.
    lsb = (VREF - VGND) / (2 ** N_BITS)
    codes  = np.clip(np.round(v_samples / lsb).astype(int), 0, 2 ** N_BITS - 1)
    v_quant = codes * lsb   # quantized voltages — true ADC output representation

    # Hann window to reduce spectral leakage; remove DC.
    # A Hann window spreads each tone across a ~4-bin main lobe, so claimed
    # bins are widened to ±3 to capture the full window energy.
    # w = np.hanning(N)
    # v_win = (v_quant - np.mean(v_quant)) * w

    # FFT
    spectrum = np.fft.rfft(v_quant - np.mean(v_quant))  # remove DC before FFT
    power    = np.abs(spectrum) ** 2
    freqs    = np.fft.rfftfreq(N, d=1.0 / f_s)

    dc_bin = 0

    # Auto-detect signal bin: peak power bin (excluding DC).
    # This handles cases where the simulated F_IN differs from the configured value.
    sig_bin = int(np.argmax(power[1:])) + 1  # index into full power array

    f_in_detected = freqs[sig_bin]

    # Claim bins as a set to avoid double-counting.
    # Hann window main lobe is ~4 bins wide → claim ±3 bins around each tone.
    LOBE_HALF = 3
    claimed = {dc_bin}
    for b in range(max(1, sig_bin - LOBE_HALF), min(len(power), sig_bin + LOBE_HALF + 1)):
        claimed.add(b)
    signal_power = sum(power[b] for b in claimed if b != dc_bin)

    # Harmonics 2 – 5 of the detected fundamental
    harmonic_power = 0.0
    harmonics = []
    for h in range(2, 6):
        hf = h * f_in_detected
        if hf >= f_s / 2:
            break
        hb = max(1, np.argmin(np.abs(freqs[1:] - hf)) + 1)
        h_bins = set(range(max(1, hb - LOBE_HALF), min(len(power), hb + LOBE_HALF + 1)))
        h_bins -= claimed          # exclude already-claimed bins
        if not h_bins:
            continue
        hp = sum(power[b] for b in h_bins)
        harmonic_power += hp
        claimed |= h_bins
        harmonics.append((h, hf, hb, hp))

    # Pure noise floor: all remaining unclaimed bins (excl. DC and signal)
    noise_power = sum(power[b] for b in range(len(power)) if b not in claimed)

    # Metrics
    # SNR uses total distortion+noise as denominator (= SINAD / IEEE 1241 definition).
    # This matches the 6.02N+1.76 theoretical formula, which assumes all quantization
    # noise is in the denominator.  In a noise-free simulation, quantization error
    # appears entirely as harmonic distortion; excluding harmonics would give SNR→∞.
    total_noise = noise_power + harmonic_power
    snr  = 10 * np.log10(signal_power / total_noise) if total_noise > 0 else np.inf
    sndr = snr  # identical here; retained as a separate label for clarity
    enob = (sndr - 1.76) / 6.02

    # Estimate true sine parameters first (needs only codes/histogram),
    # then use them to build the ideal arcsine model for DNL/INL.
    hist_count = np.bincount(codes, minlength=2 ** N_BITS).astype(float)
    amp, vos = estimate_amplitude_offset(codes, hist_count)
    dnl, inl, hist_count = compute_inl_dnl(codes, amp, vos)

    return dict(
        snr=snr, sndr=sndr, enob=enob,
        snr_ideal=6.02 * N_BITS + 1.76,
        f_s=f_s, f_in_detected=f_in_detected, freqs=freqs, power=power,
        signal_bin=sig_bin, harmonics=harmonics,
        codes=codes, v_quant=v_quant, n_samples=N,
        dnl=dnl, inl=inl, hist_count=hist_count,
        amp=amp, vos=vos,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def _fmt_freq(f_hz):
    """Return a human-readable frequency string with auto-scaled units."""
    if f_hz >= 1e6:
        return f"{f_hz/1e6:.3f} MHz"
    elif f_hz >= 1e3:
        return f"{f_hz/1e3:.3f} kHz"
    else:
        return f"{f_hz:.3f} Hz"


def _freq_axis_scale(f_max_hz):
    """Return (divisor, unit_label) for a frequency axis whose max is f_max_hz."""
    if f_max_hz >= 1e6:
        return 1e6, "MHz"
    elif f_max_hz >= 1e3:
        return 1e3, "kHz"
    else:
        return 1.0, "Hz"


def print_summary(res):
    sep = "=" * 52
    print(f"\n{sep}")
    print("  NS_SAR_ADC BENCHMARK RESULTS")
    print(sep)
    print(f"  Resolution      : {N_BITS} bits")
    print(f"  Clock frequency : {_fmt_freq(F_CLK)}")
    print(f"  Sampling rate   : {_fmt_freq(res['f_s'])}")
    print(f"  Sim duration    : {T_SIM*1e3:.3f} ms")
    print(f"  Input frequency : {_fmt_freq(res['f_in_detected'])} (detected from FFT)")
    print(f"  FFT samples     : {res['n_samples']}")
    print("-" * 52)
    print(f"  SNR             : {res['snr']:>8.2f} dB  (ideal: {res['snr_ideal']:.2f} dB)")
    print(f"  SNDR            : {res['sndr']:>8.2f} dB")
    print(f"  ENOB            : {res['enob']:>8.2f} bits  (ideal: {N_BITS})")
    print(f"  DNL (peak)      : {float(np.nanmax(np.abs(res['dnl']))):>8.3f} LSB")
    print(f"  INL (peak)      : {float(np.nanmax(np.abs(res['inl']))):>8.3f} LSB")
    amp_str = f"{res['amp']:.4f} V" if not np.isnan(res['amp']) else "N/A (no clipping)"
    vos_str = f"{res['vos']:.4f} V" if not np.isnan(res['vos']) else "N/A"
    print(f"  Amplitude (A)   : {amp_str}")
    print(f"  DC offset (Vos) : {vos_str}")
    print("-" * 52)
    delta = N_BITS - res['enob']
    status = "PASS" if delta <= 0.5 else "FAIL"
    print(f"  STATUS          : {status}  (ENOB loss = {delta:.2f} bits)")
    print(f"{sep}\n")


def plot_results(time, vip, vin, vdac, t_s, v_s, res, t_sim=None):
    from matplotlib.gridspec import GridSpec

    n_codes = 2 ** N_BITS
    code_x  = np.arange(n_codes)
    lsb     = (VREF - VGND) / n_codes
    t_end   = t_sim if t_sim is not None else T_SIM

    # 4-column × 2-row grid; last column spans both rows for the summary table
    fig = plt.figure(figsize=(24, 10))
    fig.suptitle(
        f"NS_SAR_ADC ({N_BITS}-bit)  —  Spectre Simulation Benchmark",
        fontsize=13, fontweight="bold", y=1.01,
    )
    gs = GridSpec(2, 4, figure=fig,
                  width_ratios=[1, 1, 1, 1.15],
                  hspace=0.50, wspace=0.38)

    ax_time = fig.add_subplot(gs[0, 0])   # row 0 col 0 — time domain
    ax_dnl  = fig.add_subplot(gs[0, 1])   # row 0 col 1 — DNL
    ax_inl  = fig.add_subplot(gs[0, 2])   # row 0 col 2 — INL
    ax_spec = fig.add_subplot(gs[1, 0])   # row 1 col 0 — power spectrum
    ax_hist = fig.add_subplot(gs[1, 1])   # row 1 col 1 — histogram
    ax_tf   = fig.add_subplot(gs[1, 2])   # row 1 col 2 — transfer function
    ax_tbl  = fig.add_subplot(gs[:, 3])   # col 3, both rows — summary table

    # ------------------------------------------------------------------ #
    # [0,0] Time domain — show ~100 ADC conversion cycles from the first
    # valid sample (avoids startup settling and fills the window sensibly
    # regardless of whether F_in was reliably detected from the FFT).
    # ------------------------------------------------------------------ #
    t_zoom_start = float(t_s[0]) if len(t_s) > 0 else 0.0
    # Primary zoom: 100 conversion cycles from the first valid sample.
    # Fallback: 10 detected input cycles, capped at total sim duration.
    t_100conv = t_zoom_start + 100.0 / res["f_s"] if res["f_s"] > 0 else t_end
    f_in_plot = res["f_in_detected"] if res["f_in_detected"] > 0 else (F_IN or res["f_s"] / 10)
    t_10cycles = t_zoom_start + 10.0 / f_in_plot
    t_zoom_end = min(t_100conv, t_10cycles, t_end)

    # Use searchsorted so we never build a boolean mask over the full large array
    i0 = int(np.searchsorted(time, t_zoom_start))
    i1 = int(np.searchsorted(time, t_zoom_end, side="right"))
    s0 = int(np.searchsorted(t_s, t_zoom_start))
    s1 = min(int(np.searchsorted(t_s, t_zoom_end, side="right")), s0 + 200)

    # Downsample the continuous waveform for rendering — millions of SAR
    # switching transitions would otherwise fill the axes as a solid block.
    MAX_PLOT_PTS = 8_000
    step = max(1, (i1 - i0) // MAX_PLOT_PTS)
    sl = slice(i0, i1, step)
    t_slice = np.asarray(time[sl]) * 1e6
    if vip is not None:
        ax_time.plot(t_slice, np.asarray(vip[sl]),  color="royalblue", lw=1.2, label="Vin",     alpha=0.9)
    if vin is not None:
        ax_time.plot(t_slice, np.asarray(vin[sl]),  color="seagreen",  lw=1.2, label="VIN",     alpha=0.9)
    ax_time.plot(t_slice, np.asarray(vdac[sl]), color="tomato",    lw=1.0, label="DAC_OUT", alpha=0.85)
    ax_time.plot(np.asarray(t_s[s0:s1]) * 1e6, v_s[s0:s1], "kx", ms=6, zorder=5, label="ADC samples")
    ax_time.set_xlabel("Time (µs)")
    ax_time.set_ylabel("Voltage (V)")
    n_conv_shown = s1 - s0
    _sig_labels = " / ".join(filter(None, [
        "Vin" if vip is not None else None,
        "VIN" if vin is not None else None,
        "DAC_OUT",
    ]))
    ax_time.set_title(f"Time Domain: {_sig_labels}  ({n_conv_shown} conversions shown)")
    ax_time.legend(fontsize=8, loc="upper right")
    ax_time.grid(True, alpha=0.3)
    ax_time.set_xlim(t_zoom_start * 1e6, t_zoom_end * 1e6)

    # ------------------------------------------------------------------ #
    # [0,1] DNL bar chart
    # ------------------------------------------------------------------ #
    dnl      = res["dnl"]
    dnl_valid = not np.all(np.isnan(dnl))
    dnl_num  = np.nan_to_num(dnl)
    dnl_peak = float(np.nanmax(np.abs(dnl))) if dnl_valid else 0.0
    bar_colors = ["tomato" if abs(v) > 0.5 else "steelblue" for v in dnl_num]
    ax_dnl.bar(code_x, dnl_num, color=bar_colors, edgecolor="none")
    ax_dnl.axhline(0,    color="black", lw=0.8)
    ax_dnl.axhline( 0.5, color="red",   lw=0.8, ls="--", label="±0.5 LSB")
    ax_dnl.axhline(-0.5, color="red",   lw=0.8, ls="--")
    ax_dnl.set_xlabel("Output Code")
    ax_dnl.set_ylabel("DNL (LSB)")
    dnl_title = f"DNL  (peak = {dnl_peak:.3f} LSB)" if dnl_valid else "DNL  (insufficient samples)"
    ax_dnl.set_title(dnl_title)
    ax_dnl.xaxis.set_major_locator(plt.MaxNLocator(nbins=10, integer=True))
    dnl_ylim = max(0.6, dnl_peak * 1.4)
    ax_dnl.set_ylim(-dnl_ylim, dnl_ylim)
    ax_dnl.legend(fontsize=8, loc="upper right")
    ax_dnl.grid(True, alpha=0.3, axis="y")

    # ------------------------------------------------------------------ #
    # [0,2] INL line plot
    # ------------------------------------------------------------------ #
    inl      = res["inl"]
    inl_valid = dnl_valid
    inl_peak = float(np.nanmax(np.abs(inl))) if inl_valid else 0.0
    ax_inl.plot(code_x, inl, "-", color="darkorange", lw=1.4)
    ax_inl.axhline(0,    color="black", lw=0.8)
    ax_inl.axhline( 0.5, color="red",   lw=0.8, ls="--", label="±0.5 LSB")
    ax_inl.axhline(-0.5, color="red",   lw=0.8, ls="--")
    ax_inl.set_xlabel("Output Code")
    ax_inl.set_ylabel("INL (LSB)")
    inl_title = f"INL  (peak = {inl_peak:.3f} LSB)" if inl_valid else "INL  (insufficient samples)"
    ax_inl.set_title(inl_title)
    ax_inl.xaxis.set_major_locator(plt.MaxNLocator(nbins=10, integer=True))
    inl_ylim = max(0.6, inl_peak * 1.4)
    ax_inl.set_ylim(-inl_ylim, inl_ylim)
    ax_inl.legend(fontsize=8, loc="upper right")
    ax_inl.grid(True, alpha=0.3)

    # ------------------------------------------------------------------ #
    # [1,0] Power spectrum
    # ------------------------------------------------------------------ #
    freqs  = res["freqs"]
    pwr_db = 10 * np.log10(res["power"] / res["power"].max() + 1e-20)
    f_div, f_unit = _freq_axis_scale(freqs[-1])
    ax_spec.plot(freqs / f_div, pwr_db, color="royalblue", lw=0.8)
    ax_spec.axvline(res["f_in_detected"] / f_div, color="red", ls="--", lw=1.2,
                    label=f"Fin = {_fmt_freq(res['f_in_detected'])}")
    for h, hf, _, _ in res["harmonics"]:
        ax_spec.axvline(hf / f_div, color="orange", ls=":", lw=1.0, label=f"H{h}")
    ax_spec.set_xlabel(f"Frequency ({f_unit})")
    ax_spec.set_ylabel("Power (dB, norm.)")
    ax_spec.set_title("Output Power Spectrum")
    ax_spec.legend(fontsize=8, loc="lower right")
    ax_spec.grid(True, alpha=0.3)
    ax_spec.set_ylim(-100, 5)

    # ------------------------------------------------------------------ #
    # [1,1] Code histogram
    # ------------------------------------------------------------------ #
    ax_hist.bar(code_x, res["hist_count"], color="steelblue", edgecolor="none")
    ax_hist.set_xlabel("Output Code")
    ax_hist.set_ylabel("Count")
    ax_hist.set_title("Output Code Histogram")
    ax_hist.xaxis.set_major_locator(plt.MaxNLocator(nbins=10, integer=True))
    ax_hist.grid(True, alpha=0.3, axis="y")

    # ------------------------------------------------------------------ #
    # [1,2] Transfer function from DNL
    # Transition voltages: T[0]=VGND, T[k+1] = T[k] + (1 + DNL[k]) * LSB
    # ------------------------------------------------------------------ #
    dnl_safe = np.nan_to_num(dnl, nan=0.0)
    actual_trans = np.zeros(n_codes + 1)
    actual_trans[0] = VGND
    for k in range(n_codes):
        actual_trans[k + 1] = actual_trans[k] + lsb * (1.0 + dnl_safe[k])
    ideal_trans = VGND + np.arange(n_codes + 1) * lsb

    def _staircase(transitions, codes):
        xs, ys = [], []
        for k in range(len(codes)):
            xs += [transitions[k], transitions[k + 1]]
            ys += [codes[k], codes[k]]
        for k in range(len(codes) - 1):
            xs += [transitions[k + 1], transitions[k + 1]]
            ys += [codes[k], codes[k + 1]]
        return xs, ys

    xi, yi = _staircase(ideal_trans,  code_x)
    xa, ya = _staircase(actual_trans, code_x)
    ax_tf.plot(xi, yi, color="steelblue", lw=1.6, ls="--", label="Ideal",            zorder=2)
    ax_tf.plot(xa, ya, color="tomato",    lw=2.0,           label="Actual (from DNL)", zorder=3)
    ax_tf.set_xlabel("Input Voltage (V)")
    ax_tf.set_ylabel("Output Code")
    ax_tf.set_title("ADC Transfer Function (from DNL)")
    ax_tf.yaxis.set_major_locator(plt.MaxNLocator(nbins=10, integer=True))
    pad = 0.05 * (VREF - VGND)
    ax_tf.set_xlim(VGND - pad, max(actual_trans[-1], VREF) + pad)
    ax_tf.legend(fontsize=8, loc="upper left")
    ax_tf.grid(True, alpha=0.3)

    # ------------------------------------------------------------------ #
    # [:, 3] Summary table — spans both rows in the last column
    # ------------------------------------------------------------------ #
    ax_tbl.axis("off")
    amp_meas = f"{res['amp']:.4f} V"  if not np.isnan(res["amp"]) else "N/A"
    vos_meas = f"{res['vos']:.4f} V"  if not np.isnan(res["vos"]) else "N/A"
    delta  = N_BITS - res["enob"]
    status = "PASS" if delta <= 0.5 else "FAIL"
    rows = [
        ["N (bits)",         f"{N_BITS}",                               f"{N_BITS}"],
        ["Fclk",             _fmt_freq(F_CLK),                          "—"],
        ["Fs",               _fmt_freq(res['f_s']),                     "—"],
        ["Fin (detected)",   _fmt_freq(res['f_in_detected']),           "—"],
        ["T sim",            f"{T_SIM*1e3:.3f} ms",                    "—"],
        ["N samples",        f"{res['n_samples']}",                      "—"],
        ["SNR (dB)",         f"{res['snr']:.2f}",                       f"{res['snr_ideal']:.2f}"],
        ["SNDR (dB)",        f"{res['sndr']:.2f}",                      f"{res['snr_ideal']:.2f}"],
        ["ENOB (bits)",      f"{res['enob']:.2f}",                      f"{N_BITS:.2f}"],
        ["DNL peak (LSB)",   f"{dnl_peak:.3f}",                         "< 0.5"],
        ["INL peak (LSB)",   f"{inl_peak:.3f}",                         "< 0.5"],
        ["Amplitude (A)",    amp_meas,                                   "—"],
        ["DC offset (Vos)",  vos_meas,                                   "—"],
        ["Status",           status,                                     "PASS"],
    ]
    tbl = ax_tbl.table(
        cellText=rows, colLabels=["Metric", "Measured", "Ideal"],
        loc="center", cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9.5)
    tbl.scale(1.05, 2.05)
    # Header row styling
    for j in range(3):
        tbl[0, j].set_facecolor("#2E5FA3")
        tbl[0, j].set_text_props(color="white", fontweight="bold")
    # Status row colour (green = PASS, red = FAIL)
    status_color = "#4CAF50" if status == "PASS" else "#E53935"
    for j in range(3):
        tbl[len(rows), j].set_facecolor(status_color)
        tbl[len(rows), j].set_text_props(color="white", fontweight="bold")
    ax_tbl.set_title("Performance Summary", pad=10, fontsize=10, fontweight="bold")

    plt.tight_layout()
    out = Path(__file__).parent / "benchmark_results.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Plot saved: {out}")
    try:
        plt.show()
    except Exception:
        pass  # no display available


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("NS_SAR_ADC Benchmark — Spectre PSF Analysis")
    print("-" * 45)

    data = load_psf()
    sig_names = list_signals(data)

    global VREF, F_CLK, T_SIM, N_BITS, SAMPLE_SIGNAL, CYCLES_PER_CONVERSION

    # Load DAC output (needed for VREF and N_BITS inference).
    if "DAC_OUT" not in data:
        sys.exit("ERROR: DAC_OUT signal not found in PSF.")
    vdac = data["DAC_OUT"]
    vdac_max = float(np.percentile(vdac, 99))   # 99th pct avoids outliers

    # ── N_BITS / VREF from discrete DAC_OUT levels ─────────────────────────
    # Count distinct quantisation levels in the raw waveform and find the
    # nearest power of 2.  This is the authoritative source; it overrides the
    # signal-name heuristic from _autodetect_config() when the override is unset.
    _n_dac, _n_codes, _vref_dac, _lsb_dac = detect_n_bits_from_dac(vdac)
    if _n_dac is not None:
        print(f"\nDAC_OUT level analysis : {_n_codes} distinct codes  "
              f"→  2^{_n_dac} = {1 << _n_dac}  →  N_BITS = {_n_dac}")
        print(f"  LSB ≈ {_lsb_dac*1e3:.4f} mV    Vref ≈ {_vref_dac:.4f} V")
    else:
        print("\nDAC_OUT level analysis : could not identify discrete levels "
              "(signal may be noise or flat)")

    # Auto-detect remaining config (SAMPLE_SIGNAL, CYCLES) from signal names.
    _n, _ss, _cyc, _vref_hint, _label = _autodetect_config(sig_names, vdac_max)
    if SAMPLE_SIGNAL_OVERRIDE is None:
        SAMPLE_SIGNAL = _ss
    if CYCLES_OVERRIDE is None:
        CYCLES_PER_CONVERSION = _cyc

    # N_BITS: DAC level count takes priority over signal-name heuristic
    if N_BITS_OVERRIDE is not None:
        N_BITS = N_BITS_OVERRIDE
    elif _n_dac is not None:
        N_BITS = _n_dac
    else:
        N_BITS = _n

    # VREF: DAC level spacing takes priority over signal-name heuristic
    if VREF_OVERRIDE is not None:
        VREF = VREF_OVERRIDE
    elif _vref_dac is not None:
        VREF = _vref_dac
    else:
        VREF = _vref_hint

    print(f"\nDetected circuit : {_label}")
    print(f"  N_BITS={N_BITS}, CYCLES_PER_CONV={CYCLES_PER_CONVERSION}, "
          f"SAMPLE_SIGNAL={SAMPLE_SIGNAL!r}, VREF={VREF:.4f} V")
    print(f"  PSF dir: {PSF_DIR}")

    # Warn if the PSF VREF signal differs significantly from the inferred DAC reference.
    # For some testbenches the VREF pin carries an unrelated supply rail (e.g. 8 V),
    # not the DAC reference, so we do NOT overwrite the auto-detected value here.
    vref_sig = data.get("VREF", None)
    if vref_sig is not None:
        vref_psf = float(np.percentile(vref_sig, 95))
        if abs(vref_psf - VREF) > 0.05 * VREF:
            print(f"  NOTE: PSF VREF signal = {vref_psf:.3f} V differs from DAC Vref "
                  f"= {VREF:.3f} V (VREF pin may be an unrelated supply rail).")

    # ── CLK signal analysis ────────────────────────────────────────────────
    # Step 1: basic edge-count frequency (may be aliased by Spectre's adaptive
    #         timestep — used only for diagnostics here).
    # Step 2: estimate cycles-per-conversion from CLK + DAC_OUT transitions so
    #         the script works for any ADC without hardcoded cycle counts.
    _f_clk_from_sig  = None
    _cycles_from_dac = None
    if "CLK" in data:
        clk_sig = data["CLK"]
        clk_swing = float(np.percentile(clk_sig, 95)) - float(np.percentile(clk_sig, 5))
        if clk_swing < 0.9:
            print(f"\nWARNING: CLK signal swing is only {clk_swing*1e3:.1f} mV "
                  f"(expected ≥0.9 V for 1.8 V logic).  "
                  f"The clock source may be absent or mis-connected in this testbench.")

        # Authoritative CLK frequency — measured directly from the CLK waveform
        # using the dominant half-period histogram.  This value is set as F_CLK
        # immediately; CYCLES_PER_CONVERSION is derived from it after Fs is known.
        _f_clk_from_sig = detect_clk_frequency(data["time"], clk_sig)
        if _f_clk_from_sig is not None:
            F_CLK = _f_clk_from_sig
            print(f"CLK  measured from signal : {_fmt_freq(F_CLK)}")
        else:
            print(f"CLK  detection failed (swing={clk_swing*1e3:.1f} mV) — "
                  f"using fallback {_fmt_freq(F_CLK)}")

        # Estimate cycles/conversion from CLK rising edges + DAC_OUT transitions.
        if CYCLES_OVERRIDE is None:
            print("\nEstimating cycles/conversion from CLK + DAC_OUT ...")
            _cycles_from_dac, _, _ = estimate_cycles_per_conversion(
                data["time"], vdac, clk_sig
            )
            if _cycles_from_dac is not None:
                CYCLES_PER_CONVERSION = _cycles_from_dac
                print(f"  → CYCLES_PER_CONVERSION = {CYCLES_PER_CONVERSION}  "
                      f"(from DAC_OUT boundary analysis)")
            else:
                print(f"  → DAC+CLK estimation failed; "
                      f"keeping heuristic value ({CYCLES_PER_CONVERSION})")

    time = data["time"]
    T_SIM = float(time[-1])   # actual simulation end time from PSF
    # vdac already loaded above for VREF/N_BITS inference
    # Input signals are optional — load if present in PSF, otherwise omit from plot.
    # They are never used for calculations; only VDAC drives analysis.
    vip, vin = None, None

    print(f"\nTime    : {time[0]*1e9:.1f} – {T_SIM*1e9:.1f} ns  ({len(time)} points)")
    if vip is not None:
        print(f"Vin     : {float(vip.min()):.3f} – {float(vip.max()):.3f} V")
    if vin is not None:
        print(f"VIN     : {float(vin.min()):.3f} – {float(vin.max()):.3f} V")
    print(f"VDAC    : {float(vdac.min()):.3f} – {float(vdac.max()):.3f} V")

    # ── Conversion boundary detection ─────────────────────────────────────
    # Priority:
    #   1. EOC signal — each rising edge marks a completed conversion (best)
    #   2. Explicit SAMPLE_SIGNAL override set at top of file
    #   3. DAC_OUT + CLK boundary detection (no dedicated signal available)
    #   4. Raw CLK edges (last resort)
    if "EOC" in data:
        print(f"\nSample source : EOC (end-of-conversion pulse)")
        t_s, v_s = extract_adc_samples(time, vdac, data["EOC"])
    elif SAMPLE_SIGNAL is not None and SAMPLE_SIGNAL in data:
        print(f"\nSample source : SAMPLE_SIGNAL '{SAMPLE_SIGNAL}'")
        t_s, v_s = extract_adc_samples(time, vdac, data[SAMPLE_SIGNAL])
    elif "CLK" in data and _cycles_from_dac is not None:
        print(f"\nSample source : DAC_OUT + CLK boundary detection")
        t_s, v_s = extract_adc_samples_from_dac_clk(time, vdac, data["CLK"])
    elif "CLK" in data:
        print(f"\nSample source : CLK edges (last-resort fallback)")
        t_s, v_s = extract_adc_samples(time, vdac, data["CLK"])
    else:
        sig_list = sorted(k for k in data if k != "time")
        sys.exit(
            f"ERROR: no conversion boundary source found.  "
            f"Add an EOC signal to the testbench or set SAMPLE_SIGNAL.\n"
            f"Available signals: {sig_list}"
        )
    print(f"\nADC samples detected: {len(t_s)}")

    res = analyse_spectrum(t_s, v_s)

    # F_CLK is already set from the CLK signal above.
    # Use it together with the measured Fs to refine CYCLES_PER_CONVERSION when
    # the DAC+CLK boundary analysis didn't produce a value.
    if CYCLES_OVERRIDE is None and _cycles_from_dac is None and res["f_s"] > 0:
        derived_cycles = int(round(F_CLK / res["f_s"]))
        if derived_cycles >= 1:
            CYCLES_PER_CONVERSION = derived_cycles
            print(f"  CYCLES_PER_CONVERSION = {CYCLES_PER_CONVERSION}  "
                  f"(F_CLK {_fmt_freq(F_CLK)} ÷ Fs {_fmt_freq(res['f_s'])})")

    print(f"Fs   = {_fmt_freq(res['f_s'])}  "
          f"({CYCLES_PER_CONVERSION} CLK cycles/conversion)")

    print_summary(res)
    plot_results(time, vip, vin, vdac, t_s, v_s, res, t_sim=T_SIM)


if __name__ == "__main__":
    main()
