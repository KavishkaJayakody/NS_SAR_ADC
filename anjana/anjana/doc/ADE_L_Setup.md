# ADE L Simulation Directory Setup

This guide configures Cadence ADE L to write all simulation output files into
the project's `simulations/` folder so that results can be pulled back locally
and analysed with `scripts/benchmark.py`.

---

## Why this matters

By default, Spectre/ADE L writes results to `~/simulation/<cellname>/` in your
home directory on the server.  The pull script (`scripts/pull.sh`) syncs
`NS_SAR_ADC/simulations/` — if ADE L writes elsewhere the results will never be
pulled and `benchmark.py` will not find the PSF files.

The expected output path for the 3-bit testbench is:

```
NS_SAR_ADC/simulations/Sar_3_tb/spectre/schematic/psf/
```

---

## Step-by-step: Set the project directory in ADE L

### 1. Open the testbench in Virtuoso

Open the cell you want to simulate (e.g. `NS_SAR_test / Sar_3_tb / schematic`)
in the Schematic Editor, then launch ADE L:

```
Launch → ADE L
```

### 2. Set the simulation directory

In the ADE L window:

```
Setup → Simulator / Directory / Host…
```

In the dialog that opens:

| Field | Value |
|-------|-------|
| **Simulator** | `spectre` |
| **Project Directory** | `~/NS_SAR_ADC/simulations` |
| **Host Mode** | Local (or whichever applies) |

Click **OK**.

> **Tip:** You can also type the path directly into the *Project Directory*
> field. Use the absolute server path if relative `~` does not resolve:
> `/home/user23/NS_SAR_ADC/simulations`

### 3. Verify the path in the CIW (optional)

In the Cadence Command Interpreter Window (CIW) run:

```skill
envGetVal("spectre.envOpts" "projectDir")
```

It should return `"/home/user23/NS_SAR_ADC/simulations"`.

To set it from the CIW directly (alternative to the GUI):

```skill
envSetVal("spectre.envOpts" "projectDir" 'string "/home/user23/NS_SAR_ADC/simulations")
```

### 4. Save the ADE L state

Save the session so the directory is remembered next time:

```
Session → Save State…
```

Choose **Cell** to save the state alongside the testbench cell, or **File** to
save it to a named `.sdb` file in the project.

---

## Step-by-step: Set the output directory per-testbench via `ocean`

If you run simulations non-interactively (OCEAN script), set the project
directory at the top of the script:

```skill
simulator('spectre)
envSetVal("spectre.envOpts" "projectDir" 'string "/home/user23/NS_SAR_ADC/simulations")
design("NS_SAR_test" "Sar_3_tb" "schematic")
```

---

## Verifying the output after simulation

After a successful run the PSF directory should exist on the server:

```
~/NS_SAR_ADC/simulations/Sar_3_tb/spectre/schematic/psf/
    tran.tran.tran        ← PSF index file
    tran.tran.tran.dat    ← binary waveform data
    tran.tran.tran.sig    ← ASCII signal metadata
```

Pull the results to your local machine:

```bash
bash scripts/pull.sh
```

Then run the benchmark:

```bash
python3 scripts/benchmark.py
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ERROR: file not found: …/psf/tran.tran.tran.dat` | Project directory not set correctly | Re-check Setup → Simulator / Directory / Host |
| PSF files exist but are from an old run | `pull.sh` not run after simulation | Run `bash scripts/pull.sh` |
| Results land in `~/simulation/` instead | ADE L using default path | Set project directory as above and re-run |
| `benchmark.py` shows wrong cell name in path | Testbench cell name differs from `Sar_3_tb` | Update `PSF_DIR` at the top of `benchmark.py` |
