# Cadence Genus(TM) Synthesis Solution, Version 18.10-p003_1, built Jun  7 2018 23:53:27

# Date: Fri Aug 07 06:52:51 2026
# Host: aed (x86_64 w/Linux 3.10.0-1160.108.1.el7.x86_64) (4cores*8cpus*1physical cpu*Intel(R) Core(TM) i7-4770 CPU @ 3.40GHz 8192KB)
# OS:   CentOS Linux release 7.9.2009 (Core)

source scripts/genus.tcl
source scripts/genus.tcl
cat reports/gates.rpt
cat outputs/gate_driver_netlist.v
exec ls $PDK/lib
exec grep -c "^SITE" $PDK/lef/sky130_scl_9T.lef
@genus:root: 4> cat outputs/gate_driver_netlist.v
1
@genus:root: 5> exec ls $PDK/lib
sky130_ff_1.98_0_nldm.lib
sky130_ff_1.98_0_nldm.lib.gz
sky130_ss_1.62_125_nldm.lib.gz
sky130_tt_1.8_25_nldm.lib
sky130_tt_1.8_25_nldm.lib.gz
@genus:root: 6> exec grep -c "^SITE" $PDK/lef/sky130_scl_9T.lef
0
child process exited abnormally
@genus:root: 7>
exec grep -n -i "site" $PDK/lef/sky130_scl_9T.lef | head -5
exec grep -n -i "manufacturinggrid\|^LAYER\|UNITS" $PDK/lef/sky130_scl_9T.lef | head -5
exit
