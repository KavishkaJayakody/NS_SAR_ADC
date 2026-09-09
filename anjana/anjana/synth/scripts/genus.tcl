set PDK /home/user23/Sky130_cadance_pdk/sky130_scl_9T_0.1.1/sky130_scl_9T

set_db init_lib_search_path $PDK/lib
set_db library {sky130_tt_1.8_25_nldm.lib}

set_db hdl_search_path ./rtl
set_db syn_generic_effort medium
set_db syn_map_effort     medium
set_db syn_opt_effort     medium

read_hdl gate_driver.v
elaborate gate_driver
read_sdc ./scripts/constraints.sdc

check_design -unresolved

syn_generic
syn_map
syn_opt

write_hdl > ./outputs/gate_driver_netlist.v
write_sdc > ./outputs/gate_driver.sdc

report timing > ./reports/timing.rpt
report area   > ./reports/area.rpt
report gates  > ./reports/gates.rpt
report qor    > ./reports/qor.rpt

puts "=== SYNTHESIS DONE ==="
