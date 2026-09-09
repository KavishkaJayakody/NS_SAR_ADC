# Integrated Physical Verification (DRC, LVS) and Parasitic Extraction (PEX) Guide

**Target Process:** Google/SkyWater 130nm Open-Source PDK (SKY130)
**Target Toolset:** Cadence Virtuoso IC617 + PVS 16.1 + Quantus QRC (EXT181)

## Overview & Scope
The official Cadence-compatible SkyWater 130nm PDK is natively written for Pegasus (DRC/LVS) and modern versions of Quantus. However, many academic server clusters rely on PVS for physical verification and legacy Quantus EXT181 (2018) engines for extraction.

This guide provides a comprehensive setup to successfully run:

*   **DRC & LVS** using PVS instead of Pegasus.
*   **RC Parasitic Extraction (PEX)** using Quantus EXT181 by forcing a local compilation of the physical technology rules to bypass modern software calculation crashes (`ncps=6 nvar=2`).

**Prerequisites:** Ensure your lab environment paths for `IC617`, `PVS161`, and `EXT181` are sourced in your terminal session before launching Virtuoso.

## Section 1: PVS DRC Configuration
The PDK rules look for a Pegasus environment variable by default. We can reroute this target variable to point PVS directly to the physical sign-off guidelines.

### 1.1 Shell Environment Configuration
Add the following pointer line to your ~/.bashrc file. Ensure Virtuoso is closed before performing this edit:

```bash


# Point PVS to the SkyWater DRC Rule Deck directory
export PEGASUS_DRC=/path/to/your/pdk_dir/Sky130_cadence_pdk/sky130_release_0.1.0/Sky130_DRC
Save your file and remember to refresh your active terminal window:

```bash


source ~/.bashrc
```

### 1.2 Executing a DRC Run
Open your design layout in Virtuoso Layout L/XL.

1.  From the top banner menu, click **PVS -> Run DRC...**.
2.  Under **Run Data**, choose or create a clean sandbox directory (e.g., `~/DRC_RUN`).
3.  Navigate to the **Rules** tab -> **Tech&Rules**:
    *   Click **Add...** and select the physical verification language file: `SKY130_DRC/sky130_rev_0.0_2.12.drc.pvl` (or similar version present).
    *   Leave technology mapping fields blank.
4.  Navigate to **Rules** tab -> **Configurator**:
    *   Check the box labeled **Use Configurator**.
    *   Click the "..." button and load: `SKY130_DRC/sky130.drc.cfg`.

> **Pro-Tip (Tiny Tapeout Specific):** Under the options checklist, you may safely check "Turn Off Density Rules" to prevent chip-level tiling fill density errors from failing your small macro block.

5.  Click **Submit** to execute the run.

## Section 2: PVS LVS Configuration
Setting up LVS requires mapping the physical layout properties to your schematic pins and creating a link for the Quantus extraction bridge database.

### 2.1 File System Interconnect Setups
Close Cadence Virtuoso.

1.  Navigate to your master working directory and create a brand-new text file named `pvtech.lib`. Add the following line to define the rule path:

```plaintext


DEFINE sky130_pv /path/to/your/sky130_release_0.1.0/pv
```

2.  Navigate into that `pv` directory specified above and edit the `techRuleSet` wrapper code to ensure it points natively to your PVS rule locations rather than Pegasus structures:

```scheme


;; PVS Rulesets
pvsRuleSet( "default"
  ( DrcRules     "../Sky130_DRC/sky130_rev_0.0_2.12.drc.pvl" )
  ( DrcGuiPreset "drc.preset" )
  ( LvsRules     "../Sky130_LVS/sky130.lvs.pvl" )
  ( LvsGuiPreset "lvs.preset" )
  )
pvsRuleSet( "lvs_qrc"
  ( LvsRules     "../Sky130_LVS/sky130.lvs.pvl" )
  ( LvsGuiPreset "lvs_qrc.preset" )
  )

;; Quantus Rulesets
ruleSet( "typical"
  ( RcxSetupDir "../quantus/extraction/typical" )
  )
```

3.  Move into your `SKY130_LVS` directory and create a symbolic link shortcut so the layout tools can find the generic rule deck file:

```
bash

cd /path/to/your/pdk_dir/Sky130_LVS/
ln -s sky130.lvs.v0.0_1.1.pvl sky130.lvs.pvl
```
2.2 Executing an LVS Run
Reopen your layout in Virtuoso, and select PVS -> Run LVS....

1.  Select an isolated run directory (e.g., `~/LVS_RUN`).
2.  Under the **Rules** tab -> **Tech&Rules**, pull down your technology targets to populate the form parameters using your newly defined library assets:
    *   **Technology:** `sky130_pv`
    *   **RuleSet:** `lvs_qrc`
3.  Click **Submit** to run.

(Note: For specific non-fatal device extraction warnings or pin properties, refer to the community troubleshooting notes in the reference repository links).

## Section 3: Quantus Parasitic Extraction (PEX)
The factory-default SkyWater PDK includes a binary qrcTechFile compiled using a modern version of Cadence (2022 / EXT212). If you run capacitance extraction on an older 2018 engine (EXT181), the tool will crash during the pax16 evaluation phase.

Follow these steps to recompile a native, 2018-compatible binary rule structure.

### 3.1 Resolving Missing UI Menus (The PVS-Quantus Bridge)
If the **Quantus** or **PEX** options are completely missing from your Virtuoso Layout window, you must initialize the software hooks manually. Create a text file named `.cdsInit` inside your working directory and paste this initialization script:

```scheme
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; PVS-Quantus Bridge Automation for Sky130 by cdsInit file
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

; 1. Load the PVS UI Context (The Bridge)
let( (pvsContext)
    pvsContext = "/home/aed/cadence/PVS161/tools.lnx86/pvs/bin/64bit/etc/context/6.1.0/64bit/pvsui.cxt"
    if( isFile(pvsContext) then
        loadContext(pvsContext)
        printf("INFO: PVS 6.1.0 64-bit UI Context Loaded.\n")
    else
        printf("ERROR: PVS Context not found at %s\n" pvsContext)
    )
)

; 2. Load the Quantus QRC Context (The Engine)
let( (qrcContext)
    qrcContext = "/home/aed/cadence/EXT181/tools.lnx86/extraction/bin/64bit/etc/context/6.1.7/64bit/qrc.cxt"
    if( isFile(qrcContext) then
        loadContext(qrcContext)
        printf("INFO: Quantus QRC Context Loaded.\n")
    )
)

; 3. Load SNA Context (Required for Menu Registration)
let( (snaContext)
    snaContext = "/home/aed/cadence/EXT181/tools.lnx86/extraction/bin/64bit/etc/context/6.1.7/64bit/sna.cxt"
    if( isFile(snaContext) then
        loadContext(snaContext)
        printf("INFO: Quantus SNA Context Loaded.\n")
    )
)

; 4. Initialize the Bridge and Auto-Register Menu
if( isCallable('_vuiInitPvs) then 
    _vuiInitPvs() 
    _vuiInitPvsQrc()
    
    if( isCallable('_qrcInitRunForm) then
        hiEnqueueCommand("_qrcInitRunForm()")
        printf("INFO: QRC Menu Initialization Enqueued.\n")
    )
    printf("INFO: PVS-Quantus Bridge Initialized Successfully.\n")
)

; Safety trigger to load form if asynchronous loading delays occurrences
procedure( KS_InitializeQRC(args)
    when( isCallable('_qrcInitRunForm)
        _qrcInitRunForm()
    )
    t
)
deRegUserTriggers("maskLayout" nil nil 'KS_InitializeQRC)
```

### 3.2 Step-by-Step Rule Recompilation
Navigate to the extraction directory:

```bash


cd /pdk_dir/sky130_release_0.1.0/quantus/extraction/typical/
```
Isolate the incompatible factory tech file:

```bash


mkdir -p "Original files"
mv qrcTechFile "Original files/"
```
Downgrade the compilation command structure: Open compilation.cmd in a text editor (gedit compilation.cmd). Modify it to call your local binary directly and add the necessary -p2lvs reference mapping switch required by your 2018 tool pipeline. Rewrite the script contents exactly as follows:

```plaintext
Techgen -compilation -cap_ground_layer pwell \
-p poly,allGates,diff \
-lvs_blocking nfet,nfet \
-lvs_blocking pfet,pfet \
-lvs_blocking hvtpfet,hvtpfet \
-lvs_blocking lvtpfet,lvtpfet \
-lvs_blocking lvtnfet,lvtnfet \
-lvs_blocking HV_FET_gate,HV_FET_gate \
-canonical_res_caps \
-length_units meters \
-lvs ./lvsfile -p2lvs ./qrcTechFile -layer_setup ./layer_setup 
```
(Note: Ensure your current terminal can find the local compiler tool by running which Techgen first).

Supply the baseline reference template and execute compilation:

```bash
# Copy the structure map template back into the active folder
cp "Original files/qrcTechFile" ./

# Grant permissions and run the 2018 compilation pipeline
chmod +x compilation.cmd
./compilation.cmd
```
Confirm that a fresh binary qrcTechFile has successfully populated the folder with a fresh timestamp.

3.3 Executing Parasitic Extraction via GUI
Open your completed layout view in Virtuoso Layout XL.

Select Quantus -> Run Pegasus - Quantus (or Run PVS - Quantus).

The initial layout/schematic structural cross-referencing window will be automatically filled with paths from your healthy LVS run directory database. Click OK.

In the primary Parasitic Extraction run form, configure these fields:

Technology: sky130_pv

RuleSet: typical

Extraction Type: Select RC or C Only as desired.

Output: Set to Extracted View.

View Name: av_extracted.

Click OK to run the extraction. When the log displays Quantus QRC terminated normally, your layout extraction database is ready.

Section 4: Post-Layout Simulation (ADE Setup)
To verify how wire resistance and overlapping parasitic capacitance alter circuit specs like switching parameters, settling speeds, or amplifier input offset mismatches, you must override the ideal schematic configurations.

Open your design simulation session in ADE L or ADE Explorer.

Go to the top options banner and navigate to Setup -> Environment.

Locate the field box titled Switch View List.

Modify the text sequence to include av_extracted at the very front of the line (before schematic):

Plaintext


# Example Switch View List Sequence
av_extracted spice cmos_sch schematic
Run your standard circuit simulations (Transient, AC, DC Offset). The Spectre engine will automatically read your 100% complete layout parasitic matrix and provide your post-layout simulation results!


refernces

https://github.com/atenfyr/ttsky_analog/blob/main/notes_on_using_virtuoso/notes_on_using_virtuoso.md