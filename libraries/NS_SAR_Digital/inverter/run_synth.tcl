# 1. Setup Libraries
set_db library /home/user22/sky130_pdk/sky130_scl_9T_0.1.1/sky130_scl_9T/lib/sky130_tt_1.8_25_nldm.lib

# 2. Load and Elaborate Design
read_hdl test_inverter.v
elaborate

# --- FIX: Set the active design context ---
current_design test_inverter

# 3. Apply Constraints (Virtual Clock)
create_clock -name clk -period 10000 
set_input_delay 1000 [get_ports A] -clock clk
set_output_delay 1000 [get_ports B] -clock clk

# 4. Synthesize
syn_generic
syn_map

# 5. Export Files for Innovus
write_hdl > inverter_synth.v
write_sdc > inverter.sdc

# 6. Reports
report_gates
report_timing