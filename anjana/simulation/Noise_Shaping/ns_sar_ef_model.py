"""
Mathematical / behavioral model of the 2nd-order Error-Feedback (EF) NS-SAR ADC
architecture described in:

    S. Li, B. Qiao, M. Gandara, D. Z. Pan, N. Sun,
    "A 13-ENOB Second-Order Noise-Shaping SAR ADC Realizing Optimized NTF
    Zeros Using the Error-Feedback Structure," IEEE JSSC, vol. 53, no. 12,
    Dec. 2018.
    (see simulation/Noise_Shaping/resources/2018_A_13-ENOB_...pdf)

Implements the paper's system-level equations directly:
    NTF(z) = 1 - K_EF*(z^-1 - 0.5*z^-2)              eq.(1)
    K_EF   = G_damp * A_CS                            (Sec. III-A/B)
    A_CS   = Cres1 / (CDAC + 2*Cres1)                  (Sec. IV-A, Fig. 10)
    K_EF_opt(OSR) ~= 2 / (1 + pi^2/(3*OSR^2))          eq.(5)

Electrical parameters (Sec. IV-A / Fig. 10 / Fig. 14, "This work" column of
Table I) are used as-is: CDAC=2pF, Cres1=Cres2=Cdelay=143fF, G=30, N=9-bit
SAR, Fs=10 MS/s, OSR=8, comparator/D-Amp input-referred noise = 85 uVrms.

The paper does not state an explicit reference voltage. It does state that
CDAC (2 pF) "is set to make the sampling noise contribution equal to the
quantization noise", i.e. kT/CDAC = LSB^2/12. That relation is used below to
derive LSB and the full-scale voltage from the given capacitor value and
resolution -- everything else in the model then follows from stated
electrical parameters, not from an assumed voltage range.

Simplifications (for a system-level model, not a transistor-level one):
  - The SAR quantizer is treated as ideal/accurate at every trial (the paper
    itself notes the SAR "inherently provid[es] accurate residues"), so
    sub-ranging/redundancy circuitry (Fig. 17) is not separately modeled.
  - Clock jitter (eq. 6-8) is a ~2% noise contributor per the paper and is
    omitted; thermal (kT/CDAC) and comparator/D-Amp noise are included since
    they are the dominant, explicitly-quantified noise sources.
  - G and A_CS are modeled as separate stages (matches Fig. 4/13 circuit
    partitioning) though only their product K_EF sets the NTF.
"""

from dataclasses import dataclass
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

K_BOLTZMANN = 1.380649e-23

# ---------------------------------------------------------------------------
# Electrical parameters (paper's "This work" design point)
# ---------------------------------------------------------------------------


@dataclass
class NSSARParams:
    n_bits: int = 9                # 9-bit SAR core (Sec. IV-A)
    osr: int = 8                   # Table I
    fs: float = 10e6               # Table I: Fs = 10 MS/s
    temperature: float = 300.0     # K, room temp (Fig. 22, 25 degC point)

    cdac: float = 2e-12            # F, single-ended CDAC (Fig. 10)
    cres1: float = 143e-15         # F (Fig. 10)
    cres2: float = 143e-15         # F
    cdelay: float = 143e-15        # F
    g_damp: float = 30.0           # D-Amp gain (Fig. 10, Sec. V)

    comparator_noise_rms: float = 85e-6  # V, input-referred (Sec. IV-B)

    @property
    def a_cs(self) -> float:
        return self.cres1 / (self.cdac + 2 * self.cres1)

    @property
    def k_ef(self) -> float:
        return self.g_damp * self.a_cs

    @property
    def lsb(self) -> float:
        # kT/CDAC == LSB^2/12  =>  LSB = sqrt(12*kT/CDAC)  (Sec. IV-A design rule)
        kt = K_BOLTZMANN * self.temperature
        return np.sqrt(12.0 * kt / self.cdac)

    @property
    def vfs(self) -> float:
        return self.lsb * (2 ** self.n_bits)

    @property
    def full_scale(self) -> float:
        return (2 ** (self.n_bits - 1)) * self.lsb

    @property
    def sigma_sample(self) -> float:
        kt = K_BOLTZMANN * self.temperature
        return np.sqrt(kt / self.cdac)

    @property
    def bandwidth(self) -> float:
        return self.fs / (2 * self.osr)


# ---------------------------------------------------------------------------
# NTF / loop-filter math (eq. 1-5, Fig. 5-8)
# ---------------------------------------------------------------------------


def ntf_response(omega, k_ef):
    """|NTF(e^jw)| per eq.(1): NTF(z) = 1 - K_EF*(z^-1 - 0.5*z^-2)."""
    z_inv = np.exp(-1j * omega)
    return 1.0 - k_ef * (z_inv - 0.5 * z_inv ** 2)


def ntf_zeros(k_ef):
    """Zeros of z^2 - K_EF*z + 0.5*K_EF = 0 (NTF(z) multiplied by z^2)."""
    return np.roots([1.0, -k_ef, 0.5 * k_ef])


def inband_sqnr_db(k_ef, n_bits, osr, n_points=4000):
    """Closed-form-equivalent in-band SQNR from the NTF only (ideal quantizer,
    no thermal noise) -- reproduces Fig. 6's SQNR-vs-K_EF sweep."""
    omega = np.linspace(1e-6, np.pi / osr, n_points)
    ntf_mag2 = np.abs(ntf_response(omega, k_ef)) ** 2
    lsb = 1.0  # normalized; cancels in the ratio below
    noise_power = (lsb ** 2 / 12.0) * np.trapezoid(ntf_mag2, omega) / np.pi
    signal_power = (lsb * 2 ** (n_bits - 1)) ** 2 / 2.0
    return 10 * np.log10(signal_power / noise_power)


def k_ef_opt_approx(osr):
    """eq.(5): closed-form approximation of the optimum K_EF for a given OSR."""
    return 2.0 / (1.0 + (np.pi ** 2) / (3.0 * osr ** 2))


def k_ef_opt_exact(n_bits, osr, n_grid=4000):
    """Numeric optimum of inband_sqnr_db over K_EF in [1, 2) via grid search --
    cross-check for eq.(5)'s Taylor approximation (paper's Fig. 8)."""
    k_grid = np.linspace(1.0, 1.999, n_grid)
    sqnr = [inband_sqnr_db(k, n_bits, osr) for k in k_grid]
    return k_grid[int(np.argmax(sqnr))]


# ---------------------------------------------------------------------------
# Time-domain EF NS-SAR simulator (Fig. 2 / Fig. 4 / Fig. 11 signal flow)
# ---------------------------------------------------------------------------


class EFNSSAR:
    """
    Error-feedback NS-SAR ADC behavioral model.

    Per sample n:
      1. kT/CDAC thermal noise is sampled onto the CDAC along with vin.
      2. The passive SC FIR (Cres1/Cres2/Cdelay) holds the previous two
         quantization residues, amplified by the reused D-Amp (gain G) and
         attenuated by the charge-sharing factor A_CS, and subtracts
         K_EF*(err[n-1] - 0.5*err[n-2]) from the summing node -- this is the
         circuit realization of eq.(1)'s loop filter H(z) = K_EF*(z^-1 - 0.5*z^-2).
      3. The comparator (with its own input-referred noise) makes the SAR
         decision; the residue is the true analog difference between the
         noisy target and the chosen code, which is what physically appears
         on the CDAC for the next EF cycle.
    """

    def __init__(self, params: NSSARParams, enable_ns: bool = True, seed: int = 42):
        self.p = params
        self.enable_ns = enable_ns
        self.rng = np.random.default_rng(seed)
        self.err1 = 0.0  # err[n-1]
        self.err2 = 0.0  # err[n-2]
        self.full_scale = (2 ** (self.p.n_bits - 1)) * self.p.lsb

    def _quantize(self, target: float):
        decision_val = target + self.rng.normal(0.0, self.p.comparator_noise_rms)
        clipped = np.clip(decision_val, -self.full_scale, self.full_scale - self.p.lsb)
        code = int(round(clipped / self.p.lsb))
        code = max(min(code, 2 ** (self.p.n_bits - 1) - 1), -(2 ** (self.p.n_bits - 1)))
        vdac = code * self.p.lsb
        err = target - vdac  # true physical residue left on the CDAC
        return code, err

    def step(self, vin: float):
        vin_noisy = vin + self.rng.normal(0.0, self.p.sigma_sample)

        if self.enable_ns:
            # With err[n] := target[n] - vdac[n], predictive error feedback
            # target[n] = vin[n] + K_EF*(err[n-1]-0.5*err[n-2]) makes
            # vdac[n] = vin[n] - NTF(z)*err(z), |NTF|=|1-K_EF(z^-1-0.5z^-2)| (eq. 1).
            feedback = self.p.k_ef * (self.err1 - 0.5 * self.err2)
        else:
            feedback = 0.0

        target = vin_noisy + feedback
        code, err = self._quantize(target)

        self.err2 = self.err1
        self.err1 = err
        return code

    def run(self, vin_seq: np.ndarray) -> np.ndarray:
        codes = np.empty(len(vin_seq), dtype=np.int64)
        for n, vin in enumerate(vin_seq):
            codes[n] = self.step(vin)
        return codes


# ---------------------------------------------------------------------------
# FFT-based performance evaluation
# ---------------------------------------------------------------------------


def coherent_bin(n_samples, band_limit_bin, target_fraction=0.61):
    from math import gcd
    m = int(round(target_fraction * band_limit_bin))
    m = m if m % 2 == 1 else m + 1
    while gcd(m, n_samples) != 1:
        m += 2
    return m


def evaluate_performance(codes: np.ndarray, params: NSSARParams, signal_bin: int,
                          band_limit_bin: int = None, leak_bins: int = 4):
    n = len(codes)
    x = codes.astype(np.float64) * params.lsb
    window = np.blackman(n)
    win_gain = window.sum()
    xw = x * window
    spec = np.fft.rfft(xw)
    mag2 = (np.abs(spec) / (win_gain / 2.0)) ** 2  # amplitude-normalized power per bin

    if band_limit_bin is None:
        band_limit_bin = n // (2 * params.osr)

    sig_lo, sig_hi = max(1, signal_bin - leak_bins), min(len(mag2) - 1, signal_bin + leak_bins)
    signal_power = mag2[sig_lo:sig_hi + 1].sum()

    inband = mag2[1:band_limit_bin + 1].copy()  # exclude DC
    sig_lo_ib, sig_hi_ib = sig_lo - 1, sig_hi - 1
    noise_dist_power = inband.sum() - inband[max(0, sig_lo_ib):sig_hi_ib + 1].sum()

    # Harmonics restricted to the same in-band region as noise_dist_power, so the
    # SNR subtraction below can never go negative (harmonics are a subset of it).
    harmonics_power_inband = 0.0
    full_spec = mag2[1:].copy()  # full-spectrum copy, used for THD/SFDR (informative only)
    inband_masked = inband.copy()
    inband_masked[max(0, sig_lo_ib):sig_hi_ib + 1] = 0.0
    full_spec[max(0, sig_lo - 1):sig_hi] = 0.0
    for h in range(2, 8):
        hb = signal_bin * h
        if hb >= len(mag2):
            break
        lo, hi = max(0, hb - leak_bins - 1), min(len(full_spec), hb + leak_bins)
        full_spec[lo:hi] = 0.0
        if hb <= band_limit_bin:
            lo_ib, hi_ib = max(0, lo - 1), min(len(inband_masked), hi - 1)
            harmonics_power_inband += inband_masked[lo_ib:hi_ib].sum()
            inband_masked[lo_ib:hi_ib] = 0.0

    snr_db = 10 * np.log10(signal_power / max(noise_dist_power - harmonics_power_inband, 1e-30))
    sndr_db = 10 * np.log10(signal_power / max(noise_dist_power, 1e-30))
    enob = (sndr_db - 1.76) / 6.02
    thd_db = 10 * np.log10(max(harmonics_power_inband, 1e-30) / signal_power)

    spur = full_spec.max() if full_spec.size else 0.0
    sfdr_db = 10 * np.log10(signal_power / max(spur, 1e-30))

    freqs = np.fft.rfftfreq(n, d=1.0 / params.fs)
    psd_dbfs = 10 * np.log10(np.maximum(mag2, 1e-30) / signal_power) if signal_power > 0 else None

    return dict(snr_db=snr_db, sndr_db=sndr_db, enob=enob, thd_db=thd_db,
                sfdr_db=sfdr_db, freqs=freqs, psd_dbfs=psd_dbfs)


# ---------------------------------------------------------------------------
# Main: reproduce the paper's key design/performance figures
# ---------------------------------------------------------------------------


def main():
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)

    p = NSSARParams()
    print("=== Derived electrical parameters ===")
    print(f"A_CS               = {p.a_cs:.5f}  (paper: 1/16 = {1/16:.5f})")
    print(f"K_EF = G*A_CS      = {p.k_ef:.4f}  (paper: 1.875)")
    print(f"LSB                = {p.lsb*1e6:.2f} uV   (from kT/CDAC = LSB^2/12)")
    print(f"Full scale (VFS)   = {p.vfs*1e3:.2f} mV")
    print(f"sigma_sample (kT/C)= {p.sigma_sample*1e6:.2f} uVrms")
    print(f"comparator noise   = {p.comparator_noise_rms*1e6:.2f} uVrms")
    print(f"Bandwidth (Fs/2OSR)= {p.bandwidth/1e3:.1f} kHz  (paper: 625 kHz)")
    print(f"K_EF_opt approx eq5= {k_ef_opt_approx(p.osr):.4f}")
    print(f"K_EF_opt exact     = {k_ef_opt_exact(p.n_bits, p.osr):.4f}")

    fig, axs = plt.subplots(2, 3, figsize=(20, 11))

    # --- [0,0] NTF magnitude vs K_EF (Fig. 5) ---------------------------------
    freq_norm = np.logspace(-3, 0, 2000) * np.pi
    for k, style, label in [(2.0, "k--", "K_EF=2.000"),
                              (1.9375, "r:", "K_EF=1.9375"),
                              (p.k_ef, "b-", f"K_EF={p.k_ef:.4f} (this design)")]:
        mag_db = 20 * np.log10(np.abs(ntf_response(freq_norm, k)))
        axs[0, 0].semilogx(freq_norm / np.pi, mag_db, style, label=label)
    axs[0, 0].axvline(1 / p.osr, color="gray", linestyle=":", label=f"1/OSR={1/p.osr:.3f}")
    axs[0, 0].set_title("NTF Magnitude vs K_EF (eq. 1, Fig. 5)")
    axs[0, 0].set_xlabel("Normalized Frequency (f/fs, log)")
    axs[0, 0].set_ylabel("|NTF| (dB)")
    axs[0, 0].set_ylim(-60, 20)
    axs[0, 0].legend(fontsize=8)
    axs[0, 0].grid(True, which="both", alpha=0.3)

    # --- [0,1] SQNR vs K_EF (Fig. 6) ------------------------------------------
    kefs = np.linspace(1.7, 2.0, 61)
    sqnrs = [inband_sqnr_db(k, p.n_bits, p.osr) for k in kefs]
    axs[0, 1].plot(kefs, sqnrs, "b.-")
    k_opt = k_ef_opt_exact(p.n_bits, p.osr)
    axs[0, 1].axvline(k_opt, color="r", linestyle="--",
                       label=f"K_EF_opt={k_opt:.4f}")
    axs[0, 1].set_title(f"Ideal In-Band SQNR vs K_EF (N={p.n_bits}b, OSR={p.osr})")
    axs[0, 1].set_xlabel("K_EF")
    axs[0, 1].set_ylabel("SQNR (dB)")
    axs[0, 1].legend(fontsize=8)
    axs[0, 1].grid(True, alpha=0.3)

    # --- [0,2] K_EF_opt vs OSR (Fig. 8) ----------------------------------------
    osrs = np.arange(4, 26)
    approx = [k_ef_opt_approx(o) for o in osrs]
    exact = [k_ef_opt_exact(p.n_bits, o) for o in osrs]
    axs[0, 2].plot(osrs, approx, "bs-", label="Approx (eq. 5)", markersize=4)
    axs[0, 2].plot(osrs, exact, "ro", label="Exact (numeric)", markersize=4, fillstyle="none")
    axs[0, 2].set_title("Optimum K_EF vs OSR (eq. 5, Fig. 8)")
    axs[0, 2].set_xlabel("OSR")
    axs[0, 2].set_ylabel("Optimum K_EF")
    axs[0, 2].legend(fontsize=8)
    axs[0, 2].grid(True, alpha=0.3)

    # --- Time-domain simulation: NS enabled vs disabled -----------------------
    n_samples = 2 ** 16
    band_limit_bin = n_samples // (2 * p.osr)
    m = coherent_bin(n_samples, band_limit_bin)
    f_in = m * p.fs / n_samples
    t = np.arange(n_samples) / p.fs
    amplitude = 0.9 * p.full_scale
    vin = amplitude * np.sin(2 * np.pi * f_in * t)

    adc_ns = EFNSSAR(p, enable_ns=True, seed=1)
    codes_ns = adc_ns.run(vin)
    perf_ns = evaluate_performance(codes_ns, p, signal_bin=m, band_limit_bin=band_limit_bin)

    adc_no_ns = EFNSSAR(p, enable_ns=False, seed=1)
    codes_no_ns = adc_no_ns.run(vin)
    perf_no_ns = evaluate_performance(codes_no_ns, p, signal_bin=m, band_limit_bin=band_limit_bin)

    print("\n=== Time-domain FFT performance (N=%d, Fin=%.1f kHz) ===" % (n_samples, f_in / 1e3))
    print(f"With noise shaping:    SNR={perf_ns['snr_db']:.2f} dB  SNDR={perf_ns['sndr_db']:.2f} dB  "
          f"ENOB={perf_ns['enob']:.2f} b  SFDR={perf_ns['sfdr_db']:.2f} dB  THD={perf_ns['thd_db']:.2f} dB")
    print(f"Without noise shaping: SNR={perf_no_ns['snr_db']:.2f} dB  SNDR={perf_no_ns['sndr_db']:.2f} dB  "
          f"ENOB={perf_no_ns['enob']:.2f} b  SFDR={perf_no_ns['sfdr_db']:.2f} dB")
    print("Paper (measured, Table I 'This work'): SNDR=79 dB, ENOB=13 b, SFDR=89 dB, DR=80.5 dB")

    axs[1, 0].semilogx(perf_no_ns["freqs"][1:], perf_no_ns["psd_dbfs"][1:], color="0.7", label="w/o noise shaping")
    axs[1, 0].semilogx(perf_ns["freqs"][1:], perf_ns["psd_dbfs"][1:], color="b", label="w/ noise shaping")
    axs[1, 0].axvline(p.bandwidth, color="r", linestyle=":", label=f"BW={p.bandwidth/1e3:.0f} kHz")
    axs[1, 0].set_title("Output Spectrum: NS Enabled vs Disabled (Fig. 19)")
    axs[1, 0].set_xlabel("Frequency (Hz)")
    axs[1, 0].set_ylabel("Amplitude (dBFS)")
    axs[1, 0].set_ylim(-140, 5)
    axs[1, 0].legend(fontsize=8, loc="lower left")
    axs[1, 0].grid(True, which="both", alpha=0.3)

    # --- [1,1] SNR/SNDR vs input amplitude (dynamic range, Fig. 20) -----------
    n_dr = 2 ** 15
    band_limit_bin_dr = n_dr // (2 * p.osr)
    m_dr = coherent_bin(n_dr, band_limit_bin_dr)
    f_in_dr = m_dr * p.fs / n_dr
    t_dr = np.arange(n_dr) / p.fs

    dbfs_points = np.arange(0, -85, -5)
    snrs, sndrs = [], []
    for dbfs in dbfs_points:
        amp = p.full_scale * (10 ** (dbfs / 20.0))
        vin_dr = amp * np.sin(2 * np.pi * f_in_dr * t_dr)
        adc = EFNSSAR(p, enable_ns=True, seed=7)
        codes_dr = adc.run(vin_dr)
        perf = evaluate_performance(codes_dr, p, signal_bin=m_dr, band_limit_bin=band_limit_bin_dr)
        snrs.append(perf["snr_db"])
        sndrs.append(perf["sndr_db"])

    axs[1, 1].plot(dbfs_points, snrs, "r.-", label="SNR")
    axs[1, 1].plot(dbfs_points, sndrs, "b.-", label="SNDR")
    dr_est = dbfs_points[np.argmax(np.array(sndrs) < 3)] if any(np.array(sndrs) < 3) else dbfs_points[-1]
    axs[1, 1].set_title("SNR/SNDR vs Input Level -- Dynamic Range (Fig. 20)")
    axs[1, 1].set_xlabel("Input Level (dBFS)")
    axs[1, 1].set_ylabel("Amplitude (dB)")
    axs[1, 1].legend(fontsize=8)
    axs[1, 1].grid(True, alpha=0.3)

    # --- [1,2] Performance summary table ---------------------------------------
    axs[1, 2].axis("off")
    rows = [
        ("Architecture", "True EF, 2nd-order", ""),
        ("N (SAR bits)", f"{p.n_bits}", "9"),
        ("OSR", f"{p.osr}", "8"),
        ("Fs", f"{p.fs/1e6:.0f} MS/s", "10 MS/s"),
        ("Bandwidth", f"{p.bandwidth/1e3:.0f} kHz", "625 kHz"),
        ("K_EF", f"{p.k_ef:.4f}", "1.875"),
        ("SNR", f"{perf_ns['snr_db']:.1f} dB", "--"),
        ("SNDR", f"{perf_ns['sndr_db']:.1f} dB", "79 dB"),
        ("ENOB", f"{perf_ns['enob']:.1f} b", "13 b"),
        ("SFDR", f"{perf_ns['sfdr_db']:.1f} dB", "89 dB"),
    ]
    table = axs[1, 2].table(
        cellText=[[r[0], r[1], r[2]] for r in rows],
        colLabels=["Metric", "This model", "Paper (measured)"],
        cellLoc="center", loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.6)
    axs[1, 2].set_title("Performance Summary")

    fig.suptitle("EF NS-SAR ADC Mathematical Model  (Li et al., JSSC 2018)", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = out_dir / "ns_sar_ef_model_results.png"
    fig.savefig(out_path, dpi=150)
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
