create_clock -name vclk -period 10
set_input_delay  1 -clock vclk [all_inputs]
set_output_delay 1 -clock vclk [all_outputs]
set_max_transition 0.5 [current_design]
set_load 0.05 [all_outputs]
