<div align="right">
  <img src="../resources/silicon_edge_logo.png" alt="Silicon Edge Logo" height="80" />
</div>

# 8-Bit NS-SAR ADC Core: Timing Specification

**Datasheet Level: 1**  
**Document Revision:** 1.0  
**Designer:** Silicon_Edge

---

## 1. System Targets

| Parameter | Specification |
| :--- | :--- |
| **Target Output Data Rate** | 1 ksps |
| **Oversampling Ratio (OSR)** | 8 |
| **Target Sampling Rate** | 8 ksps |

## 2. Clock Cycle Allocation

| Description | Value |
| :--- | :--- |
| **Conversions per output code** | 8 conversions |
| **Cycles per A/D conversion** | 9 clock cycles |
| **Padding for Noise Shaping (NS)** | 3 clock cycles (average) |
| **Total cycles per conversion** | 12 clock cycles (average) |
| **Total cycles per output code** | 96 clock cycles |

## 3. Clock Frequency Requirements

| Parameter | Specification |
| :--- | :--- |
| **Required Clock Rate** | 96 kHz (Period ≈ 10.417 µs) |
| **Relaxed System Clock Input** | 100 kHz (Period = 10.0 µs) |
| **Output Data Rate @ 100 kHz** | ~1.042 ksps |

> **Note:** The system is designed for a nominal 96 kHz input clock, meanwhile relaxing the strict 96 kHz requirement to accommodate a 4.16% higher upper target capability of 100 kHz.

## 4. Timing Diagrams

### 4.1 Timing per Code Output

```text
/CONV0\/CONV1\/CONV2\/CONV3\/CONV4\/CONV5\/CONV6\/CONV7\
\     /\     /\     /\     /\     /\     /\     /\     /  
```
*\* CONV: Conversion (single 8-bit SAR resolution + NS loop)*

### 4.2 Timing per Conversion (Non-Overlapping)

```text
/SAMP\/BIT7\/BIT6\/BIT5\/BIT4\/BIT3\/BIT2\/BIT1\/BIT0\/ NS \/ NS \/ NS \
\    /\    /\    /\    /\    /\    /\    /\    /\    /\    /\    /\    /
```
*\* SAMP: Sample phase | BITx: Bit decision phase | NS: Noise shaping loop phase*

### 4.3 Timing per Conversion (Overlapped Architecture)
*An overlapped architecture variant can be considered to optimize timing:*

```text
/SAMP\/BIT7\/BIT6\/BIT5\/BIT4\/BIT3\/BIT2\/BIT1\/BIT0\/FIN \/SET \/    \
\    /\    /\    /\    /\    /\ NS /\ NS /\ NS /\ NS /\    /\    /\    /
```
*\* FIN: Final residue transfer into the integrator | SET: Integrator settling phase*

## 5. Asynchronous Design Notes
Non-overlapping clocks will be utilized for robust asynchronous event handling.