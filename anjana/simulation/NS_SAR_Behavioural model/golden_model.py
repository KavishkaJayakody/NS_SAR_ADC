#!/usr/bin/env python3
"""
golden_model.py -- z-domain reference for the EF NS-SAR.

Run this FIRST. Everything Cadence produces should match it within ~1 dB
with noise disabled. If it doesn't, the bug is in the charge-sharing
network, not in the ADC concept.

    python3 golden_model.py
    python3 golden_model.py --sweep      # SQNR vs K_EF, reproduces Fig. 6
"""

import argparse
import numpy as np


def kef_opt(osr):
    """Optimum EF path gain for a given OSR (eq. 5 of the paper)."""
    return 2.0 / (1.0 + np.pi ** 2 / (3.0 * osr ** 2))


def simulate(nb=9, osr=8, kef=1.875, nfft=8192, mbin=None,
             ampl=0.9, acs=1.0 / 16, vn_rms=0.0, seed=0):
    """
    Time-domain EF NS-SAR model.

    nb     : SAR resolution including redundancy
    kef    : G * A_CS
    acs    : charge-sharing attenuation (sets the 1 - 2*acs signal loss)
    vn_rms : total input-referred thermal noise, in LSB of the SAR
    """
    rng = np.random.default_rng(seed)
    if mbin is None:
        mbin = int(nfft / (2 * osr) * 0.8) | 1        # odd, in band

    n = np.arange(nfft)
    x = ampl * np.sin(2 * np.pi * mbin * n / nfft)

    lsb = 2.0 / (2 ** nb)
    q1 = q2 = 0.0                                     # residues z^-1, z^-2
    out = np.empty(nfft)

    for i in range(nfft):
        # charge-sharing summation at the CDAC top plate
        v = (1 - 2 * acs) * x[i] + kef * (q1 - 0.5 * q2)
        if vn_rms:
            v += rng.normal(0.0, vn_rms * lsb)

        # SAR quantiser, saturating at full scale
        code = np.clip(np.round(v / lsb), -2 ** (nb - 1), 2 ** (nb - 1) - 1)
        d = code * lsb

        q2, q1 = q1, v - d                            # extract residue
        out[i] = d / (1 - 2 * acs)                    # de-scale for the FFT

    return out, mbin


def sqnr(y, mbin, osr, nfft):
    """In-band SNDR via coherent FFT. Signal bin and harmonics excluded."""
    spec = np.abs(np.fft.rfft(y)) ** 2
    nbw = int(nfft / (2 * osr))
    sig = spec[mbin]
    band = spec[1:nbw + 1].copy()
    for h in range(1, 12):                            # strip harmonics
        k = (h * mbin) % nfft
        if 1 <= k <= nbw:
            band[k - 1] = 0.0
    band[mbin - 1] = 0.0
    noise = band.sum()
    return 10 * np.log10(sig / noise) if noise > 0 else np.inf


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--nb", type=int, default=9)
    p.add_argument("--osr", type=int, default=8)
    p.add_argument("--nfft", type=int, default=8192)
    p.add_argument("--sweep", action="store_true")
    a = p.parse_args()

    print(f"nb = {a.nb}   OSR = {a.osr}   K_EF_opt = {kef_opt(a.osr):.4f}")
    print()

    if a.sweep:
        print("  K_EF     G (A_CS=1/16)   SQNR [dB]")
        best = (None, -1e9)
        for k in np.arange(1.70, 2.005, 0.0125):
            y, m = simulate(nb=a.nb, osr=a.osr, kef=k, nfft=a.nfft)
            s = sqnr(y, m, a.osr, a.nfft)
            if s > best[1]:
                best = (k, s)
            print(f"  {k:5.4f}      {k*16:6.2f}       {s:7.2f}")
        print(f"\n  peak at K_EF = {best[0]:.4f}  (G = {best[0]*16:.2f}), "
              f"{best[1]:.2f} dB")
        print("  Cadence must peak at the same G. If it doesn't, A_CS is wrong.")
        return

    for label, kef in (("zeros at DC (K_EF = 2)", 2.0),
                       ("optimised zeros", kef_opt(a.osr))):
        y, m = simulate(nb=a.nb, osr=a.osr, kef=kef, nfft=a.nfft)
        print(f"  {label:26s}  K_EF = {kef:.4f}   "
              f"SQNR = {sqnr(y, m, a.osr, a.nfft):6.2f} dB")

    print()
    print("  OSR   K_EF_opt   G for A_CS = 1/16")
    for o in (4, 8, 16, 32, 64):
        print(f"  {o:3d}    {kef_opt(o):.4f}      {kef_opt(o)*16:6.2f}")
    print("\n  Only G changes with OSR. No capacitor changes, no topology change.")


if __name__ == "__main__":
    main()
