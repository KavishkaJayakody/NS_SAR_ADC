# ####################################################################

#  Created by Genus(TM) Synthesis Solution 18.10-p003_1 on Fri Aug 07 06:58:42 +0530 2026

# ####################################################################

set sdc_version 2.0

set_units -capacitance 1000.0fF
set_units -time 1000.0ps

# Set the current design
current_design gate_driver

create_clock -name "vclk" -period 10.0 -waveform {0.0 5.0} 
set_load -pin_load 0.05 [get_ports SEL_VIN]
set_load -pin_load 0.05 [get_ports SEL_VIN_N]
set_load -pin_load 0.05 [get_ports SEL_VREF_P]
set_load -pin_load 0.05 [get_ports SEL_VREF_P_N]
set_load -pin_load 0.05 [get_ports SEL_VREF_N]
set_load -pin_load 0.05 [get_ports SEL_VREF_N_N]
set_clock_gating_check -setup 0.0 
set_input_delay -clock [get_clocks vclk] -add_delay 1.0 [get_ports SAMPLE]
set_input_delay -clock [get_clocks vclk] -add_delay 1.0 [get_ports VREF]
set_output_delay -clock [get_clocks vclk] -add_delay 1.0 [get_ports SEL_VIN]
set_output_delay -clock [get_clocks vclk] -add_delay 1.0 [get_ports SEL_VIN_N]
set_output_delay -clock [get_clocks vclk] -add_delay 1.0 [get_ports SEL_VREF_P]
set_output_delay -clock [get_clocks vclk] -add_delay 1.0 [get_ports SEL_VREF_P_N]
set_output_delay -clock [get_clocks vclk] -add_delay 1.0 [get_ports SEL_VREF_N]
set_output_delay -clock [get_clocks vclk] -add_delay 1.0 [get_ports SEL_VREF_N_N]
set_max_transition 0.5 [current_design]
set_wire_load_mode "enclosed"
set_dont_use [get_lib_cells sky130_tt_1.8_25/ICGX1]
