// Verilog HDL for "NS_SAR_Analog", "gate_driver", "functional"

module gate_driver (
    output wire SEL_VIN,
    output wire SEL_VIN_N,
    output wire SEL_VREF_P,
    output wire SEL_VREF_P_N,
    output wire SEL_VREF_N,
    output wire SEL_VREF_N_N,

    input  wire SAMPLE,
    input  wire VREF
);

    // Functional model
    assign SEL_VIN    = SAMPLE & VREF;
    assign SEL_VREF_P = ~SAMPLE & VREF;
    assign SEL_VREF_N = ~(SAMPLE | VREF);

    assign SEL_VIN_N    = ~SEL_VIN;
    assign SEL_VREF_P_N = ~SEL_VREF_P;
    assign SEL_VREF_N_N = ~SEL_VREF_N;

endmodule