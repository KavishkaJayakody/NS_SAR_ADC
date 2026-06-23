# ####################################################################

#  Created by Genus(TM) Synthesis Solution 18.10-p003_1 on Mon May 04 01:07:08 +0530 2026

# ####################################################################

set sdc_version 2.0

set_units -capacitance 1000.0fF
set_units -time 1000.0ps

# Set the current design
current_design test_inverter

create_clock -name "clk" -period 10000.0 -waveform {0.0 5000.0} 
set_clock_gating_check -setup 0.0 
set_input_delay -clock [get_clocks clk] -add_delay 1000.0 [get_ports A]
set_output_delay -clock [get_clocks clk] -add_delay 1000.0 [get_ports B]
set_wire_load_mode "enclosed"
set_dont_use [get_lib_cells sky130_tt_1.8_25/ICGX1]
