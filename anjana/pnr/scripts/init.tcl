set PDK  /home/user23/Sky130_cadance_pdk/sky130_scl_9T_0.1.1
set TLEF $PDK/sky130_scl_9T_tech/lef/sky130_scl_9T.tlef
set CLEF $PDK/sky130_scl_9T/lef/sky130_scl_9T.lef

set init_verilog     ./gate_driver_netlist.v
set init_top_cell    gate_driver
set init_lef_file    [list $TLEF $CLEF]
set init_mmmc_file   ./scripts/mmmc.view
set init_pwr_net     VDD
set init_gnd_net     VSS

init_design

# sanity checks
puts "=== Sites available ==="
dbGet head.sites.name
puts "=== Layers ==="
dbGet head.layers.name
