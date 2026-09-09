if {![namespace exists ::IMEX]} { namespace eval ::IMEX {} }
set ::IMEX::dataVar [file dirname [file normalize [info script]]]
set ::IMEX::libVar ${::IMEX::dataVar}/libs

create_library_set -name lib_tt\
   -timing\
    [list ${::IMEX::libVar}/mmmc/sky130_tt_1.8_25_nldm.lib]
create_rc_corner -name rc_typ\
   -preRoute_res 1\
   -postRoute_res 1\
   -preRoute_cap 1\
   -postRoute_cap 1\
   -postRoute_xcap 1\
   -preRoute_clkres 0\
   -preRoute_clkcap 0\
   -qx_tech_file ${::IMEX::libVar}/mmmc/rc_typ/qrcTechFile
create_delay_corner -name dc_tt\
   -library_set lib_tt\
   -rc_corner rc_typ
create_constraint_mode -name cm\
   -sdc_files\
    [list ${::IMEX::libVar}/mmmc/gate_driver.sdc]
create_analysis_view -name av_tt -constraint_mode cm -delay_corner dc_tt
set_analysis_view -setup [list av_tt] -hold [list av_tt]
