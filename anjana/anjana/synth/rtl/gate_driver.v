module gate_driver (
  input  SAMPLE, VREF,
  output SEL_VIN, SEL_VIN_N,
  output SEL_VREF_P, SEL_VREF_P_N,
  output SEL_VREF_N, SEL_VREF_N_N
);
  assign SEL_VIN      =  SAMPLE &  VREF;
  assign SEL_VIN_N    = ~SEL_VIN;
  assign SEL_VREF_P   = ~SAMPLE &  VREF;
  assign SEL_VREF_P_N = ~SEL_VREF_P;
  assign SEL_VREF_N   = ~SAMPLE & ~VREF;
  assign SEL_VREF_N_N = ~SEL_VREF_N;
endmodule
