# Cadence Genus(TM) Synthesis Solution, Version 18.10-p003_1, built Jun  7 2018 23:53:27

# Date: Sun May 03 23:01:38 2026
# Host: aed (x86_64 w/Linux 3.10.0-1160.108.1.el7.x86_64) (4cores*8cpus*1physical cpu*Intel(R) Core(TM) i7-4770 CPU @ 3.40GHz 8192KB)
# OS:   CentOS Linux release 7.9.2009 (Core)

set_db library /home/user22/sky130_pdk/sky130_scl_9T_0.1.1/sky130_scl_9T/lib/sky130_tt_1.8_25_nldm.lib
read_hdl test_inverter.v
elaborate
syn_generic
syn_map
report_gates
write_hdl > inverter_synth.v
exit
