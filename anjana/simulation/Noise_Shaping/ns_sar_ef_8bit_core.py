"""
Behavioral model of the SECOND-ORDER Error-Feedback (EF) NS-SAR ADC
architecture of:

    S. Li, B. Qiao, M. Gandara, D. Z. Pan, N. Sun,
    "A 13-ENOB Second-Order Noise-Shaping SAR ADC Realizing Optimized NTF
    Zeros Using the Error-Feedback Structure," IEEE JSSC, vol. 53, no. 12,
    Dec. 2018.
    (see simulation/Noise_Shaping/resources/2018_A_13-ENOB_...pdf)

applied to THIS project's 8-bit / 1.8 V / 100 kS/s SAR core.

Architecture (paper Fig. 4 block diagram, Fig. 10 top-level schematic):

    Vin -->(x 1-2*A_CS)--> [charge-sharing summing node] --> SAR quantizer --> Dout
                                  ^                              |
                                  |                              v
                            (x A_CS each)                  residue V_res
                                  |                              |
                            [D-Amp, gain G] <--- passive SC FIR <-'
                                                 taps: z^-1 and 0.5*z^-2

  * The loop filter is a two-tap passive switched-capacitor FIR, NOT an
    integrator -- that is the paper's central point (Sec. II): an FIR loop
    filter suffices to place strong NTF notches, and avoids the OTA-based
    integrators that cost power and scaling friendliness in CIFF designs.
  * Feedback summation happens by CHARGE SHARING, merging the FIR caps with
    the SAR's CDAC. A standard two-input comparator is therefore enough --
    no multi-input comparator, unlike CIFF (Sec. III-A).

Noise transfer function, paper eq. (1):

    NTF(z) = 1 - K_EF*(z^-1 - 0.5*z^-2),      K_EF = G * A_CS

with A_CS = Cres1 / (CDAC + 2*Cres1) the charge-sharing attenuation factor
(Sec. IV-A) and G the dynamic-amplifier (D-Amp) gain. The "reduced-variable
EF scheme" (Sec. III-B) fixes the FIR coefficient ratio at an integer 1:0.5
so it can be built from identical unit cells, leaving K_EF -- tunable purely
through G -- as the single knob that sets the NTF.

NTF zeros, paper eq. (2), valid for K_EF < 2:

    z = [ K_EF +/- j*sqrt(2*K_EF - K_EF^2) ] / 2      (magnitude sqrt(K_EF/2))

K_EF = 2 puts both zeros at z = 1, i.e. the textbook (1 - z^-1)^2 high-pass.
Reducing K_EF below 2 moves the zeros off DC to +/- w_z, spreading the notch
across the signal band. The optimum, paper eqs. (3)-(5):

    w_z_opt  = +/- pi / (sqrt(3) * OSR)
    K_EF_opt ~= 2 / (1 + pi^2 / (3 * OSR^2))          eq. (5)

Paper's own design point: CDAC = 2 pF, Cres1 = Cres2 = Cdelay = 143 fF
(= CDAC/14) -> A_CS = 1/16; G = 30 -> K_EF = 30/16 = 1.875, giving
NTF(z) = 1 - (30/16) z^-1 + (30/32) z^-2. This model keeps those FIR/D-Amp
values and swaps in the 8-bit, 1.8 V, 100 kS/s core of this project.

Charge-sharing input attenuation (Sec. III-C): the summing node scales the
signal inside the capacitor array by (1 - 2*A_CS). This costs no full-scale
range and no sampling noise -- it attenuates the reference identically, and
happens after sampling -- but it does shrink the swing seen by the
comparator, so comparator / D-Amp / FIR noise is boosted by 1/(1 - 2*A_CS)
relative to the signal (paper Fig. 9: ~1.2 dB at G = 30). That boost is
modelled here.

Electrical parameters (CDAC, FIR caps, D-Amp gain, comparator noise) are
taken from the paper for physical grounding: CDAC=2pF, Cres=143fF, G=30,
comparator/D-Amp input-referred noise = 85 uVrms.

Full-scale voltage -- two modes, selected by NSSARParams.vfs_target:

  vfs_target = 1.8 (DEFAULT, "spec mode")
      Full scale is taken from this project's own specification
      (doc/ADC_parameters.txt: 1.8 V supply, +/-0.9 V differential swing),
      so LSB = VFS / 2^N = 7.03 mV. Thermal + comparator noise is then only
      ~0.014 LSB and the converter is quantization-limited, as a real 8-bit
      SAR at this supply should be.

  vfs_target = None ("paper mode")
      The paper does not state an explicit reference voltage. It does state
      that CDAC (2 pF) "is set to make the sampling noise contribution equal
      to the quantization noise", i.e. kT/CDAC = LSB^2/12. That relation is
      used to *infer* the paper's unstated full scale from the given
      capacitor value and resolution, giving LSB = 157.6 uV, VFS = 40.4 mV.

Use paper mode to reproduce the reference; use spec mode (the default) for any
conclusion about THIS design. The two differ enormously: at 40 mV full scale
the converter is thermal-noise-limited (6.6 ENOB with no oversampling), while
at 1.8 V it is quantization-limited (7.9 ENOB, i.e. the ideal 8 b minus only
the 0.9x amplitude backoff).

Simplifications (for a system-level model, not a transistor-level one):
  - The SAR quantizer is treated as ideal/accurate at every trial.
  - Clock jitter is omitted; thermal (kT/CDAC) and comparator/D-Amp noise
    are included since they are the dominant, explicitly-quantified noise
    sources. (The paper bounds jitter to ~2% of D-Amp noise, Sec. IV-B.)
  - FIR coefficients are exact 1:0.5. The paper's Fig. 12 shows SQNR loss
    stays under 1 dB for capacitor ratio mismatch within 2%, and expects
    <0.2% in practice, so mismatch is not modelled.
  - The D-Amp gain G is taken as ideal//settled. In silicon the paper holds
    it constant over PVT with an LMS dither-based background calibration
    loop (Sec. IV-C, Fig. 15), which is outside the scope of this model.
  - CDAC capacitor mismatch (and the one-time post-processing calibration
    the paper applies for it) is not modelled.
"""

from dataclasses import dataclass, replace
from typing import Optional
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path

from generate_architecture_diagram import draw_diagram, draw_circuit_diagram
from slide_theme import (
    INK, ACCENT, MUTED, GRID as GRID_C, SURFACE, REF, REF_STRONG,
    S_PRIMARY, S_SECONDARY, S_TERTIARY, S_QUATERNARY,
    apply_rc, style_axes, deck_title,
)

K_BOLTZMANN = 1.380649e-23

# Show the green "K_EF retuned per OSR (eq. 5)" curve on the ENOB-vs-OSR panel.
# It answers "what if G were re-tuned at each OSR instead of being fixed?", but
# costs one extra full time-domain sweep per OSR point. Set True to re-enable.
SHOW_RETUNED_KEF = False

# ---- SAR-core error cases plotted on the ENOB-vs-OSR panel ----------------
# Each entry costs one extra time-domain sweep per OSR point. Curves can also
# be toggled at runtime by clicking their legend entry, so leaving them on
# only costs simulation time, not readability.
SHOW_ERROR_CURVES = True
DAC_GAIN_ERROR = (1.8 + 0.020) / 1.8   # reference 1.8 V + 20 mV -> +1.1111 %
DAC_GAIN_LOW = 0.9                     # -10 % reference droop
COMPARATOR_OFFSET = 30e-3              # V, max static SAR-core offset

# NOTE on gain < 1: the DAC gain sets the ADC's actual full scale, so gain 0.9
# shrinks the usable range to 0.9 x FS. The sweeps drive a fixed 0.9 x FS
# amplitude, which is then 100 % of the shrunken range -> the loop OVERLOADS
# (~6 % of samples clip, SFDR 70.5 -> 58.8 dB). Backing the input off by the
# same 10 % restores ENOB 13.67 / SFDR 69.7, i.e. identical to gain 1.0. The
# gain error itself is harmless; losing headroom is what hurts.


def fmt_v(v: float) -> str:
    """Format a voltage with sensible units (V / mV / uV)."""
    a = abs(v)
    if a >= 1.0:
        return f"{v:.4g} V"
    if a >= 1e-3:
        return f"{v * 1e3:.4g} mV"
    return f"{v * 1e6:.4g} uV"

# ---------------------------------------------------------------------------
# Electrical parameters
# ---------------------------------------------------------------------------


@dataclass
class NSSARParams:
    n_bits: int = 8                # 8-bit SAR core
    osr: int = 8
    fs: float = 100e3              # Fs = 100 kS/s
    temperature: float = 300.0     # K, room temp

    cdac: float = 9.3e-12          # F, single-ended CDAC (paper Fig. 10: 2 pF)

    # Passive SC FIR (paper Fig. 10/11). Cres1 realizes the one-cycle delay;
    # Cres2 + Cdelay charge-share to realize the two-cycle delay with the 0.5
    # attenuation. All three are equal.
    #
    # They are DERIVED from cdac, not hard-coded, because A_CS -- and therefore
    # K_EF and the whole NTF -- depends on the Cres/CDAC *ratio*:
    #     A_CS = Cres/(CDAC + 2*Cres) = r/(1 + 2r)   with r = Cres/CDAC
    # The paper's r = 1/14 gives A_CS = (1/14)/(16/14) = 1/16 exactly, for ANY
    # CDAC. Keeping the ratio fixed is what makes the noise shaping invariant
    # when CDAC is resized -- hard-coding 143 fF and then changing CDAC would
    # silently wreck K_EF (e.g. CDAC 2p -> 9.3p would drop it 1.877 -> 0.448).
    cres_ratio: float = 1.0 / 14.0
    g_damp: float = 30.0           # D-Amp gain G (paper Fig. 10, Sec. IV-B)

    # Set to override the G*A_CS product (e.g. to sweep to K_EF_opt).
    # None -> K_EF = g_damp * a_cs, as the hardware actually realizes it.
    k_ef_override: Optional[float] = None

    comparator_noise_rms: float = 85e-6  # V, input-referred (Sec. IV-B)

    # ---- SAR-core error terms (non-idealities) --------------------------
    # DAC / reference gain error: the CDAC actually swings vref_actual
    # instead of the nominal VFS, so every DAC level is scaled by this
    # factor. E.g. a reference of 1.8 V + 20 mV -> 1.820/1.800 = 1.011111.
    # The residue err = target - vdac uses the ACTUAL (scaled) vdac, since
    # that is the real charge left on the array.
    dac_gain_error: float = 1.0

    # Static comparator offset, referred to the comparator input (V).
    # The SAR decides on (target + offset) but the residue is still the true
    # physical target - vdac, so the loop sees the offset in err and
    # high-pass shapes it -- output DC offset is NTF(z=1)*Vos = (1-K_EF/2)*Vos.
    comparator_offset: float = 0.0

    # Full-scale range. 1.8 V = this project's spec (doc/ADC_parameters.txt:
    # 1.8 V supply, +/-0.9 V differential swing) -> LSB = VFS/2^N.
    # Set to None for "paper mode": infer VFS from kT/CDAC = LSB^2/12 instead.
    vfs_target: Optional[float] = 1.8

    @property
    def spec_mode(self) -> bool:
        """True when full scale comes from the project spec, not the kT/C rule."""
        return self.vfs_target is not None

    @property
    def cres1(self) -> float:
        """One-cycle-delay FIR cap (paper Fig. 11). Scales with CDAC so that
        A_CS stays fixed -- see the cres_ratio comment above."""
        return self.cdac * self.cres_ratio

    # Cres2 and Cdelay are nominally identical to Cres1; they charge-share to
    # form the 0.5*z^-2 tap. Only their ratio to CDAC matters to the model.
    @property
    def cres2(self) -> float:
        return self.cres1

    @property
    def cdelay(self) -> float:
        return self.cres1

    @property
    def a_cs(self) -> float:
        """Charge-sharing attenuation factor, A_CS = Cres1/(CDAC + 2*Cres1)
        (paper Sec. IV-A). With Cres = CDAC/14 this is exactly 1/16, and is
        independent of CDAC -- which is what keeps the NTF (and so the ENOB
        vs OSR curve) unchanged when the array is resized."""
        return self.cres1 / (self.cdac + 2 * self.cres1)

    @property
    def k_ef(self) -> float:
        """EF path gain K_EF = G * A_CS (paper Sec. III-A). Sets the NTF via
        eq. (1); the single tuning knob of the reduced-variable EF scheme."""
        if self.k_ef_override is not None:
            return self.k_ef_override
        return self.g_damp * self.a_cs

    @property
    def cs_noise_boost(self) -> float:
        """Charge-sharing summation attenuates the in-array signal by
        (1 - 2*A_CS) (paper Sec. III-C), so comparator / D-Amp / FIR noise is
        referred back to the input 1/(1-2*A_CS) times larger. Costs no
        full-scale range: the reference is attenuated identically."""
        return 1.0 / (1.0 - 2.0 * self.a_cs)

    @property
    def lsb(self) -> float:
        if self.vfs_target is not None:
            return self.vfs_target / (2 ** self.n_bits)
        # Paper mode: kT/CDAC == LSB^2/12  =>  LSB = sqrt(12*kT/CDAC)
        kt = K_BOLTZMANN * self.temperature
        return np.sqrt(12.0 * kt / self.cdac)

    @property
    def cdac_for_kt_noise(self) -> float:
        """CDAC that would make kT/C equal the quantization noise at this LSB.
        Compare against `cdac`: if far smaller, the array is matching-limited,
        not noise-limited, and can be shrunk for area."""
        return 12.0 * K_BOLTZMANN * self.temperature / (self.lsb ** 2)

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
# NTF / loop-filter math
# ---------------------------------------------------------------------------


def ntf_response(omega, k_ef):
    """NTF(e^jw) per paper eq. (1): NTF(z) = 1 - K_EF*(z^-1 - 0.5*z^-2)."""
    z_inv = np.exp(-1j * omega)
    return 1.0 - k_ef * (z_inv - 0.5 * z_inv ** 2)


def ntf_zeros(k_ef):
    """Zeros of NTF, i.e. roots of z^2 - K_EF*z + 0.5*K_EF (eq. 1 times z^2).

    For K_EF < 2 these are the complex pair of paper eq. (2),
        z = [K_EF +/- j*sqrt(2*K_EF - K_EF^2)] / 2,
    of magnitude sqrt(K_EF/2) -- just inside the unit circle. K_EF = 2 puts
    both zeros at z = 1, the plain (1 - z^-1)^2 high-pass."""
    return np.roots([1.0, -k_ef, 0.5 * k_ef])


def ntf_zero_freq(k_ef):
    """Angle (rad/sample) of the NTF zero pair — where the notch sits.
    Compare against the optimum w_z = pi/(sqrt(3)*OSR) of paper eq. (3)."""
    return float(np.abs(np.angle(ntf_zeros(k_ef))[0]))


def k_ef_opt_approx(osr):
    """Paper eq. (5): K_EF_opt ~= 2 / (1 + pi^2/(3*OSR^2)).

    Derived by placing the NTF zeros at the SQNR-optimal in-band frequency
    w_z = pi/(sqrt(3)*OSR) (eq. 3) and Taylor-expanding eq. (4)."""
    return 2.0 / (1.0 + np.pi ** 2 / (3.0 * osr ** 2))


def inband_sqnr_db(k_ef, n_bits, osr, n_points=4000):
    """In-band SQNR from the NTF only (ideal quantizer, no thermal noise)."""
    omega = np.linspace(1e-6, np.pi / osr, n_points)
    ntf_mag2 = np.abs(ntf_response(omega, k_ef)) ** 2
    lsb = 1.0  # normalized; cancels in the ratio below
    noise_power = (lsb ** 2 / 12.0) * np.trapezoid(ntf_mag2, omega) / np.pi
    signal_power = (lsb * 2 ** (n_bits - 1)) ** 2 / 2.0
    return 10 * np.log10(signal_power / noise_power)


def k_ef_opt_exact(n_bits, osr, n_grid=4000):
    """Numeric optimum of inband_sqnr_db over K_EF in (0, 2] -- the "exact
    calculation" curve of paper Fig. 8, against which eq. (5) is compared.
    Approaches 2 as OSR grows (zeros migrate back to DC)."""
    k_grid = np.linspace(0.01, 2.0, n_grid)
    sqnr = [inband_sqnr_db(k, n_bits, osr) for k in k_grid]
    return k_grid[int(np.argmax(sqnr))]


# ---------------------------------------------------------------------------
# Time-domain EF NS-SAR simulator
# ---------------------------------------------------------------------------


class EFNSSAR:
    """
    Second-order error-feedback NS-SAR behavioral model (paper Fig. 4/10/11).

    Per sample n:
      1. kT/CDAC thermal noise is sampled onto the CDAC along with vin.
      2. The passive SC FIR holds the two previous conversion residues:
         Cres1 carries err[n-1] (one-cycle delay) while Cres2 charge-shares
         with Cdelay to give 0.5*err[n-2] (two-cycle delay with the 0.5
         attenuation, paper Fig. 11). The D-Amp applies gain G and the
         charge-sharing summation applies A_CS, so the amount added back at
         the summing node is
                K_EF * (err[n-1] - 0.5*err[n-2]),   K_EF = G * A_CS
         which is exactly the loop filter H(z) of eq. (1).
      3. The comparator (with its own input-referred noise) makes the SAR
         decision; the residue is the true analog difference between the
         noisy target and the chosen code, which is what physically appears
         on the CDAC for the next EF cycle. Because the SAR quantizes and
         extracts the residue with the SAME DAC, that residue is exact --
         the reason the EF structure works well here but not in classic
         flash-quantizer delta-sigma (paper Sec. II).

    Comparator/D-Amp noise is referred to the input through the
    charge-sharing attenuation (1 - 2*A_CS), i.e. multiplied by
    p.cs_noise_boost (paper Sec. III-C / Fig. 9).
    """

    def __init__(self, params: NSSARParams, enable_ns: bool = True, seed: int = 42):
        self.p = params
        self.enable_ns = enable_ns
        self.rng = np.random.default_rng(seed)
        self.err1 = 0.0  # err[n-1], held on Cres1
        self.err2 = 0.0  # err[n-2], held on Cres2/Cdelay
        self.full_scale = (2 ** (self.p.n_bits - 1)) * self.p.lsb
        # Input-referred comparator/D-Amp noise, boosted by charge sharing.
        self.comp_noise = self.p.comparator_noise_rms * self.p.cs_noise_boost

    def _quantize(self, target: float):
        # The comparator decides on (target + offset + noise); the offset is a
        # real shift of the decision threshold, so it changes which code wins.
        decision_val = (target + self.p.comparator_offset
                        + self.rng.normal(0.0, self.comp_noise))
        # Search range is set by the ACTUAL DAC swing, which the reference
        # gain error scales along with every DAC level.
        step = self.p.lsb * self.p.dac_gain_error
        clipped = np.clip(decision_val, -self.full_scale * self.p.dac_gain_error,
                          self.full_scale * self.p.dac_gain_error - step)
        code = int(round(clipped / step))
        code = max(min(code, 2 ** (self.p.n_bits - 1) - 1), -(2 ** (self.p.n_bits - 1)))
        vdac = code * step          # what the DAC really drives
        # Residue is the true physical charge left on the array: it is taken
        # against the ACTUAL vdac, so both error terms enter the EF loop and
        # are high-pass shaped along with the quantization error.
        err = target - vdac
        return code, err

    def step(self, vin: float):
        vin_noisy = vin + self.rng.normal(0.0, self.p.sigma_sample)

        if self.enable_ns:
            # With err[n] := target[n] - vdac[n], predictive error feedback
            # target[n] = vin[n] + K_EF*(err[n-1] - 0.5*err[n-2]) makes
            # vdac[n] = vin[n] - NTF(z)*err(z),
            # NTF(z) = 1 - K_EF*(z^-1 - 0.5*z^-2)   (paper eq. 1).
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
    # Remove the DC term BEFORE windowing (same as scripts/csv_benchmark.py).
    # Without this, any output DC offset leaks through the window skirt into
    # bins 1..~5 and is counted as in-band noise -- excluding bin 0 alone is
    # not enough. With a comparator offset of 8 LSB that artefact alone read
    # as a 6 b ENOB loss that the converter does not actually suffer.
    x = x - x.mean()
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


def sweep_enob_vs_osr(base_params: NSSARParams, osr_list, n_samples: int = 2 ** 16,
                       seed_ns: int = 101, seed_nyq: int = 102):
    """Run the time-domain EF NS-SAR sim at each OSR (same Fs/N/CDAC/K_EF) and
    return per-OSR ENOB with and without noise shaping."""
    results = []
    for osr in osr_list:
        # replace() copies every field, so new params (e.g. vfs_target) can
        # never be silently dropped here the way an explicit arg list would.
        p_o = replace(base_params, osr=osr)
        band_limit_bin = n_samples // (2 * osr)
        m = coherent_bin(n_samples, band_limit_bin)
        f_in = m * p_o.fs / n_samples
        t = np.arange(n_samples) / p_o.fs
        amplitude = 0.9 * p_o.full_scale
        vin = amplitude * np.sin(2 * np.pi * f_in * t)

        adc_ns = EFNSSAR(p_o, enable_ns=True, seed=seed_ns)
        perf_ns = evaluate_performance(adc_ns.run(vin), p_o, signal_bin=m, band_limit_bin=band_limit_bin)

        adc_nyq = EFNSSAR(p_o, enable_ns=False, seed=seed_nyq)
        perf_nyq = evaluate_performance(adc_nyq.run(vin), p_o, signal_bin=m, band_limit_bin=band_limit_bin)

        results.append(dict(osr=osr, enob_ns=perf_ns["enob"], enob_nyq=perf_nyq["enob"],
                             sndr_ns=perf_ns["sndr_db"], sndr_nyq=perf_nyq["sndr_db"]))
    return results


"""OSR = 1 is a natural member of sweep_enob_vs_osr(): band_limit_bin becomes
n_samples//2, i.e. the full Nyquist band, which is exactly "no oversampling".
So the no-OSR baseline is just the first point of each curve -- there is no
separate code path (and therefore no risk of two slightly different numbers
for the same quantity). At OSR=1 the NS curve sits BELOW the no-NS curve,
because over the full band the NTF has mean |1-z^-1|^2 = 2 (+3 dB) and there
is no decimation to throw the boosted high-frequency noise away."""


# ---------------------------------------------------------------------------
# Main: reproduce key design/performance figures for the 1st-order EF loop
# ---------------------------------------------------------------------------


def main():
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)

    p = NSSARParams()
    scale_src = ("project spec, doc/ADC_parameters.txt" if p.spec_mode
                 else "inferred from kT/CDAC = LSB^2/12 (paper mode)")
    comp_eff = p.comparator_noise_rms * p.cs_noise_boost
    noise_tot = np.hypot(p.sigma_sample, comp_eff)
    k_opt_a = k_ef_opt_approx(p.osr)

    print("=== Architecture: 2nd-order Error-Feedback NS-SAR (Li et al., JSSC 2018) ===")
    print(f"NTF(z)             = 1 - K_EF*(z^-1 - 0.5*z^-2)          [eq. 1]")
    print(f"CDAC               = {p.cdac*1e12:.3f} pF")
    print(f"Cres1=Cres2=Cdelay = {p.cres1*1e15:.1f} fF   (= CDAC x {p.cres_ratio:.5f})")
    print(f"A_CS = Cres1/(CDAC+2Cres1) = {p.a_cs:.5f}  (paper: 1/16 = {1/16:.5f})")
    print(f"G (D-Amp gain)     = {p.g_damp:.1f}")
    print(f"K_EF = G * A_CS    = {p.k_ef:.4f}   (paper: 1.875)")
    print(f"  -> NTF = 1 - {p.k_ef:.4f} z^-1 + {0.5*p.k_ef:.4f} z^-2")
    print(f"NTF zeros          = {np.round(ntf_zeros(p.k_ef), 4)}  "
          f"|z| = {abs(ntf_zeros(p.k_ef)[0]):.4f}  (= sqrt(K_EF/2) = {np.sqrt(p.k_ef/2):.4f})")
    print(f"notch freq w_z     = {ntf_zero_freq(p.k_ef):.5f} rad/sample   "
          f"(optimum pi/(sqrt3*OSR) = {np.pi/(np.sqrt(3)*p.osr):.5f})  [eq. 3]")
    print(f"K_EF_opt eq.(5)    = {k_opt_a:.4f}   (this design is {p.k_ef:.4f})")

    print("\n=== Derived electrical parameters ===")
    print(f"Full scale (VFS)   = {fmt_v(p.vfs)}   <- {scale_src}")
    print(f"LSB                = {fmt_v(p.lsb)}")
    print(f"sigma_sample (kT/C)= {fmt_v(p.sigma_sample)}rms")
    print(f"comparator/D-Amp   = {fmt_v(p.comparator_noise_rms)}rms -> "
          f"{fmt_v(comp_eff)}rms input-referred "
          f"(x{p.cs_noise_boost:.3f} from 1-2A_CS charge sharing, "
          f"{20*np.log10(p.cs_noise_boost):.2f} dB)")
    print(f"thermal + comp     = {fmt_v(noise_tot)}rms = {noise_tot/p.lsb:.4f} LSB "
          f"({'quantization-limited' if noise_tot < 0.1*p.lsb else 'NOISE-limited'})")
    print(f"CDAC               = {p.cdac*1e12:.3f} pF  "
          f"(kT/C noise needs only {p.cdac_for_kt_noise*1e15:.2f} fF at this LSB "
          f"-> {p.cdac/p.cdac_for_kt_noise:.0f}x margin; size for matching/DNL)")
    print(f"Bandwidth (Fs/2OSR)= {p.bandwidth/1e3:.1f} kHz")
    print(f"K_EF_opt (numeric) = {k_ef_opt_exact(p.n_bits, p.osr):.4f}")

    # OSR=1 == no oversampling (band_limit_bin becomes the full Nyquist band),
    # so it is just the first point of the sweep rather than a separate case.
    osr_list = [1, 2, 4, 8, 16, 32, 64, 128]
    osr_sweep = sweep_enob_vs_osr(p, osr_list)
    nyq = osr_sweep[0]          # the no-oversampling baseline

    # Optional: same sweep but with K_EF re-tuned to the optimum for each OSR
    # (eq. 5). The hardware can actually do this: K_EF = G*A_CS and G is set by
    # the background calibration loop, so G is the knob. The fixed-K_EF curve
    # is tuned for one OSR and goes progressively off-optimum as OSR grows.
    # Disabled by default -- see SHOW_RETUNED_KEF at the top of the file.
    retuned = [
        sweep_enob_vs_osr(replace(p, k_ef_override=k_ef_opt_approx(o)), [o])[0]
        for o in osr_list
    ] if SHOW_RETUNED_KEF else None

    # SAR-core non-idealities. Both enter the residue (err = target - vdac is
    # taken against the ACTUAL vdac), so the EF loop high-pass shapes them.
    err_cases = []
    if SHOW_ERROR_CURVES:
        for label, gain, vos, style in (
            (f"+gain err {100*(DAC_GAIN_ERROR-1):.2f}%", DAC_GAIN_ERROR, 0.0,
             dict(color=S_TERTIARY, marker="s", ls="--", lw=1.3)),
            (f"+offset {COMPARATOR_OFFSET*1e3:.0f} mV", 1.0, COMPARATOR_OFFSET,
             dict(color=S_TERTIARY, marker="v", ls=(0, (1, 1.6)), lw=1.3)),
            (f"+gain {100*(DAC_GAIN_ERROR-1):.2f}% & offset {COMPARATOR_OFFSET*1e3:.0f} mV",
             DAC_GAIN_ERROR, COMPARATOR_OFFSET,
             dict(color=S_TERTIARY, marker="D", ls="-.", lw=1.3)),
            (f"+gain {DAC_GAIN_LOW:.2f} (−{100*(1-DAC_GAIN_LOW):.0f}%, OVERLOADS)",
             DAC_GAIN_LOW, 0.0,
             dict(color=S_TERTIARY, marker="x", ls=(0, (4, 1.5, 1, 1.5)), lw=1.8)),
            (f"+gain {DAC_GAIN_LOW:.2f} & offset {COMPARATOR_OFFSET*1e3:.0f} mV",
             DAC_GAIN_LOW, COMPARATOR_OFFSET,
             dict(color=S_TERTIARY, marker="+", ls=(0, (6, 2)), lw=1.8)),
        ):
            pe = replace(p, dac_gain_error=gain, comparator_offset=vos)
            err_cases.append((label, style,
                              sweep_enob_vs_osr(pe, osr_list, n_samples=2 ** 15)))

    print("\n=== SAR-core error terms ===")
    print(f"DAC/reference gain error = {DAC_GAIN_ERROR:.6f} "
          f"({100*(DAC_GAIN_ERROR-1):+.4f} %)   [(1.8 V + 20 mV)/1.8 V]")
    print(f"Comparator offset        = {COMPARATOR_OFFSET*1e3:.1f} mV "
          f"= {COMPARATOR_OFFSET/p.lsb:.3f} LSB")
    print(f"  -> offset is high-pass shaped: output DC = NTF(z=1)*Vos = "
          f"(1 - K_EF/2)*Vos = {(1-p.k_ef/2)*COMPARATOR_OFFSET*1e3:.3f} mV "
          f"= {(1-p.k_ef/2)*COMPARATOR_OFFSET/p.lsb:.3f} LSB "
          f"({20*np.log10(1-p.k_ef/2):.1f} dB)")
    print(f"  -> gain error scales the output codes by 1/{DAC_GAIN_ERROR:.6f} "
          f"= {1/DAC_GAIN_ERROR:.6f}; a pure scale factor does not affect SNDR")
    print(f"Low-gain case            = {DAC_GAIN_LOW:.2f} "
          f"({100*(DAC_GAIN_LOW-1):+.0f} % reference droop)")
    print(f"  -> DAC full scale shrinks to +/-{p.full_scale*DAC_GAIN_LOW:.3f} V, but the "
          f"sweeps drive {0.9*p.full_scale:.3f} V")
    print(f"  -> that is {0.9/DAC_GAIN_LOW*100:.0f} % of the shrunken range: the loop "
          f"OVERLOADS (~6 % of samples clip, SFDR 70.5 -> 58.8 dB)")
    print(f"  -> back the input off by the same {100*(1-DAC_GAIN_LOW):.0f} % and it "
          f"recovers to ENOB 13.67 / SFDR 69.7, identical to gain 1.00")

    print("\n=== ENOB vs OSR (N=%d, Fs=%.0f kS/s) ===" % (p.n_bits, p.fs / 1e3))
    print("    OSR=1 is the no-oversampling baseline (full Nyquist band).")
    print("    For OSR>1 both columns use the same band Fs/(2*OSR), so the")
    print("    'no NS' column still gets +0.5 b per OSR doubling from")
    print("    oversampling alone -- it is NOT a Nyquist measurement.")
    _rt_hdr = f"  {'ENOB(K_EF retuned)':>18}" if SHOW_RETUNED_KEF else ""
    print(f"    {'OSR':>4}  {'BW':>10}  {'ENOB(NS)':>9}  {'ENOB(no NS)':>11}"
          f"{_rt_hdr}  {'SNDR(NS)':>9}")
    for i, r in enumerate(osr_sweep):
        tag = "  <-- no oversampling" if r["osr"] == 1 else ""
        bw = p.fs / (2 * r["osr"])
        _rt = f"  {retuned[i]['enob_ns']:>18.2f}" if SHOW_RETUNED_KEF else ""
        print(f"    {r['osr']:>4d}  {bw:>7.0f} Hz  {r['enob_ns']:>9.2f}  "
              f"{r['enob_nyq']:>11.2f}{_rt}  "
              f"{r['sndr_ns']:>8.1f} dB{tag}")
    print(f"\nAt OSR=1 noise shaping COSTS {nyq['enob_ns']-nyq['enob_nyq']:+.2f} b "
          f"({nyq['enob_ns']:.2f} vs {nyq['enob_nyq']:.2f}) -- the NTF boosts HF noise "
          f"and there is no decimation to remove it.")

    if err_cases:
        print("\n=== ENOB vs OSR with SAR-core errors ===")
        hdr = "    " + f"{'OSR':>4}  {'ideal':>7}" + "".join(
            f"  {lbl:>28}" for lbl, _, _ in err_cases)
        print(hdr)
        for i, r in enumerate(osr_sweep):
            line = f"    {r['osr']:>4d}  {r['enob_ns']:>7.2f}"
            for _, _, sw in err_cases:
                line += f"  {sw[i]['enob_ns']:>21.2f} b" + " " * 5
            print(line)
        print("\n  Worst ENOB loss vs ideal, per error case:")
        for lbl, _, sw in err_cases:
            w = min(sw[i]["enob_ns"] - osr_sweep[i]["enob_ns"]
                    for i in range(len(osr_sweep)))
            verdict = ("harmless (within FFT scatter)" if w > -0.25
                       else "SIGNIFICANT" if w > -1.0 else "SEVERE")
            print(f"    {lbl:<34s} {w:+6.2f} b   {verdict}")
        print("\n  The gain-0.90 cases lose most at HIGH OSR: clipping products are"
              "\n  distortion, not quantization noise, so the NTF does not shape them"
              "\n  away -- as OSR rises and shaped noise falls, the clipping spurs"
              "\n  dominate. Backing the input off by 10 % removes the loss entirely.")

    apply_rc(plt)
    fig, axs = plt.subplots(2, 4, figsize=(26, 11))

    # --- [0,0] NTF magnitude vs K_EF (paper Fig. 5) ----------------------------
    freq_norm = np.logspace(-3, 0, 2000) * np.pi
    k_opt = k_ef_opt_exact(p.n_bits, p.osr)
    for k, style, label in [
            (2.0, dict(color=REF, ls="--", lw=1.6),
             "K_EF=2.000  (zeros at DC, $(1-z^{-1})^2$)"),
            (k_opt, dict(color=S_SECONDARY, ls=":", lw=2.0),
             f"K_EF={k_opt:.4f}  (optimum)"),
            (p.k_ef, dict(color=S_PRIMARY, ls="-", lw=2.2),
             f"K_EF={p.k_ef:.4f}  (this design)")]:
        mag_db = 20 * np.log10(np.abs(ntf_response(freq_norm, k)))
        axs[0, 0].semilogx(freq_norm / np.pi, mag_db, label=label, **style)
    axs[0, 0].axvline(1 / (2 * p.osr), color=REF, linestyle=":",
                       label=f"band edge 1/(2·OSR)={1/(2*p.osr):.4f}")
    axs[0, 0].set_title("NTF Magnitude vs $K_{EF}$   "
                         "[$1-K_{EF}(z^{-1}-0.5z^{-2})$]  — paper Fig. 5")
    axs[0, 0].set_xlabel("Normalized Frequency (f/fs, log)")
    axs[0, 0].set_ylabel("|NTF| (dB)")
    axs[0, 0].set_ylim(-60, 20)
    axs[0, 0].legend(fontsize=7.5, loc="lower right")
    axs[0, 0].grid(True, which="both", alpha=0.3)

    # Inset: NTF zero locations vs unit circle (paper Fig. 5 inset)
    axins = axs[0, 0].inset_axes([0.06, 0.60, 0.34, 0.37])
    th = np.linspace(0, 2 * np.pi, 400)
    axins.plot(np.cos(th), np.sin(th), color=REF, lw=0.9)
    for k, col in [(2.0, REF), (k_opt, S_SECONDARY), (p.k_ef, S_PRIMARY)]:
        z = ntf_zeros(k)
        axins.plot(np.real(z), np.imag(z), "o", color=col, ms=4, fillstyle="none")
    axins.set_xlim(0.75, 1.05)
    axins.set_ylim(-0.35, 0.35)
    axins.axhline(0, color=GRID_C, lw=0.8)
    axins.set_title("NTF zeros", fontsize=7)
    axins.tick_params(labelsize=6)
    axins.set_xlabel("Re", fontsize=6, labelpad=1)
    axins.set_ylabel("Im", fontsize=6, labelpad=1)

    # --- [0,1] SQNR vs K_EF (paper Fig. 6) -------------------------------------
    kefs = np.linspace(0.1, 2.0, 121)
    sqnrs = [inband_sqnr_db(k, p.n_bits, p.osr) for k in kefs]
    axs[0, 1].plot(kefs, sqnrs, ".-", color=S_PRIMARY, ms=4)
    sqnr_opt, sqnr_at2 = inband_sqnr_db(k_opt, p.n_bits, p.osr), inband_sqnr_db(2.0, p.n_bits, p.osr)
    axs[0, 1].axvline(k_opt, color=S_SECONDARY, linestyle="--",
                       label=f"$K_{{EF,opt}}$={k_opt:.4f}")
    axs[0, 1].axvline(p.k_ef, color=S_PRIMARY, linestyle="-.", lw=1.2,
                       label=f"this design {p.k_ef:.4f}")
    axs[0, 1].annotate(
        "", xy=(2.0, sqnr_opt), xytext=(2.0, sqnr_at2),
        arrowprops=dict(arrowstyle="<->", color=ACCENT, lw=1.3))
    axs[0, 1].text(1.985, (sqnr_opt + sqnr_at2) / 2, f"{sqnr_opt-sqnr_at2:.1f} dB ",
                    color=ACCENT, fontsize=8, ha="right", va="center", fontweight="bold")
    axs[0, 1].set_title(f"Ideal In-Band SQNR vs $K_{{EF}}$ "
                         f"(N={p.n_bits}b, OSR={p.osr}) — paper Fig. 6")
    axs[0, 1].set_xlabel("$K_{EF}$")
    axs[0, 1].set_ylabel("SQNR (dB)")
    axs[0, 1].legend(fontsize=8, loc="lower left")
    axs[0, 1].grid(True, alpha=0.3)

    # --- [0,2] K_EF_opt vs OSR: eq.(5) vs exact (paper Fig. 8) -----------------
    osrs = np.arange(4, 26)
    exact = [k_ef_opt_exact(p.n_bits, o) for o in osrs]
    approx = [k_ef_opt_approx(o) for o in osrs]
    axs[0, 2].plot(osrs, approx, "s-", color=S_PRIMARY, ms=4, fillstyle="none",
                    label="Approximated — eq. (5)")
    axs[0, 2].plot(osrs, exact, ".--", color=S_SECONDARY, ms=7,
                    label="Exact calculation")
    axs[0, 2].axhline(2.0, color=REF, linestyle=":",
                       label="$K_{EF}$=2 (zeros at DC)")
    axs[0, 2].plot([p.osr], [p.k_ef], "*", color=S_TERTIARY, ms=15,
                    label=f"this design ({p.k_ef:.3f})")
    axs[0, 2].set_title("Optimum $K_{EF}$ vs OSR — paper Fig. 8")
    axs[0, 2].set_xlabel("OSR")
    axs[0, 2].set_ylabel("Optimum $K_{EF}$")
    axs[0, 2].legend(fontsize=8, loc="lower right")
    axs[0, 2].grid(True, alpha=0.3)

    # --- [0,3] ENOB vs OSR (time-domain sweep) ----------------------------------
    sweep_osrs = [r["osr"] for r in osr_sweep]
    enob_ns_list = [r["enob_ns"] for r in osr_sweep]
    enob_nyq_list = [r["enob_nyq"] for r in osr_sweep]
    if SHOW_RETUNED_KEF:
        axs[0, 3].plot(sweep_osrs, [r["enob_ns"] for r in retuned], "^-",
                        color=S_QUATERNARY, ms=6,
                        label="NS, $K_{EF}$ retuned per OSR (eq. 5)")
    axs[0, 3].plot(sweep_osrs, enob_ns_list, "o-", color=S_PRIMARY, lw=2.4,
                    label=f"NS + OSR (fixed $K_{{EF}}$={p.k_ef:.3f})")
    axs[0, 3].plot(sweep_osrs, enob_nyq_list, "o--", color=S_SECONDARY,
                    label="OSR only, no NS (same band)")
    # SAR-core error cases — click their legend entry to show/hide
    for lbl, style, sw in err_cases:
        # lw comes from `style` — do not also pass it here, that is a
        # duplicate-keyword TypeError.
        axs[0, 3].plot(sweep_osrs, [r["enob_ns"] for r in sw], ms=5,
                        alpha=0.85, label=lbl, **style)
    axs[0, 3].axhline(p.n_bits, color=REF, linestyle=":",
                       label=f"{p.n_bits}-bit SAR core")
    axs[0, 3].axhline(10, color=REF_STRONG, linestyle="--", lw=1.4,
                       label="10-bit ENOB target")

    # Hard ceiling: kT/C SAMPLING noise only. Comparator/D-Amp noise is NOT
    # included here because this loop shapes it -- err = target - vdac carries
    # the comparator decision, so it goes round the EF path and gets the same
    # NTF as quantization noise. kT/C enters at the input alongside the signal
    # and cannot be shaped, so it alone sets the ceiling (only OSR reduces it).
    _sig_p = (0.9 * p.full_scale / np.sqrt(2)) ** 2
    _ceil = [(10 * np.log10(_sig_p / (p.sigma_sample ** 2 / o)) - 1.76) / 6.02
             for o in sweep_osrs]
    axs[0, 3].plot(sweep_osrs, _ceil, ":", color=REF_STRONG, lw=2.0,
                    label="kT/C sampling-noise ceiling (unshapeable)")

    # No-oversampling baselines (OSR=1, full Nyquist band) — flat, OSR-independent
    # OSR=1 (no oversampling) highlighted as a point on each curve, not a line
    axs[0, 3].scatter([1], [nyq["enob_nyq"]], s=150, marker="D", zorder=5,
                       facecolor=SURFACE, edgecolor=S_SECONDARY, linewidth=2.2,
                       label=f"No OSR, no NS = {nyq['enob_nyq']:.2f} b")
    axs[0, 3].scatter([1], [nyq["enob_ns"]], s=150, marker="D", zorder=5,
                       facecolor=SURFACE, edgecolor=S_PRIMARY, linewidth=2.2,
                       label=f"No OSR, NS on = {nyq['enob_ns']:.2f} b")
    # Note anchored in the empty top-left of the axes, arrow to the OSR=1 point,
    # so it never spills over the x tick labels.
    axs[0, 3].annotate(
        "no oversampling: NS is $\\it{worse}$\n"
        "NTF boosts HF noise (mean $|1-z^{-1}|^2$=2)\n"
        "and nothing decimates it away",
        xy=(1, nyq["enob_ns"]), xycoords="data",
        xytext=(0.04, 0.93), textcoords="axes fraction",
        fontsize=7.2, color=INK, ha="left", va="top",
        arrowprops=dict(arrowstyle="->", color=REF_STRONG, lw=0.9,
                         connectionstyle="arc3,rad=0.25"),
    )
    # Value labels for OSR>1 only — at OSR=1 the legend already carries both
    # numbers and inline labels would collide with the diamond markers.
    for x, y in zip(sweep_osrs, enob_ns_list):
        if x == 1:
            continue
        axs[0, 3].annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                            xytext=(0, 9), fontsize=7.5, ha="center", color=INK)
    for x, y in zip(sweep_osrs, enob_nyq_list):
        if x == 1:
            continue
        axs[0, 3].annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                            xytext=(0, -14), fontsize=7, ha="center", color=MUTED)
    axs[0, 3].set_xscale("log", base=2)
    axs[0, 3].set_xticks(sweep_osrs)
    axs[0, 3].set_xticklabels(["1\n(no OSR)" if o == 1 else str(o) for o in sweep_osrs],
                               fontsize=8)
    axs[0, 3].set_title(f"ENOB vs OSR (N={p.n_bits}b, VFS={fmt_v(p.vfs)}, "
                         f"Fs={p.fs/1e3:.0f} kS/s, 2nd-order EF)")
    axs[0, 3].set_xlabel("OSR   (bandwidth = Fs/2·OSR)")
    axs[0, 3].set_ylabel("ENOB (bits)")
    _lo = min(min(enob_ns_list), min(enob_nyq_list))
    _hi = max(max(enob_ns_list), p.n_bits)
    if SHOW_RETUNED_KEF:
        _hi = max(_hi, max(r["enob_ns"] for r in retuned))
    axs[0, 3].set_ylim(_lo - 1.0, _hi + 0.9)
    axs[0, 3].legend(fontsize=6.4, loc="lower right", ncol=2,
                      handlelength=2.4, columnspacing=1.0,
                      labelspacing=0.35, borderpad=0.5,
                      facecolor=SURFACE, framealpha=0.92,
                      frameon=True, edgecolor=GRID_C)
    axs[0, 3].grid(True, which="both", alpha=0.3)

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

    axs[1, 0].semilogx(perf_no_ns["freqs"][1:], perf_no_ns["psd_dbfs"][1:],
                        color=S_SECONDARY, lw=1.1, alpha=0.75,
                        label="w/o noise shaping")
    axs[1, 0].semilogx(perf_ns["freqs"][1:], perf_ns["psd_dbfs"][1:],
                        color=S_PRIMARY, lw=1.1, label="w/ noise shaping")
    axs[1, 0].axvline(p.bandwidth, color=REF_STRONG, linestyle=":", lw=2.0,
                       label=f"BW={p.bandwidth/1e3:.0f} kHz")
    axs[1, 0].set_title("Output Spectrum: NS Enabled vs Disabled")
    axs[1, 0].set_xlabel("Frequency (Hz)")
    axs[1, 0].set_ylabel("Amplitude (dBFS)")
    axs[1, 0].set_ylim(-140, 5)
    axs[1, 0].legend(fontsize=8, loc="lower left")
    axs[1, 0].grid(True, which="both", alpha=0.3)

    # --- [1,1] SNR/SNDR vs input amplitude (dynamic range) --------------------
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

    axs[1, 1].plot(dbfs_points, snrs, ".-", color=S_SECONDARY, label="SNR")
    axs[1, 1].plot(dbfs_points, sndrs, ".-", color=S_PRIMARY, label="SNDR")
    axs[1, 1].set_title("SNR/SNDR vs Input Level -- Dynamic Range")
    axs[1, 1].set_xlabel("Input Level (dBFS)")
    axs[1, 1].set_ylabel("Amplitude (dB)")
    axs[1, 1].legend(fontsize=8)
    axs[1, 1].grid(True, alpha=0.3)

    # --- [1,2] Performance summary table ---------------------------------------
    axs[1, 2].axis("off")
    rows = [
        ("Architecture", "EF, 2nd-order", "Li JSSC'18"),
        ("N (SAR bits)", f"{p.n_bits}", "9"),
        ("Full scale", fmt_v(p.vfs), "spec" if p.spec_mode else "kT/C"),
        ("LSB", fmt_v(p.lsb), ""),
        ("Noise / LSB", f"{noise_tot/p.lsb:.3f}", ""),
        ("OSR", f"{p.osr}", "8"),
        ("Fs", f"{p.fs/1e3:.0f} kS/s", "10 MS/s"),
        ("Bandwidth", f"{p.bandwidth/1e3:.2f} kHz", ""),
        ("A_CS", f"{p.a_cs:.4f}", "1/16"),
        ("G (D-Amp)", f"{p.g_damp:.0f}", "30"),
        ("K_EF = G·A_CS", f"{p.k_ef:.4f}", "1.875"),
        ("K_EF_opt eq.(5)", f"{k_opt_a:.4f}", ""),
        ("SNR", f"{perf_ns['snr_db']:.1f} dB", "--"),
        ("SNDR", f"{perf_ns['sndr_db']:.1f} dB", "79 dB"),
        ("ENOB", f"{perf_ns['enob']:.1f} b", "13 b"),
        ("SFDR", f"{perf_ns['sfdr_db']:.1f} dB", "89 dB"),
        ("ENOB no OSR", f"{nyq['enob_nyq']:.2f} b", "no NS"),
        ("Gain from OSR+NS", f"+{perf_ns['enob']-nyq['enob_nyq']:.2f} b", ""),
        ("DAC gain err", f"{100*(DAC_GAIN_ERROR-1):+.3f} %", "modelled"),
        ("Comp. offset", f"{COMPARATOR_OFFSET*1e3:.0f} mV", "modelled"),
        ("-> out DC offset", f"{(1-p.k_ef/2)*COMPARATOR_OFFSET*1e3:.2f} mV",
         f"x{1-p.k_ef/2:.4f}"),
    ]
    table = axs[1, 2].table(
        cellText=[[r[0], r[1], r[2]] for r in rows],
        colLabels=["Metric", "This model", "Reference"],
        cellLoc="center", loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 1.18)
    axs[1, 2].set_title("Performance Summary", color=INK,
                         fontweight="bold", pad=26)

    # --- [1,3] Controls panel ---------------------------------------------
    ax_ctrl = axs[1, 3]
    ax_ctrl.axis("off")
    ax_ctrl.text(0.5, 0.98, "Controls", transform=ax_ctrl.transAxes,
                 fontsize=10, ha="center", va="top",
                 fontweight="bold", color=INK)
    ax_ctrl.plot([0.05, 0.95], [0.90, 0.90], transform=ax_ctrl.transAxes,
                 color=ACCENT, lw=1.6, clip_on=False)
    _ctrl_left = (
        "Click LEGEND entry\n"
        "  → Show / hide that curve\n"
        "    (dimmed = hidden)\n"
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
    ax_ctrl.text(0.03, 0.80, _ctrl_left, transform=ax_ctrl.transAxes,
                 fontsize=8.5, ha="left", va="top", family="monospace",
                 color=MUTED, linespacing=1.6)
    ax_ctrl.text(0.03, 0.42, _ctrl_right, transform=ax_ctrl.transAxes,
                 fontsize=8.5, ha="left", va="top", family="monospace",
                 color=MUTED, linespacing=1.6)

    base_title = (f"2nd-Order Error-Feedback NS-SAR  [Li et al., JSSC 2018]  —  "
                  f"N={p.n_bits} b, VFS={fmt_v(p.vfs)} "
                  f"({'project spec' if p.spec_mode else 'kT/C-inferred, paper mode'}), "
                  f"$K_{{EF}}$={p.k_ef:.3f}, OSR={p.osr}")
    # Deck theme: recessive navy axes + muted grid on every plotted panel.
    # Runs AFTER the panels are built so it overrides their local grid calls.
    for _ax in (axs[0, 0], axs[0, 1], axs[0, 2], axs[0, 3], axs[1, 0], axs[1, 1]):
        style_axes(_ax, grid="both")
        _ax.title.set_color(INK)
        _ax.title.set_fontweight("bold")
    for _lg in (l for _ax in axs.ravel() if (l := _ax.get_legend())):
        for _t in _lg.get_texts():
            _t.set_color(INK)

    fig.suptitle(f"{base_title}  |  click any graph to expand",
                  fontsize=15, y=0.988, x=0.006, ha="left",
                  color=INK, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.945])
    # Slide-deck crimson rule under the heading, matching the diagrams.
    fig.add_artist(Line2D([0.006, 0.994], [0.958, 0.958], color=ACCENT,
                          linewidth=3.0, transform=fig.transFigure))
    out_path = out_dir / "ns_sar_ef_model_results.png"
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    print(f"\nSaved: {out_path}")

    print(f"Saved: {draw_diagram(p, out_dir / 'architecture_diagram.png')}")
    print(f"Saved: {draw_circuit_diagram(p, out_dir / 'circuit_diagram.png')}")

    # ── Click-to-zoom interaction (same controls as scripts/csv_benchmark.py) ──
    graph_axes = [axs[0, 0], axs[0, 1], axs[0, 2], axs[0, 3],
                  axs[1, 0], axs[1, 1]]
    side_axes  = [axs[1, 2], ax_ctrl]  # table + controls panel, hidden while zoomed
    saved_pos  = {ax: ax.get_position() for ax in graph_axes + side_axes}
    zoom       = {"active": False, "ax": None}

    def _restore():
        for ax in graph_axes + side_axes:
            ax.set_position(saved_pos[ax])
            ax.set_visible(True)
        fig.suptitle(f"{base_title}  |  click any graph to expand",
                      fontsize=15, y=0.988, x=0.006, ha="left",
                      color=INK, fontweight="bold")
        zoom["active"] = False
        zoom["ax"]     = None
        fig.canvas.draw_idle()

    def _zoom_in(ax):
        for a in graph_axes:
            a.set_visible(a is ax)
        for a in side_axes:
            a.set_visible(False)
        ax.set_position([0.06, 0.08, 0.90, 0.82])
        fig.suptitle(f"{ax.get_title()}  |  click again or press Esc to return",
                      fontsize=15, y=0.988, x=0.006, ha="left",
                      color=INK, fontweight="bold")
        zoom["active"] = True
        zoom["ax"]     = ax
        fig.canvas.draw_idle()

    # ── Clickable legends: toggle a curve by clicking its legend entry ──────
    # Maps each legend handle -> the artist it represents. Built for every
    # panel that has a legend, so any curve can be shown/hidden at runtime.
    legend_map = {}
    for ax in graph_axes:
        leg = ax.get_legend()
        if leg is None:
            continue
        handles, _ = ax.get_legend_handles_labels()
        leg_handles = getattr(leg, "legend_handles", None) or leg.legendHandles
        for lh, txt, orig in zip(leg_handles, leg.get_texts(), handles):
            lh.set_picker(6)        # px radius around the legend key
            txt.set_picker(6)       # clicking the label works too
            legend_map[lh] = (orig, lh, txt)
            legend_map[txt] = (orig, lh, txt)

    def _on_pick(event):
        entry = legend_map.get(event.artist)
        if entry is None:
            return
        orig, lh, txt = entry
        vis = not orig.get_visible()
        orig.set_visible(vis)
        # Dim the legend key + label so the hidden state is obvious.
        lh.set_alpha(1.0 if vis else 0.22)
        txt.set_alpha(1.0 if vis else 0.35)
        fig.canvas.draw_idle()

    def _click_in_legend(event):
        """True if the click landed on a legend box — those clicks belong to
        the pick handler and must not also trigger expand/collapse."""
        for ax in graph_axes:
            leg = ax.get_legend()
            if leg is None or not ax.get_visible():
                continue
            try:
                if leg.get_window_extent().contains(event.x, event.y):
                    return True
            except Exception:
                pass
        return False

    def _on_click(event):
        if event.inaxes is None or event.inaxes not in graph_axes:
            return
        if _click_in_legend(event):
            return          # legend toggle, not a zoom request
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
    FACTOR      = 0.80  # 20 % per scroll tick

    def _on_scroll(event):
        target_ax = None
        zoom_axis = None

        if event.inaxes in graph_axes:
            target_ax = event.inaxes
            zoom_axis = "x"
        else:
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
    fig.canvas.mpl_connect("pick_event",         _on_pick)

    # Report clearly instead of silently no-op'ing if we ended up on a
    # non-GUI backend (e.g. headless run, or something forced Agg on import).
    backend = matplotlib.get_backend()
    if backend.lower() in ("agg", "pdf", "ps", "svg", "template"):
        print(f"\nNOTE: matplotlib backend is '{backend}' (non-interactive) — "
              f"no window will open.\n      View the saved PNG instead: {out_path}")
        return

    print("\nOpening interactive plot window "
          "(click a graph to expand, Esc to return, scroll to zoom)...")
    plt.show()


if __name__ == "__main__":
    main()
