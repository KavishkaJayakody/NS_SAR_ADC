# Scripts

## Setting the simulation output directory in ADE L

All scripts expect Spectre to write results into the project `simulations/` folder.

**In ADE L:**

1. Go to **Setup → Simulator / Directory / Host**
2. Set **Project Directory** to:
   ```
   ~/NS_SAR_ADC/simulations
   ```
3. Click **OK**
4. Save the session: **Session → Save State**

After simulation, pull results and run the benchmark:

```bash
bash scripts/pull.sh
python3 scripts/benchmark.py
```
