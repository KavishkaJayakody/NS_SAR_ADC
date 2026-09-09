# EF NS-SAR — Verilog-A behavioural model set

Active blocks are behavioural, passives are structural. That split is what makes
the block-by-block swap to real electronics work.

| File | What it is | Replaced at stage |
|---|---|---|
| `sw_ideal.va` | switch, finite ron/roff | 4 (transmission gate) |
| `clkgen.va` | frame-rate phases + handshake | last / never |
| `sar_logic.va` | generic SAR FSM, bit-rate control | **superseded — see below** |
| `cdac_diff.va` | **placeholder** CDAC | **superseded — see below** |
| `comp_damp.va` | dual-mode comparator / D-Amp | 3 then 4 |
| `prng_lfsr.va` | dither LFSR | last |
| `fir_ef_diff.scs` | passive SC FIR — already structural | 4 (switches only) |
| `tb_ns_sar.scs` | testbench, generic blocks | — |
| `golden_model.py` | z-domain reference | — |

### Stage-5 replicas of the real 8-bit core (`core_*`)

The "teammate's core" stage is done. These are Verilog-A replicas of the cells
in `libraries/NS_SAR_Analog` and `libraries/NS_SAR_Digital`, carrying the same
pin names, parameter names and 1.8 V logic levels, so they import onto the
existing Virtuoso symbols and can be swapped for the real schematics one at a
time.

| File | Replica of | Notes |
|---|---|---|
| `core_capacitor_array.va` | `NS_SAR_Analog/capacitor_array` | 8-bit binary array, flattened: 9 gate drivers + 256 unit cells + input select + vcm switches. **Retires `cdac_diff.va`** |
| `core_unit_capacitor.va` | `NS_SAR_Analog/unit_capacitor{,_dummy}` | populated version of the core's empty veriloga shell; `weight` puts W cells in parallel |
| `core_gate_driver.va` | `NS_SAR_Analog/gate_driver` | decodes {SAMPLE, C_i} into the three complementary select pairs |
| `core_gate_driver_vcm.va` | `NS_SAR_Analog/gate_driver_vcm` | top-plate reset buffer, rails taken from VDD/VSS |
| `core_vcm_switch.va` | `NS_SAR_Analog/vcm_switch` | finite ron + the hard current clamp |
| `core_input_select_switch.va` | `NS_SAR_Analog/input_select_switch` | VIN vs VREF_P onto the bottom-plate rail |
| `core_comparator.va` | `NS_SAR_Analog/comparator` | + CLK strobe, noise, OUT_N. `clocked=0` restores the core's continuous behaviour |
| `core_sar_logic_8bit.va` | `NS_SAR_Digital/digital_SAR_logic_8bit` | + CONV_START / PHI_S / PHI_EF. **Retires `sar_logic.va`** |
| `core_cdac_diff.scs` | — | two arrays wired differentially; drop-in for `cdac_diff` |
| `tb_ns_sar_core.scs` | — | the same EF loop, built from the blocks above |

Run it with `spectre tb_ns_sar_core.scs +escchars +log spectre_core.out`.

**Weight map.** `C7` = MSB (128 units) — `C0` = LSB (1 unit), `C8` = the
common/dummy cell (1 unit). 256 units x 34.62 fF = **8.863 pF per side**, so
`cf = cdac/14 = 633 fF` still gives A_CS = 1/16 and K_EF = 1.875 at G = 30 —
the sizing table below is unchanged. This mirrors the CP7..CP0 + CPC bus. If
your symbol wires CPC to `C0` instead, swap those two nets at the instance;
the dummy is the only control whose position is free.

**Four things the core blocks change, all of which bite.**

1. **1.8 V logic, not 1.1 V.** Every generic block in `tb_ns_sar_core.scs` is
   given `vdd=1.8 vth=0.9`. Miss one and its threshold sits at 0.55 V, where
   1.8 V logic still parses correctly — so the bug hides until you lower the
   supply.

2. **The vcm_switch sees the whole array.** tau = ron x 8.86 pF, which at the
   core cell's ron = 1 kohm is 8.9 ns and would need `t_s` > 60 ns for 9-bit
   settling. The testbench instead cuts `ron_vcm` to 100 ohm and uses
   `t_s = 30 ns`. Either is fine; choosing by accident is not. An under-sized
   sampling window looks exactly like DAC gain error on a spectrum.

3. **Differential full scale is +/-(VREF_P - VREF_N) = +/-1.8 V**, twice the
   +/-0.9 V swing in `doc/ADC_parameters.txt`. Driving the spec swing throws
   away 6 dB — a whole bit. Either drive the full +/-1.8 V, or set
   VREF_P = 0.9 V and get the LSB back.

4. **The core is 8 bits with NO redundancy**, and the pitfall list below says
   redundancy is not optional. EF charge injected during `phi_ef` can push the
   residue past what the remaining LSB trials can recover, and that error is
   *not* shaped. Either add one redundant cap to the array and set `nb=9` in
   `core_sar_logic_8bit`, or shrink `cf` until the overload disappears — at
   the cost of K_EF, and hence of notch depth. It shows up as distortion that
   gets **worse** with OSR, because the NTF does not shape it: sweep the input
   amplitude and watch SFDR.

**Why `SP`/`SN` are gated by `PHI_S`.** The core FSM raises SP/SN the moment
EOC fires. In this loop that is fatal: `clkgen`'s frame runs
`phi_rst -> phi_d2 -> phi_amp -> phi_s`, so the D-Amp reads the residue off the
top plates *before* the next sample is taken. Reconnecting the array to VIN at
EOC would destroy the residue before `phi_amp` ever saw it, and the loop would
quietly degenerate into a plain SAR that still looks plausible on a spectrum.
`core_sar_logic_8bit` therefore holds the converged code through the idle
period and samples only inside `PHI_S`. `VCM_CON` also falls `t_bp` = 200 ps
*before* SP/SN so the top plate opens first — that is what bottom-plate
sampling means, and putting both on the same edge is a race the simulator
resolves arbitrarily.

---

## Import into Virtuoso

For each `.va`:

1. `File → Import → Verilog-A…`, target your library, cellview `veriloga`.
2. Virtuoso auto-generates the symbol and CDF from the parameter list.
3. Check pin directions on the generated symbol: **`topp`, `topn`, `inp`,
   `inn`, `outp`, `outn` must be `inputOutput`**. If any is `output` it becomes
   a voltage source, `A_CS` collapses and the notch vanishes.

Build `fir_ef_diff` as a **schematic**, not Verilog-A — place six `cap`
instances and twelve `sw_ideal` symbols per the `.scs` netlist. Set the switch
view list to `spectre cmos_sch schematic veriloga`.

---

## Netlist wiring

```
vinp/vinn ──► cdac_diff ──┬── topp/topn ──┬──► comp_damp.inp/inn
                          │               └──◄─ fir_ef.topp/topn   (phi_ef)
                          │
comp_damp.outp/outn ──────┴──► fir_ef.ampp/ampn                    (phi_amp)

clkgen ──► phi_rst, phi_d2, phi_amp, phi_s, phi_prn, conv_start
sar_logic ──► cmp_clk, phi_ef, dac_code[8:0], dout[8:0], eoc
comp_damp ──► cmp_out, amp_done
```

`topp`/`topn` carry **three** connections: CDAC, comparator/amp input, and the
FIR injection port. One net pair, four `inout` pins.

Bus order in the flat netlist is **MSB first** — `dac_code[8]` … `dac_code[0]`.

---

## Sizing

| Parameter | Value | Origin |
|---|---|---|
| `cdac` | 1 pF per side | kT/C ≈ quantisation noise |
| `cf` | `cdac/14` = 71.4 fF | gives A_CS = 1/16 |
| `gain` | 30 | K_EF = G·A_CS = 1.875 |
| `rout` | 20 kΩ | τ ≈ rout·2cf ≈ 2.9 ns, comparable to `t_amp` |
| `vn_amp` | 85 µV rms | ~68 % of the noise budget |
| `n_ef` | 5 | last 4 LSB + 1 redundancy |
| `t_frame` | 100 ns | fs = 10 MS/s |

Retuning for a different OSR changes **`gain` only**:

| OSR | K_EF_opt | `gain` |
|---|---|---|
| 4 | 1.659 | 26.5 |
| 8 | 1.902 | 30.4 |
| 16 | 1.975 | 31.6 |
| 32 | 1.994 | 31.9 |

---

## Bring-up order

1. **`python3 golden_model.py`** — fixes the number you are chasing.
   9-bit / OSR 8 / K_EF 1.902 → **89.5 dB**.
2. **NS disabled.** Set `n_ef=0` in `sar_logic` and `noise_on=0`. Expect plain
   9-bit SQNR ≈ 56 dB. If this fails, do not debug the noise shaping.
3. **NS enabled, noiseless.** Should land within ~1 dB of step 1.
4. **`python3 golden_model.py --sweep`**, then sweep `gain_v` from 26 to 34 in
   Cadence. Peaks must coincide at G ≈ 30. **This is the cheapest possible
   check that A_CS is right** — most people skip it and pay for it later.
5. `noise_on=1`, then swap `comp_damp` to schematic, then `sw_ideal` to
   transmission gates, then the real CDAC.

After step 5, **re-extract A_CS** — parasitics will move it, and `gain` must be
retuned to hold K_EF at 1.875.

---

## Pitfalls that cost days

**Off-by-one in the EF delay.** The D-Amp processes residue *n−1* at the top of
frame *n*; the charge lands during frame *n*'s conversion. Get this wrong and
the NTF becomes `1 − K(z⁻² − 0.5z⁻³)` — still shaped, still plausible on a
spectrum, wrong. Check against the golden model, not by eye.

**Phase overlap.** `Cres1`/`Cres2` must disconnect from the amp *before*
`phi_ef` closes, or you get a low-impedance path from the amp onto the top
plate and the passive summation becomes a driven one. `t_gap` in `clkgen`
guards this. Finite `roff` is what makes the failure visible.

**Comparator polarity.** `cdac_diff` yields `V(topp,topn) = d − vin_diff`, so
`cmp_out = 1` means the trial is too large. That is `cmp_pol = 1`. If your
teammate's core defines it the other way, flip the parameter — the search will
converge to full scale otherwise.

**Redundancy.** `nb = 9` is 8 bits + 1 redundancy. With `nb = 8` and no
redundancy the EF charge pushes the residue out of range and the back end
overloads. This is not optional.

**maxstep.** Charge-redistribution networks with fast switches will step over
`phi_ef` if unconstrained. `maxstep=0.5n` in the testbench.

---

## FFT post-processing

Sample `d8..d0` on the rising edge of `eoc`, drop the first 200 frames, then
coherent FFT (no window). Integrate bins `1 … nfft/(2·OSR)`, excluding the
signal bin and its harmonics. `golden_model.py:sqnr()` does exactly this and
can be pointed at Cadence data for an apples-to-apples comparison.
