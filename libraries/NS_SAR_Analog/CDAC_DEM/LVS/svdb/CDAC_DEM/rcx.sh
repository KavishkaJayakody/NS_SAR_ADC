#!/bin/ksh
# This script was generated Fri Aug 28 15:51:38 2026 by:
#
# Program: /home/aed/cadence/EXT181/tools.lnx86/extraction/bin/64bit//RCXspice
# Version: 15.2.0
# Created: Fri May 15 16:43:23 EST 2015
#
#/home/aed/cadence/EXT181/tools.lnx86/extraction/bin/64bit//RCXspice -techdir \
#	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
#	-newlvs \
#	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM.lvsfile \
#	-rcxdir \
#	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM \
#	-xy_coordinates c,r -type full -temperature 25.0 -tempdir \
#	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/rcx_temp \
#	-sub_node_char # -res_models yes -parasitic_res_models no \
#	-parasitic_cap_models no -output_net_name_space schematic \
#	-output_hierarchy_delimiter / -output \
#	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/extview.tmp \
#	-net_name_space layout -minR 0.1 -minC_by_percentage 0.1 -minC 1e-15 \
#	-max_merged_via_size auto -max_fracture_length infinite -lvs_source \
#	hcci -ignore_gate_diffusion_fringing_cap -hierarchy_delimiter / \
#	-hcci_run_name CDAC_DEM -hcci_run_dir \
#	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb \
#	-hcci_net_prop 5 -hcci_inst_prop 6 -hcci_dev_prop 7 \
#	-fracture_length_units MICRONS -extract both \
#	-exclude_self_caps_extended Y -df2 -device_finger_delimiter @ \
#	-cap_models yes -cap_ground VSS! -cap_extract_mode coupled \
#	-cap_coupling_factor 1.0 -array_vias_spacing auto \
#	-agds_layer_map_file \
#	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM.gds.map
set -e
set -v
##=======================================================
##ADD_EXPLICIT_VIAS=N
##ADD_BULK_TERMINAL=N
##AGDS_FILE=/dev/null
##AGDS_LAYER_MAP_FILE=/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM.gds.map
##HCCI_DEV_PROP_FILE=/dev/null
##AGDS_SPICE_FILE=/dev/null
##AGDS_TEXT_LAYERS=
##ARRAY_VIAS_SPACING=
##ASSURA_RUN_DIR=.
##ASSURA_RUN_NAME=run1
##BLACK_BOX_CELLS=/dev/null
##BREAK_WIDTH=
##CAP_COUPLING_FACTOR=1.0
##CAP_EXTRACT_MODE=coupled
##CAP_GROUND=VSS!
##CAP_MODELS=yes
##DANGLINGR=N
##DENSITY_CHECK_METHOD=P
##DELETE_OUTPUT_FILE=N
##DEVICE_FINGER_DELIMITER='@'
##DF2=Y
##DRACULA_RUN_DIR=
##DRACULA_RUN_NAME=
##ENABLESENSITIVITYEXTRACTION=N
##EXCLUDE_FLOAT_LIMIT=
##EXCLUDE_FLOAT_DECOPULING_FACTOR=
##EXCLUDE_FLOATING_NETS=N
##EXCLUDE_NETS_REDUCERC=/dev/null
##EXCLUDE_SELF_CAPS=Y
##IGNORE_GATE_DIFFUSION_FRINGING_CAP=Y
##EXTRACT=both
##EXTRACT_MOS_DIFFUSION_AP=N
##EXTRACT_MOS_DIFFUSION_HIGH=
##EXTRACT_MOS_DIFFUSION_RES=N
##FILTER_SIZE=2.0
##FIXED_NETS_FILE=/dev/null
##FMAX=
##FRACTURE_LENGTH_UNITS=MICRONS
##FREQUENCY_FILE=/dev/null
##GROUND_NETS=
##GROUND_NETS_FILE=/dev/null
##GROUND_SUBSTRATE_FLOATING_NETS=N
##HCCI_DEV_PROP=7
##HCCI_INST_PROP=6
##HCCI_NET_PROP=5
##HCCI_RULE_FILE=
##HCCI_RUN_DIR=/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb
##HCCI_RUN_NAME=CDAC_DEM
##HEADER_FILE=/dev/null
##HIERARCHY_DELIMITER='/'
##OUTPUT_HIERARCHY_DELIMITER='/'
##HRCX_CELLS_FILE=/dev/null
##IMPORT_GLOBALS=Y
##LADDER_NETWORK=N
##LVS_SOURCE=hcci
##M_FACTORR=
##M_FACTORW=N
##MACRO_CELL=N
##MAX_FRACTURE_LENGTH=infinite
##MAX_SIGNALS=
##MERGE_PARALLEL_R=N
##MERGE_PARALLEL_VIA=N
##MINC=1e-15
##MINC_BY_PERCENTAGE=0.1
##MINR=0.1
##NET_NAME_SPACE=layout
##NETS_FILE=/dev/null
##OUTPUT=/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/extview.tmp
##OUTPUT_NET_NAME_SPACE=schematic
##PARASITIC_BLOCKING_DEVICE_CELLS_TYPE=gray
##PARASITIC_CAP_MODELS=no
##PARASITIC_RES_MODELS=no
##PARASITIC_RES_LENGTH=N
##PARASITIC_RES_WIDTH=N
##PARASITIC_RES_WIDTH_DRAWN=N
##PARASITIC_RES_UNIT=N
##PARTIAL_CAP_BLOCKING=N
##PEEC=N
##PIN_ORDER_FILE=/dev/null
##PIPE_ADVGEN=
##PIPE_SPICE2DB=
##POWER_NETS=
##POWER_NETS_FILE=/dev/null
##RC_FREQUENCY=
##RCXDIR=/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM
##RCXFS_HIGH=N
##RCXFS_NETS_FILE=/dev/null
##RCXFS_TYPE=none
##RCXFS_CUTOFF_DISTANCE=
##RCXFS_CUTOFF_DISTANCE=
##RCXFS_CUTOFF_DISTANCE=
##RCXFS_CUTOFF_DISTANCE=
##RCXFS_CUTOFF_DISTANCE=
##RCXFS_VIA_OFF=N
##REDUCERC=N
##REGION_LIMIT=
##RES_MODELS=yes
##RISE_TIME=
##SAVE_FILL_SHAPES=N
##SINGLE_CAP_EDSPF=N
##SHOW_DIODES=N
##SKIN_FREQUENCY=
##SPEF=N
##SPEF_UNITS=
##SPLIT_PINS=N
##FORCE_SUBCELL_PIN_ORDERS=N
##SPLIT_PINS_DISTANCE=
##SUB_NODE_CHAR='#'
##SUBSTRATE_PROFILE=/dev/null
##SUBSTRATE_STAMPING_OFF=N
##TEMPDIR=/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/rcx_temp
##TEMPERATURE=25.0
##TYPE=full
##USER_REGION=/dev/null
##VARIANT_CELL_FILE=/dev/null
##VIA_EFFECT_OFF=N
##VIRTUAL_FILL=
##XREF=/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/CDAC_DEM.gnx,/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/CDAC_DEM.gdx
##XY_COORDINATES=c,r
##=======================================================

CASE_SENSITIVE=TRUE
export CASE_SENSITIVE
QRC_MOS_LW_PRECISION=y
export QRC_MOS_LW_PRECISION
TEMPDIR=`setTempDir /home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/rcx_temp`
export TEMPDIR
DEVICE_FINGER_DELIMITER='@'
HIERARCHY_DELIMITER='/'
OUTPUT_HIERARCHY_DELIMITER='/'
cd /home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM
cat <<ENDCAT> caps2dversion
* caps2d version: 10
ENDCAT
cat <<ENDCAT> flattransUnit.info
meters
ENDCAT
QRC=Y
export QRC

#==========================================================#
# Generate RCX input data from annotated GDS2 database
#==========================================================#

agds2rcx -V -H satfile -r \
	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/CDAC_DEM.xcn \
	-crundir \
	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb \
	-unit meters -df2 -xgl -pl CDAC_DEM.ports -f CDAC_DEM.alm -lnn \
	CDAC_DEM.lnn -pnet 5 -pinst 6 -pdev 7 CDAC_DEM.agf \
	CDAC_DEM_pin_xy.spi

#==========================================================#
# Calculate erosion tables for specified process layers
#==========================================================#

densitymap -V -TC -o metal4.den 30 met4
densitymap -V -TC -o metal3.den 30 met3
densitymap -V -TC -o metal2.den 14 met2
densitymap -V -TC -o metal1.den 14 met1
geom nfet_001v8_0rec nSourceDrain - nfet_001v8_0rec,10,i,1
geom pfet_001v8_0rec pSourceDrain - pfet_001v8_0rec,10,i,1

#==========================================================#
# Generate power list
#==========================================================#

cat global.net > power_list
geom -C pfet,nfet,gate,poly - poly,1,i,1

#==========================================================#
# Create ports for abutment
#==========================================================#

geom -C met3 - met3,1,i,1
geom -C bottom_0plate - bottom_0plate,1,i,1
inter met3 bottom_0plate -t met3_bottom_0plate_butt:edge
geom -C met4 - met4,1,i,1
geom -C top_0plate - top_0plate,1,i,1
inter met4 top_0plate -t met4_top_0plate_butt:edge
/bin/mv -f nwell nwell_orig
epick nwell_orig nwell

#==========================================================#
# Ensure vias do not extend beyond routing
#==========================================================#

geom -V met3 bottom_0plate - met3_bottom_0plate_ovia,11,i,1
geom -V met3 met3_bottom_0plate_butt - met3_met3_bottom_0plate_butt_ovia,11,i,1
geom -V bottom_0plate met3_bottom_0plate_butt - bottom_0plate_met3_bottom_0plate_butt_ovia,11,i,1
geom -V met4 top_0plate - met4_top_0plate_ovia,11,i,1
geom -V met4 met4_top_0plate_butt - met4_met4_top_0plate_butt_ovia,11,i,1
geom -V top_0plate met4_top_0plate_butt - top_0plate_met4_top_0plate_butt_ovia,11,i,1
geom -V licon1 li1 pSourceDrain - licon1_li1_pSourceDrain,111,i,2
geom -V licon1 li1 nSourceDrain - licon1_li1_nSourceDrain,111,i,2
geom -V licon1 li1 ptap - licon1_li1_ptap,111,i,2
geom -V licon1 li1 ntap - licon1_li1_ntap,111,i,2
geom -V licon1 li1 nsd - licon1_li1_nsd,111,i,2
geom -V licon1 li1 psd - licon1_li1_psd,111,i,2
geom -V poly_0licon1 li1 poly - poly_0licon1,111,i,2
geom -V mcon met1 li1 - mcon,111,i,2
geom -V via met2 met1 - via,111,i,2
geom -V via2 met3 met2 - via2,111,i,2
geom -V via3 met4 met3 - via3,111,i,2
geom -V pwell_0all ptap - pwell_0all_ptap_ovia,11,i,1
geom -V nwell ntap - nwell_ntap_ovia,11,i,1
/bin/mv -f nwell_orig nwell

#==========================================================#
# Flatten net file, routing, via and device layers
#==========================================================#

SAVEDIR=`beginFlattenInputs`
export SAVEDIR
/bin/mv -f NET h_NET
flatnet -V -li -h '/' h_NET NET
netprint -V -N1 power_list:power_list_nums NET
flattenTransistorData nfet_001v8_0rec meters
flattenTransistorData pfet_001v8_0rec meters
flattenCapData capacitor meters
flattenLayers -m licon1 met4 met3 met2 met1 li1 poly gate nfet pfet \
	nSourceDrain ntap pSourceDrain ptap nwell met3_bottom_0plate_ovia \
	bottom_0plate met3_met3_bottom_0plate_butt_ovia \
	met3_bottom_0plate_butt bottom_0plate_met3_bottom_0plate_butt_ovia \
	met4_top_0plate_ovia top_0plate met4_met4_top_0plate_butt_ovia \
	met4_top_0plate_butt top_0plate_met4_top_0plate_butt_ovia \
	licon1_li1_pSourceDrain licon1_li1_nSourceDrain licon1_li1_ptap \
	licon1_li1_ntap licon1_li1_nsd nsd licon1_li1_psd psd poly_0licon1 \
	mcon via via2 via3 pwell_0all_ptap_ovia pwell_0all nwell_ntap_ovia
endFlattenInputs

#==========================================================#
# Initialize CAP_GROUND variable
#==========================================================#

CAP_GROUND=`findCapGround -g VSS! NET`
echo "CAP_GROUND=" ${CAP_GROUND}
export CAP_GROUND
#mergelayers=pfet,nfet,gate
#mergelayersf=poly
geom pfet,nfet,gate,poly - poly,1,i,1
/bin/mv pfet pfet_orig
createEmptyLayer pfet
/bin/mv nfet nfet_orig
createEmptyLayer nfet
/bin/mv gate gate_orig
createEmptyLayer gate
reconnect -cgnd ${CAP_GROUND} -float floatlvsnetsfile -tf \
	nfet_001v8_0rec,pfet_001v8_0rec -cf capacitor -probe \
	text_met4:met4:text_met4_fvia,text_met3:met3:text_met3_fvia,text_met2:met2:text_met2_fvia,text_met1:met1:text_met1_fvia
geom nfet_001v8_0rec,pfet_001v8_0rec - qrcgate,1,i,1
iprint -imerge power_list_nums floatlvsnetsfile power_list_nums2
mv power_list_nums power_list_nums_orig
cp power_list_nums2 power_list_nums 

#==========================================================#
# Segregate interconnect into resistive and non-resistive
#==========================================================#

selectNetsByNumber power_list_nums bottom_0plate p_rbottom_0plate np_rbottom_0plate
selectNetsByNumber power_list_nums gate p_rgate np_rgate
selectNetsByNumber power_list_nums li1 p_rli1 np_rli1
selectNetsByNumber power_list_nums met1 p_rmet1 np_rmet1
selectNetsByNumber power_list_nums met2 p_rmet2 np_rmet2
selectNetsByNumber power_list_nums met3 p_rmet3 np_rmet3
selectNetsByNumber power_list_nums met3_bottom_0plate_butt p_rmet3_bottom_0plate_butt np_rmet3_bottom_0plate_butt
selectNetsByNumber power_list_nums met4 p_rmet4 np_rmet4
selectNetsByNumber power_list_nums met4_top_0plate_butt p_rmet4_top_0plate_butt np_rmet4_top_0plate_butt
selectNetsByNumber power_list_nums nSourceDrain p_rnSourceDrain np_rnSourceDrain
selectNetsByNumber power_list_nums nfet p_rnfet np_rnfet
selectNetsByNumber power_list_nums nsd p_rnsd np_rnsd
selectNetsByNumber power_list_nums ntap p_rntap np_rntap
selectNetsByNumber power_list_nums nwell p_rnwell np_rnwell
selectNetsByNumber power_list_nums pSourceDrain p_rpSourceDrain np_rpSourceDrain
selectNetsByNumber power_list_nums pfet p_rpfet np_rpfet
selectNetsByNumber power_list_nums poly p_rpoly np_rpoly
selectNetsByNumber power_list_nums psd p_rpsd np_rpsd
selectNetsByNumber power_list_nums ptap p_rptap np_rptap
selectNetsByNumber power_list_nums pwell_0all p_rpwell_0all np_rpwell_0all
selectNetsByNumber power_list_nums top_0plate p_rtop_0plate np_rtop_0plate
selectNetsByNumber power_list_nums pfet p_rpfet np_rpfet
selectNetsByNumber power_list_nums nfet p_rnfet np_rnfet
selectNetsByNumber power_list_nums gate p_rgate np_rgate
selectNetsByNumber power_list_nums gate p_rgate np_rgate
selectNetsByNumber power_list_nums pfet p_rpfet np_rpfet
selectNetsByNumber power_list_nums pfet p_rpfet np_rpfet
selectNetsByNumber power_list_nums nfet p_rnfet np_rnfet
selectNetsByNumber power_list_nums pfet p_rpfet np_rpfet
selectNetsByNumber power_list_nums nfet p_rnfet np_rnfet
selectNetsByNumber power_list_nums gate p_rgate np_rgate
selectNetsByNumber power_list_nums gate p_rgate np_rgate
selectNetsByNumber power_list_nums gate p_rgate np_rgate
selectNetsByNumber power_list_nums pfet p_rpfet np_rpfet
selectNetsByNumber power_list_nums pfet p_rpfet np_rpfet
selectNetsByNumber power_list_nums pfet p_rpfet np_rpfet
selectNetsByNumber power_list_nums pfet p_rpfet np_rpfet
selectNetsByNumber power_list_nums nfet p_rnfet np_rnfet
selectNetsByNumber power_list_nums nfet p_rnfet np_rnfet
selectNetsByNumber power_list_nums mcon p_rmcon np_rmcon
selectNetsByNumber power_list_nums poly_0licon1 p_rpoly_0licon1 np_rpoly_0licon1
selectNetsByNumber power_list_nums via p_rvia np_rvia
selectNetsByNumber power_list_nums via2 p_rvia2 np_rvia2
selectNetsByNumber power_list_nums via3 p_rvia3 np_rvia3
mv power_list_nums_orig power_list_nums

#==========================================================#
# Create resistor cut regions between resistive
# interconnect levels
#==========================================================#

mergevia -V -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt np_rmcon rmcon - np_rmet1 np_rli1
mergevia -V -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt np_rpoly_0licon1 rpoly_0licon1 - np_rli1 np_rpoly
mergevia -V -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt np_rvia rvia - np_rmet2 np_rmet1
mergevia -V -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt np_rvia2 rvia2 - np_rmet3 np_rmet2
mergevia -V -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt np_rvia3 rvia3 - np_rmet4 np_rmet3

#==========================================================#
# Create resistive interconnect MOSFET terminals
#==========================================================#

createMosfetGateTerminal nfet_001v8_0rec np_rpoly nfet_001v8_0rec_mgvia
createMosfetGateTerminal pfet_001v8_0rec np_rpoly pfet_001v8_0rec_mgvia

#==========================================================#
# Assign net numbers to cut regions
#==========================================================#

/bin/mv -f np_rnwell np_rnwell.conn_orig
createEmptyLayer np_rnwell
connect -V -relocate NET np_rnSourceDrain:np_rnSourceDrain.conn \
	np_rntap:np_rntap.conn np_rpSourceDrain:np_rpSourceDrain.conn \
	np_rptap:np_rptap.conn np_rbottom_0plate:np_rbottom_0plate.conn \
	np_rmet3_bottom_0plate_butt:np_rmet3_bottom_0plate_butt.conn \
	np_rmet4_top_0plate_butt:np_rmet4_top_0plate_butt.conn \
	np_rnsd:np_rnsd.conn np_rnwell:np_rnwell.conn np_rpsd:np_rpsd.conn \
	np_rpwell_0all:np_rpwell_0all.conn np_rtop_0plate:np_rtop_0plate.conn \
	rmcon rpoly_0licon1 rvia rvia2 rvia3 nfet_001v8_0rec_mgvia \
	pfet_001v8_0rec_mgvia - \
	bottom_0plate_met3_bottom_0plate_butt_ovia,5,6 nwell_ntap_ovia,9,2 \
	pwell_0all_ptap_ovia,11,4 top_0plate_met4_top_0plate_butt_ovia,12,7 -

#==========================================================#
# Assign net numbers to resistor vias
#==========================================================#

geom -V licon1_li1_nSourceDrain np_rnSourceDrain.conn - tmp_rlicon1_li1_nSourceDrain,11,i,2
mergevia -V -i -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt tmp_rlicon1_li1_nSourceDrain rlicon1_li1_nSourceDrain - np_rli1 \
	np_rnSourceDrain
/bin/rm -f tmp_rlicon1_li1_nSourceDrain
geom -V licon1_li1_nsd np_rnsd.conn - tmp_rlicon1_li1_nsd,11,i,2
mergevia -V -i -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt tmp_rlicon1_li1_nsd rlicon1_li1_nsd - np_rli1 np_rnsd
/bin/rm -f tmp_rlicon1_li1_nsd
geom -V licon1_li1_ntap np_rntap.conn - tmp_rlicon1_li1_ntap,11,i,2
mergevia -V -i -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt tmp_rlicon1_li1_ntap rlicon1_li1_ntap - np_rli1 np_rntap
/bin/rm -f tmp_rlicon1_li1_ntap
geom -V licon1_li1_pSourceDrain np_rpSourceDrain.conn - tmp_rlicon1_li1_pSourceDrain,11,i,2
mergevia -V -i -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt tmp_rlicon1_li1_pSourceDrain rlicon1_li1_pSourceDrain - np_rli1 \
	np_rpSourceDrain
/bin/rm -f tmp_rlicon1_li1_pSourceDrain
geom -V licon1_li1_psd np_rpsd.conn - tmp_rlicon1_li1_psd,11,i,2
mergevia -V -i -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt tmp_rlicon1_li1_psd rlicon1_li1_psd - np_rli1 np_rpsd
/bin/rm -f tmp_rlicon1_li1_psd
geom -V licon1_li1_ptap np_rptap.conn - tmp_rlicon1_li1_ptap,11,i,2
mergevia -V -i -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt tmp_rlicon1_li1_ptap rlicon1_li1_ptap - np_rli1 np_rptap
/bin/rm -f tmp_rlicon1_li1_ptap
geom -V met3_bottom_0plate_ovia np_rbottom_0plate.conn - tmp_rmet3_bottom_0plate_ovia,11,i,2
mergevia -V -i -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt tmp_rmet3_bottom_0plate_ovia rmet3_bottom_0plate_ovia - np_rmet3 \
	np_rbottom_0plate
/bin/rm -f tmp_rmet3_bottom_0plate_ovia
geom -V met3_met3_bottom_0plate_butt_ovia np_rmet3_bottom_0plate_butt.conn - tmp_rmet3_met3_bottom_0plate_butt_ovia,11,i,2
[ -r rmet3_met3_bottom_0plate_butt_ovia ] && /bin/rm -f rmet3_met3_bottom_0plate_butt_ovia
/bin/mv -f tmp_rmet3_met3_bottom_0plate_butt_ovia rmet3_met3_bottom_0plate_butt_ovia
geom -V met4_met4_top_0plate_butt_ovia np_rmet4_top_0plate_butt.conn - tmp_rmet4_met4_top_0plate_butt_ovia,11,i,2
[ -r rmet4_met4_top_0plate_butt_ovia ] && /bin/rm -f rmet4_met4_top_0plate_butt_ovia
/bin/mv -f tmp_rmet4_met4_top_0plate_butt_ovia rmet4_met4_top_0plate_butt_ovia
geom -V met4_top_0plate_ovia np_rtop_0plate.conn - tmp_rmet4_top_0plate_ovia,11,i,2
mergevia -V -i -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-cnt tmp_rmet4_top_0plate_ovia rmet4_top_0plate_ovia - np_rmet4 \
	np_rtop_0plate
/bin/rm -f tmp_rmet4_top_0plate_ovia

#==========================================================#
# Assign net numbers to nonresistive layers
#==========================================================#

epick -V -reo -e rlicon1_li1_nSourceDrain -e rlicon1_li1_nsd -e \
	rlicon1_li1_ntap -e rlicon1_li1_pSourceDrain -e rlicon1_li1_psd -e \
	rlicon1_li1_ptap -e rmet3_bottom_0plate_ovia -e \
	rmet3_met3_bottom_0plate_butt_ovia -e rmet4_met4_top_0plate_butt_ovia \
	-e rmet4_top_0plate_ovia np_rnSourceDrain.conn tmp_nSourceDrain
epick -V -reo -e tmp_nSourceDrain -c np_rnSourceDrain.conn tmp1_nSourceDrain
geom -V tmp1_nSourceDrain np_rnSourceDrain - tmp1_nSourceDrain,11,i,2
geom -V tmp_nSourceDrain,tmp1_nSourceDrain - np_rnSourceDrain,1,i,1
/bin/rm -f tmp_nSourceDrain tmp1_nSourceDrain
epick -V -reo -e rlicon1_li1_nSourceDrain -e rlicon1_li1_nsd -e \
	rlicon1_li1_ntap -e rlicon1_li1_pSourceDrain -e rlicon1_li1_psd -e \
	rlicon1_li1_ptap -e rmet3_bottom_0plate_ovia -e \
	rmet3_met3_bottom_0plate_butt_ovia -e rmet4_met4_top_0plate_butt_ovia \
	-e rmet4_top_0plate_ovia np_rntap.conn tmp_ntap
epick -V -reo -e tmp_ntap -c np_rntap.conn tmp1_ntap
geom -V tmp1_ntap np_rntap - tmp1_ntap,11,i,2
geom -V tmp_ntap,tmp1_ntap - np_rntap,1,i,1
/bin/rm -f tmp_ntap tmp1_ntap
epick -V -reo -e rlicon1_li1_nSourceDrain -e rlicon1_li1_nsd -e \
	rlicon1_li1_ntap -e rlicon1_li1_pSourceDrain -e rlicon1_li1_psd -e \
	rlicon1_li1_ptap -e rmet3_bottom_0plate_ovia -e \
	rmet3_met3_bottom_0plate_butt_ovia -e rmet4_met4_top_0plate_butt_ovia \
	-e rmet4_top_0plate_ovia np_rpSourceDrain.conn tmp_pSourceDrain
epick -V -reo -e tmp_pSourceDrain -c np_rpSourceDrain.conn tmp1_pSourceDrain
geom -V tmp1_pSourceDrain np_rpSourceDrain - tmp1_pSourceDrain,11,i,2
geom -V tmp_pSourceDrain,tmp1_pSourceDrain - np_rpSourceDrain,1,i,1
/bin/rm -f tmp_pSourceDrain tmp1_pSourceDrain
epick -V -reo -e rlicon1_li1_nSourceDrain -e rlicon1_li1_nsd -e \
	rlicon1_li1_ntap -e rlicon1_li1_pSourceDrain -e rlicon1_li1_psd -e \
	rlicon1_li1_ptap -e rmet3_bottom_0plate_ovia -e \
	rmet3_met3_bottom_0plate_butt_ovia -e rmet4_met4_top_0plate_butt_ovia \
	-e rmet4_top_0plate_ovia np_rptap.conn tmp_ptap
epick -V -reo -e tmp_ptap -c np_rptap.conn tmp1_ptap
geom -V tmp1_ptap np_rptap - tmp1_ptap,11,i,2
geom -V tmp_ptap,tmp1_ptap - np_rptap,1,i,1
/bin/rm -f tmp_ptap tmp1_ptap
epick -V -reo -e rlicon1_li1_nSourceDrain -e rlicon1_li1_nsd -e \
	rlicon1_li1_ntap -e rlicon1_li1_pSourceDrain -e rlicon1_li1_psd -e \
	rlicon1_li1_ptap -e rmet3_bottom_0plate_ovia -e \
	rmet3_met3_bottom_0plate_butt_ovia -e rmet4_met4_top_0plate_butt_ovia \
	-e rmet4_top_0plate_ovia np_rnwell.conn tmp_nwell
epick -V -reo -e tmp_nwell -c np_rnwell.conn tmp1_nwell
geom -V tmp1_nwell np_rnwell - tmp1_nwell,11,i,2
geom -V tmp_nwell,tmp1_nwell - np_rnwell,1,i,1
/bin/rm -f tmp_nwell tmp1_nwell
epick -V -reo -e rlicon1_li1_nSourceDrain -e rlicon1_li1_nsd -e \
	rlicon1_li1_ntap -e rlicon1_li1_pSourceDrain -e rlicon1_li1_psd -e \
	rlicon1_li1_ptap -e rmet3_bottom_0plate_ovia -e \
	rmet3_met3_bottom_0plate_butt_ovia -e rmet4_met4_top_0plate_butt_ovia \
	-e rmet4_top_0plate_ovia np_rbottom_0plate.conn tmp_bottom_0plate
epick -V -reo -e tmp_bottom_0plate -c np_rbottom_0plate.conn tmp1_bottom_0plate
geom -V tmp1_bottom_0plate np_rbottom_0plate - tmp1_bottom_0plate,11,i,2
geom -V tmp_bottom_0plate,tmp1_bottom_0plate - np_rbottom_0plate,1,i,1
/bin/rm -f tmp_bottom_0plate tmp1_bottom_0plate
epick -V -reo -e rlicon1_li1_nSourceDrain -e rlicon1_li1_nsd -e \
	rlicon1_li1_ntap -e rlicon1_li1_pSourceDrain -e rlicon1_li1_psd -e \
	rlicon1_li1_ptap -e rmet3_bottom_0plate_ovia -e \
	rmet3_met3_bottom_0plate_butt_ovia -e rmet4_met4_top_0plate_butt_ovia \
	-e rmet4_top_0plate_ovia np_rpwell_0all.conn tmp_pwell_0all
epick -V -reo -e tmp_pwell_0all -c np_rpwell_0all.conn tmp1_pwell_0all
geom -V tmp1_pwell_0all np_rpwell_0all - tmp1_pwell_0all,11,i,2
geom -V tmp_pwell_0all,tmp1_pwell_0all - np_rpwell_0all,1,i,1
/bin/rm -f tmp_pwell_0all tmp1_pwell_0all
epick -V -reo -e rlicon1_li1_nSourceDrain -e rlicon1_li1_nsd -e \
	rlicon1_li1_ntap -e rlicon1_li1_pSourceDrain -e rlicon1_li1_psd -e \
	rlicon1_li1_ptap -e rmet3_bottom_0plate_ovia -e \
	rmet3_met3_bottom_0plate_butt_ovia -e rmet4_met4_top_0plate_butt_ovia \
	-e rmet4_top_0plate_ovia np_rtop_0plate.conn tmp_top_0plate
epick -V -reo -e tmp_top_0plate -c np_rtop_0plate.conn tmp1_top_0plate
geom -V tmp1_top_0plate np_rtop_0plate - tmp1_top_0plate,11,i,2
geom -V tmp_top_0plate,tmp1_top_0plate - np_rtop_0plate,1,i,1
/bin/rm -f tmp_top_0plate tmp1_top_0plate

#==========================================================#
# Process text layers
#==========================================================#

flatlabel -V  -tc -F -l flatlabel.info text_met4,text_met3,text_met2,text_met1 L1T0,L2T0,L3T0,L4T0
/bin/mv -f np_rnwell.conn_orig np_rnwell

#==========================================================#
# Parasitic R extraction with default precision
#==========================================================#

rex -V -m -pd -I'#' -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-medge np_rnwell -map p2elayermapfile -N NET -e2 -P \
	nfet_001v8_0rec_mgvia,pfet_001v8_0rec_mgvia -rP res.mod \
	np_rpfet::pfet_cut np_rnfet::nfet_cut np_rgate::gate_cut \
	np_rpoly::poly_cut np_rli1::li_cut np_rmet1::metal1_cut \
	np_rmet2::metal2_cut np_rmet3::metal3_cut np_rmet4::metal4_cut - \
	rlicon1_li1_nSourceDrain,5,t rlicon1_li1_nsd,5,t rlicon1_li1_ntap,5,t \
	rlicon1_li1_pSourceDrain,5,t rlicon1_li1_psd,5,t rlicon1_li1_ptap,5,t \
	rmcon,5,6,t rmet3_bottom_0plate_ovia,8 \
	rmet3_met3_bottom_0plate_butt_ovia,8 \
	rmet4_met4_top_0plate_butt_ovia,9 rmet4_top_0plate_ovia,9 \
	rpoly_0licon1,4,5,t rvia,6,7,t rvia2,7,8,t rvia3,8,9,t \
	nfet_001v8_0rec_mgvia,4,z pfet_001v8_0rec_mgvia,4,z - L1T0,9,I \
	L2T0,8,I L3T0,7,I L4T0,6,I
/bin/cp -f np_rnwell np_rnwell.conn

#==========================================================#
# Combine power non-power
#==========================================================#

/bin/rm -f bottom_0plate
geom np_rbottom_0plate,p_rbottom_0plate - bottom_0plate,1,i,1
/bin/rm -f nSourceDrain
geom np_rnSourceDrain,p_rnSourceDrain - nSourceDrain,1,i,1
/bin/rm -f nwell
geom np_rnwell,p_rnwell - nwell,1,i,1
/bin/rm -f pSourceDrain
geom np_rpSourceDrain,p_rpSourceDrain - pSourceDrain,1,i,1
/bin/rm -f poly
geom np_rpoly,p_rpoly - poly,1,i,1
/bin/rm -f pwell_0all
geom np_rpwell_0all,p_rpwell_0all - pwell_0all,1,i,1
/bin/rm -f top_0plate
geom np_rtop_0plate,p_rtop_0plate - top_0plate,1,i,1

#==========================================================#
# Reconnect MOSFET devices
#==========================================================#

reconnect -V -n NET -se2 mwires.res -t \
	nfet_001v8_0rec.trans:nfet_001v8_0rec.transr nfet_001v8_0rec \
	nSourceDrain,nfet_001v8_0rec_mgvia,pwell_0all -t \
	pfet_001v8_0rec.trans:pfet_001v8_0rec.transr pfet_001v8_0rec \
	pSourceDrain,pfet_001v8_0rec_mgvia,nwell
changeTransFileNameAP nfet_001v8_0rec.trans nfet_001v8_0rec.transr
changeTransFileNameAP pfet_001v8_0rec.trans pfet_001v8_0rec.transr

#==========================================================#
# Reconnect CAP devices
#==========================================================#

createLink top_0plate capacitor_top_0plate_cvia
createLink bottom_0plate capacitor_bottom_0plate_cvia
reconnect -V -se2 cwires.res -n NET -c capacitor.cpax:capacitor.cpaxr \
	capacitor capacitor_top_0plate_cvia,capacitor_bottom_0plate_cvia

#==========================================================#
# Form capacitance layers for resistive process layers
#==========================================================#

geom -V -i p_rpoly,p_rgate,p_rnfet,p_rpfet,np_rpoly,np_rgate,np_rnfet,np_rpfet - so_poly,1,n
geom -V -i p_rpoly,p_rgate,p_rnfet,p_rpfet,np_rpoly,np_rgate,np_rnfet,np_rpfet - poly,1,n
geom -V -i poly_cut,gate_cut,nfet_cut,pfet_cut - poly_cut,1,n
geom -V -i p_rli1,np_rli1 - so_li,1,n
geom -V p_rli1,np_rli1 - li,1,i,1
geom -V -i p_rmet1,np_rmet1 - so_metal1,1,n
geom -V p_rmet1,np_rmet1 - metal1,1,i,1
geom -V -i p_rmet2,np_rmet2 - so_metal2,1,n
geom -V p_rmet2,np_rmet2 - metal2,1,i,1
geom -V -i p_rmet3,np_rmet3 - so_metal3,1,n
geom -V p_rmet3,np_rmet3 - metal3,1,i,1
geom -V -i p_rmet4,np_rmet4 - so_metal4,1,n
geom -V p_rmet4,np_rmet4 - metal4,1,i,1

#==========================================================#
# Form capacitance layers for non-resistive process layers
#==========================================================#

emerge -V p_rntap np_rntap ntap
emerge -V p_rptap np_rptap ptap
grow -V .001 nSourceDrain mask
geom -V ntap mask - ntap,10,i,1
grow -V .001 ntap g_ntap
geom -V mask,g_ntap - mask,1
geom -V pSourceDrain mask - pSourceDrain,10,i,1
grow -V .001 pSourceDrain g_pSourceDrain
geom -V mask,g_pSourceDrain - mask,1
geom -V ptap mask - ptap,10,i,1
geom -V nSourceDrain,ntap,pSourceDrain,ptap - diff,1,i,1
createEmptyLayer metal5

#==========================================================#
# Form substrate
#==========================================================#

geom -V p_rnwell,np_rnwell - nwell,1,i,1
/bin/cp -f nwell nwell.df2
xytoebbox -V -g 16.002 -e metal5,metal4,metal3,metal2,metal1,li,poly,diff,nwell xg_nwell
grow -V 0.001 nwell g_nwell
geom -V xg_nwell g_nwell - tmp_nwell,10
epick -V -reo -D ${CAP_GROUND} tmp_nwell pick_nwell
grow -V -m 0.002 nwell g_nwell
stamp -i g_nwell pick_nwell
emerge -V pick_nwell nwell tmp1_nwell
geom -V tmp1_nwell - nwell,1,i,1
/bin/rm -f g_nwell xg_nwell tmp_nwell tmp1_nwell
geom -V nwell - FOX,1,i,1
geom -V FOX diff - FOX,10,i,1

#==========================================================#
# Perform Marker processing
#==========================================================#

geom poly nfet_001v8_0rec,pfet_001v8_0rec - poly,11,i,1
geom nfet_001v8_0rec,pfet_001v8_0rec - qrcgate,1,i,1
netprint -max NET > maxnetfile
/bin/rm -f lvsblockingmaxnet lvsblockingmap
grow -m .001 nfet nfet__g
geom poly nfet__g - poly_out,10,i,1
geom poly nfet - poly_in,11,i,1
relocate -net NET -lvs 1,lvsblockingmaxnet,lvsblockingmap poly_in
geom poly_in,poly_out - poly,1,i,1
grow -m .001 pfet pfet__g
geom poly pfet__g - poly_out,10,i,1
geom poly pfet - poly_in,11,i,1
relocate -net NET -lvs 2,lvsblockingmaxnet,lvsblockingmap poly_in
geom poly_in,poly_out - poly,1,i,1

#==========================================================#
# Create sip/sw3d/cn3d capacitance data files
#==========================================================#

cat <<ENDCAT> sip.cmd
sip -V -cgnd ${CAP_GROUND} -s -o -sub 2 -mlc metal3,metal4 -n 8 -i 0,8.001 -b \
	metal4,metal3,metal2,metal1,li,poly,diff,FOX -j 0.8 -Maxw 12 -p \
	metal5,key 0,8 - metal5.sip
sip -V -cgnd ${CAP_GROUND} -s -o -sub 2 -cp poly,allGates,diff -n 2.1 -i \
	0,2.101 -b diff,FOX -t li,metal1,metal2,metal3,metal4,metal5 -j 0.15 \
	-Maxw 2.25 -p poly,key 0,2.1 - poly.sip
sip -V -cgnd ${CAP_GROUND} -s -o -sub 2 -mlc poly -n 1.4 -i 0,1.401 -b \
	poly,diff,FOX -t metal1,metal2,metal3,metal4,metal5 -j 0.14 -Maxw 2.1 \
	-p li,key 0,1.4 - li.sip
sip -V -cgnd ${CAP_GROUND} -s -o -sub 2 -mlc poly,li -n 1.4 -i 0,1.401 -b \
	li,poly,diff,FOX -t metal2,metal3,metal4,metal5 -j 0.14 -Maxw 2.1 -p \
	metal1,key 0,1.4 - metal1.sip
sip -V -cgnd ${CAP_GROUND} -s -o -sub 2 -mlc li,metal1 -n 2.8 -i 0,2.801 -b \
	metal1,li,poly,diff,FOX -t metal3,metal4,metal5 -j 0.14 -Maxw 2.1 -p \
	metal2,key 0,2.8 - metal2.sip
sip -V -cgnd ${CAP_GROUND} -s -o -sub 2 -mlc metal1,metal2 -n 3 -i 0,3.001 -b \
	metal2,metal1,li,poly,diff,FOX -t metal4,metal5 -j 0.3 -Maxw 4.5 -p \
	metal3,key 0,3 - metal3.sip
sip -V -cgnd ${CAP_GROUND} -s -o -sub 2 -mlc metal2,metal3 -n 6 -i 0,6.001 -b \
	metal3,metal2,metal1,li,poly,diff,FOX -t metal5 -j 0.3 -Maxw 4.5 -p \
	metal4,key 0,6 - metal4.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -L3A -h -b \
	metal3,metal2,metal1,li,poly,diff,FOX -Maxw 12 -p \
	metal4:metal4_cut,key,metal5,key 0,8,0 - metal4_metal5.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -L3A -h -R metal5 -b \
	metal2,metal1,li,poly,diff,FOX -k metal4:0.845 -Maxw 12 -p \
	metal3:metal3_cut,key,metal5,key 0,8,0 - metal3_metal5.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -h -b metal2,metal1,li,poly,diff,FOX -t \
	metal5 -Maxw 4.5 -p metal3:metal3_cut,key,metal4:metal4_cut,key 0,6,0 \
	- metal3_metal4.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -L3A -h -R metal4 -b \
	metal1,li,poly,diff,FOX -t metal5 -k metal3:0.845 -Maxw 4.5 -p \
	metal2:metal2_cut,key,metal4:metal4_cut,key 0,6,0 - metal2_metal4.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -h -b metal1,li,poly,diff,FOX -t \
	metal4,metal5 -Maxw 4.5 -p \
	metal2:metal2_cut,key,metal3:metal3_cut,key 0,3,0 - metal2_metal3.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -L3A -h -R metal3 -b li,poly,diff,FOX -t \
	metal4,metal5 -k metal2:0.36 -Maxw 4.5 -p \
	metal1:metal1_cut,key,metal3:metal3_cut,key 0,3,0 - metal1_metal3.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -h -b li,poly,diff,FOX -t \
	metal3,metal4,metal5 -Maxw 2.1 -p \
	metal1:metal1_cut,key,metal2:metal2_cut,key 0,2.8,0 - \
	metal1_metal2.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -L3A -h -R metal2 -b poly,diff,FOX -t \
	metal3,metal4,metal5 -k metal1:0.36 -Maxw 2.1 -p \
	li:li_cut,key,metal2:metal2_cut,key 0,2.8,0 - li_metal2.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -h -b poly,diff,FOX -t \
	metal2,metal3,metal4,metal5 -Maxw 2.1 -p \
	li:li_cut,key,metal1:metal1_cut,key 0,1.4,0 - li_metal1.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -L3A -h -R metal1 -b diff,FOX -t \
	metal2,metal3,metal4,metal5 -k li:0.1 -Maxw 2.25 -p \
	poly:poly_cut,key,metal1:metal1_cut,key 0,2.1,0 - poly_metal1.sip
sip -V -s -cgnd ${CAP_GROUND} -sub 2 -h -R li,poly -b diff,FOX -t \
	metal1,metal2,metal3,metal4,metal5 -Maxw 2.25 -p \
	poly:poly_cut,key,li:li_cut,key 0,2.1,0 - poly_li.sip
sw3d -V -cgnd ${CAP_GROUND} -sub 2 -b metal3,metal2,metal1,li,poly,diff,FOX \
	-p metal4:metal4_cut,metal5 - metal4_metal5.sw3d
sw3d -V -cgnd ${CAP_GROUND} -sub 2 -b metal2,metal1,li,poly,diff,FOX -t \
	metal5 -p metal3:metal3_cut,metal4:metal4_cut - metal3_metal4.sw3d
sw3d -V -cgnd ${CAP_GROUND} -sub 2 -b metal1,li,poly,diff,FOX -t \
	metal4,metal5 -p metal2:metal2_cut,metal3:metal3_cut - \
	metal2_metal3.sw3d
sw3d -V -cgnd ${CAP_GROUND} -sub 2 -b li,poly,diff,FOX -t \
	metal3,metal4,metal5 -p metal1:metal1_cut,metal2:metal2_cut - \
	metal1_metal2.sw3d
sw3d -V -cgnd ${CAP_GROUND} -sub 2 -b poly,diff,FOX -t \
	metal2,metal3,metal4,metal5 -p li:li_cut,metal1:metal1_cut - \
	li_metal1.sw3d
sw3d -V -cgnd ${CAP_GROUND} -sub 2 -b diff,FOX -t \
	metal1,metal2,metal3,metal4,metal5 -p poly:poly_cut,li:li_cut - \
	poly_li.sw3d
ENDCAT

#==========================================================#
# Prepare canonical capfiles
#==========================================================#


#==========================================================#
# Prepare gate capacitance blocking layers
#==========================================================#

emerge -V nfet_001v8_0rec pfet_001v8_0rec allGates

#==========================================================#
# Perform Marker Via Preparation
#==========================================================#


#==========================================================#
# Run pax16 to generate capfile
#==========================================================#

pax16 -V -lee_off -gnd ${CAP_GROUND} -rmselfC -ignore_cf_table -scf sip.cmd \
	-filterfile maxnetfile -rP \
	np_rmet4.res,np_rmet3.res,np_rmet2.res,np_rmet1.res,np_rli1.res,np_rpoly.res,np_rgate.res,np_rnfet.res,np_rpfet.res,mwires.res,cwires.res \
	-M_perim_off -c \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical/qrcTechFile \
	-f FOX diff poly:poly_cut li:li_cut metal1:metal1_cut \
	metal2:metal2_cut metal3:metal3_cut metal4:metal4_cut metal5 allGates \
	- \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical/qrcTechFile \
	- - NET - capfile
relocate -V -R lvsblockingmaxnet,lvsblockingmap -n NET poly
geom pfet_orig poly - pfet,11,i,2 poly,01,i,2
geom nfet_orig poly - nfet,11,i,2 poly,01,i,2
geom gate_orig poly - gate,11,i,2 poly,01,i,2

#==========================================================#
# Generate netlister data files
#==========================================================#

createCAPModelFile lvscap.mod1 cap_mim_m3__base 1 capacitor top_0plate bottom_0plate 

#==========================================================#
# Perform RC reduction
#==========================================================#

xreduce -V -mergecap -n NET -tech \
	/home/user22/Sky130_cadence_pdk/sky130_release_0.1.0/quantus/extraction/typical \
	-d1 -e \
	metal5,metal4,metal3,metal2,metal1,li,poly,diff,FOX,rmcon,rpoly_0licon1,rvia,rvia2,rvia3 \
	-sr -g ${CAP_GROUND},1.0 -danglingR -minR 0.1 -rP \
	np_rmet4.res,np_rmet3.res,np_rmet2.res,np_rmet1.res,np_rli1.res,np_rpoly.res,np_rgate.res,np_rnfet.res,np_rpfet.res,mwires.res,cwires.res \
	-minC 1e-15 -minCper 0.1 -cap capfile L1T0 L2T0 L3T0 L4T0 \
	nfet_001v8_0rec.transr pfet_001v8_0rec.transr capacitor.cpaxr

#==========================================================#
# Generate HSPICE file
#==========================================================#

advgen -V -g0 -li -f -n -o HSPICE -TL L1T0,L2T0,L3T0,L4T0 -nxref \
	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/CDAC_DEM.gnx \
	-dxref \
	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/CDAC_DEM.gdx \
	-addprefix -sc caps2dversion -mx capfile \
	metal5,metal4,metal3,metal2,metal1,li,poly,diff,FOX -rP res.mod \
	np_rmet4.res,Rnp_rmet4.dev2 np_rmet3.res,Rnp_rmet3.dev2 \
	np_rmet2.res,Rnp_rmet2.dev2 np_rmet1.res,Rnp_rmet1.dev2 \
	np_rli1.res,Rnp_rli1.dev2 np_rpoly.res,Rnp_rpoly.dev2 \
	np_rgate.res,Rnp_rgate.dev2 np_rnfet.res,Rnp_rnfet.dev2 \
	np_rpfet.res,Rnp_rpfet.dev2 -rP mwires.mod mwires.res,mwires.dev2 -rP \
	cwires.mod cwires.res,cwires.dev2 -ta lvsmos.mod,nfet_001v8_0rec.net \
	nfet_001v8_0rec.transr -ta lvsmos.mod,pfet_001v8_0rec.net \
	pfet_001v8_0rec.transr -pM lvscap.mod1,capacitor.net capacitor.cpaxr \
	- NET - \
	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/extview.tmp

#==========================================================#
# Create _save_layers file for Assura extracted view
#==========================================================#

geom metal4 np_rmet4 - np_rmet4,11,i,1
geom metal3 np_rmet3 - np_rmet3,11,i,1
geom metal2 np_rmet2 - np_rmet2,11,i,1
geom metal1 np_rmet1 - np_rmet1,11,i,1
geom li np_rli1 - np_rli1,11,i,1
geom poly np_rpoly - np_rpoly,11,i,1
geom poly np_rgate - np_rgate,11,i,1
geom poly np_rnfet - np_rnfet,11,i,1
geom poly np_rpfet - np_rpfet,11,i,1
stamp -i2 np_rmet1 rmcon np_rmcon
stamp -i2 np_rli1 rpoly_0licon1 np_rpoly_0licon1
stamp -i2 np_rmet2 rvia np_rvia
stamp -i2 np_rmet3 rvia2 np_rvia2
stamp -i2 np_rmet4 rvia3 np_rvia3
ereduce  rlicon1_li1_nSourceDrain rlicon1_li1_nSourceDrain.reduce
stamp -i  np_rli1 rlicon1_li1_nSourceDrain.reduce
stamp -i  rlicon1_li1_nSourceDrain.reduce rlicon1_li1_nSourceDrain
stamp -i  rlicon1_li1_nSourceDrain licon1_li1_nSourceDrain
/bin/rm -f rlicon1_li1_nSourceDrain.reduce
ereduce  rlicon1_li1_nsd rlicon1_li1_nsd.reduce
stamp -i  np_rli1 rlicon1_li1_nsd.reduce
stamp -i  rlicon1_li1_nsd.reduce rlicon1_li1_nsd
stamp -i  rlicon1_li1_nsd licon1_li1_nsd
/bin/rm -f rlicon1_li1_nsd.reduce
ereduce  rlicon1_li1_ntap rlicon1_li1_ntap.reduce
stamp -i  np_rli1 rlicon1_li1_ntap.reduce
stamp -i  rlicon1_li1_ntap.reduce rlicon1_li1_ntap
stamp -i  rlicon1_li1_ntap licon1_li1_ntap
/bin/rm -f rlicon1_li1_ntap.reduce
ereduce  rlicon1_li1_pSourceDrain rlicon1_li1_pSourceDrain.reduce
stamp -i  np_rli1 rlicon1_li1_pSourceDrain.reduce
stamp -i  rlicon1_li1_pSourceDrain.reduce rlicon1_li1_pSourceDrain
stamp -i  rlicon1_li1_pSourceDrain licon1_li1_pSourceDrain
/bin/rm -f rlicon1_li1_pSourceDrain.reduce
ereduce  rlicon1_li1_psd rlicon1_li1_psd.reduce
stamp -i  np_rli1 rlicon1_li1_psd.reduce
stamp -i  rlicon1_li1_psd.reduce rlicon1_li1_psd
stamp -i  rlicon1_li1_psd licon1_li1_psd
/bin/rm -f rlicon1_li1_psd.reduce
ereduce  rlicon1_li1_ptap rlicon1_li1_ptap.reduce
stamp -i  np_rli1 rlicon1_li1_ptap.reduce
stamp -i  rlicon1_li1_ptap.reduce rlicon1_li1_ptap
stamp -i  rlicon1_li1_ptap licon1_li1_ptap
/bin/rm -f rlicon1_li1_ptap.reduce
ereduce  rmet3_bottom_0plate_ovia rmet3_bottom_0plate_ovia.reduce
stamp -i  np_rmet3 rmet3_bottom_0plate_ovia.reduce
stamp -i  rmet3_bottom_0plate_ovia.reduce rmet3_bottom_0plate_ovia
stamp -i  rmet3_bottom_0plate_ovia met3_bottom_0plate_ovia
/bin/rm -f rmet3_bottom_0plate_ovia.reduce
ereduce  rmet3_met3_bottom_0plate_butt_ovia rmet3_met3_bottom_0plate_butt_ovia.reduce
stamp -i  np_rmet3 rmet3_met3_bottom_0plate_butt_ovia.reduce
stamp -i  rmet3_met3_bottom_0plate_butt_ovia.reduce rmet3_met3_bottom_0plate_butt_ovia
stamp -i  rmet3_met3_bottom_0plate_butt_ovia met3_met3_bottom_0plate_butt_ovia
/bin/rm -f rmet3_met3_bottom_0plate_butt_ovia.reduce
ereduce  rmet4_met4_top_0plate_butt_ovia rmet4_met4_top_0plate_butt_ovia.reduce
stamp -i  np_rmet4 rmet4_met4_top_0plate_butt_ovia.reduce
stamp -i  rmet4_met4_top_0plate_butt_ovia.reduce rmet4_met4_top_0plate_butt_ovia
stamp -i  rmet4_met4_top_0plate_butt_ovia met4_met4_top_0plate_butt_ovia
/bin/rm -f rmet4_met4_top_0plate_butt_ovia.reduce
ereduce  rmet4_top_0plate_ovia rmet4_top_0plate_ovia.reduce
stamp -i  np_rmet4 rmet4_top_0plate_ovia.reduce
stamp -i  rmet4_top_0plate_ovia.reduce rmet4_top_0plate_ovia
stamp -i  rmet4_top_0plate_ovia met4_top_0plate_ovia
/bin/rm -f rmet4_top_0plate_ovia.reduce
cat <<ENDCAT> _save_layers
FOX nwell
metal5 metal5
diff np_rptap p_rptap np_rpSourceDrain p_rpSourceDrain np_rntap p_rntap np_rnSourceDrain p_rnSourceDrain
licon1 licon1_li1_psd licon1_li1_nsd licon1_li1_ntap licon1_li1_ptap licon1_li1_nSourceDrain licon1_li1_pSourceDrain
met4 np_rmet4 p_rmet4
met3 np_rmet3 p_rmet3
met2 np_rmet2 p_rmet2
met1 np_rmet1 p_rmet1
li1 np_rli1 p_rli1
poly np_rpoly p_rpoly
gate np_rgate p_rgate
nfet np_rnfet p_rnfet
pfet np_rpfet p_rpfet
nSourceDrain np_rnSourceDrain p_rnSourceDrain
ntap np_rntap p_rntap
pSourceDrain np_rpSourceDrain p_rpSourceDrain
ptap np_rptap p_rptap
nwell nwell.df2
met3_bottom_0plate_ovia met3_bottom_0plate_ovia
bottom_0plate np_rbottom_0plate p_rbottom_0plate
met3_met3_bottom_0plate_butt_ovia met3_met3_bottom_0plate_butt_ovia
met3_bottom_0plate_butt np_rmet3_bottom_0plate_butt p_rmet3_bottom_0plate_butt
bottom_0plate_met3_bottom_0plate_butt_ovia bottom_0plate_met3_bottom_0plate_butt_ovia
met4_top_0plate_ovia met4_top_0plate_ovia
top_0plate np_rtop_0plate p_rtop_0plate
met4_met4_top_0plate_butt_ovia met4_met4_top_0plate_butt_ovia
met4_top_0plate_butt np_rmet4_top_0plate_butt p_rmet4_top_0plate_butt
top_0plate_met4_top_0plate_butt_ovia top_0plate_met4_top_0plate_butt_ovia
nsd np_rnsd p_rnsd
psd np_rpsd p_rpsd
poly_0licon1 np_rpoly_0licon1 p_rpoly_0licon1
mcon np_rmcon p_rmcon
via np_rvia p_rvia
via2 np_rvia2 p_rvia2
via3 np_rvia3 p_rvia3
pwell_0all_ptap_ovia pwell_0all_ptap_ovia
pwell_0all np_rpwell_0all p_rpwell_0all
nwell_ntap_ovia nwell_ntap_ovia
ENDCAT
cat \
	/home/user22/NS_SAR_ADC/libraries/NS_SAR_Analog/CDAC_DEM/LVS/svdb/CDAC_DEM/hccisavefile \
	>> _save_layers

