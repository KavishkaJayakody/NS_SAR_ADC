import numpy as np
import matplotlib.pyplot as plt

class PassiveSCFIR:
    """Models the passive SC FIR filter with 1-cycle and 2-cycle delays."""
    def __init__(self):
        self.z1 = 0.0  # Represents C_res1 (1-cycle delay)
        self.z2 = 0.0  # Represents C_res2 & C_delay (2-cycle delay)

    def step(self, x_in):
        # The paper specifies the filter transfer function: z^-1 - 0.5*z^-2
        out = self.z1 - 0.5 * self.z2
        
        # Clock updates (shifting states)
        self.z2 = self.z1
        self.z1 = x_in
        return out

class DynamicResidueAmp:
    """Models the comparator-reused D-amp with variable gain G."""
    def __init__(self, G=30.0):
        self.G = G

    def amplify(self, residue):
        # Amplifies the residual quantization voltage linearly
        return self.G * residue

class ChargeSharingSummation:
    """Models the passive charge sharing between the CDAC and FIR caps."""
    def __init__(self, A=1.0/16.0):
        self.A = A  # Attenuation factor defined by capacitor ratios

    def combine(self, v_in, v_fir):
        # STF = 1 - 2A for the input path, feedback path scales by attenuation A
        # From the paper diagram: V_in is scaled by (1 - 2A), and V_fir is subtracted by A
        v_dac = (1.0 - 2.0 * self.A) * v_in - self.A * v_fir
        return v_dac

class SARCore:
    """Models the 8-bit SAR ADC quantizer."""
    def __init__(self, n_bits=8, v_ref=1.0):
        self.n_bits = n_bits
        self.v_ref = v_ref
        self.lsb = v_ref / (2**n_bits)

    def convert(self, v_target):
        # Bounded ideal quantization to the configured SAR resolution
        full_scale = (2 ** (self.n_bits - 1)) * self.lsb

        if not np.isfinite(v_target):
            if np.isnan(v_target):
                v_target = full_scale
            else:
                v_target = np.copysign(full_scale, v_target)

        v_target = float(np.clip(v_target, -full_scale, full_scale - self.lsb))
        code = round(v_target / self.lsb)
        code = max(min(code, (2**(self.n_bits-1)) - 1), -(2**(self.n_bits-1)))
        
        v_dac_final = code * self.lsb
        quantization_error = v_target - v_dac_final
        return v_dac_final, quantization_error

# =====================================================================
# Simulation Setup
# =====================================================================
np.random.seed(42)
N_samples = 4096
OSR = 16
fs = 10e3  # 10 ksps sampling rate

# Input signal: Near full-scale sine wave inside the signal bandwidth (fs / (2 * OSR))
f_in = 123.45
t = np.arange(N_samples) / fs
v_in_seq = 0.8 * np.sin(2 * np.pi * f_in * t)

# Sub-block Instantiations using the paper's exact parameters
fir_filter = PassiveSCFIR()
d_amp = DynamicResidueAmp(G=30.0)             # G = 30
adder = ChargeSharingSummation(A=1.0/16.0)     # A = 1/16
sar = SARCore(n_bits=8)                        # 8b SAR

# K_EF = G * A = 30 * (1/16) = 1.875 (Optimum complex zeros configuration)
print(f"Configured Loop Gain K_EF: {d_amp.G * adder.A} (Target: 1.875)")

# Waveform tracers
node_v_dac = np.zeros(N_samples)
node_v_fir = np.zeros(N_samples)
node_q_err = np.zeros(N_samples)
d_out = np.zeros(N_samples)

# Processing Loop
for n in range(N_samples):
    v_in = v_in_seq[n]
    
    # 1. Read current FIR filter output from prior residues
    v_fir = fir_filter.step(0.0) # Clock shifts out the current filter state
    node_v_fir[n] = v_fir
    
    # 2. Charge sharing summation node
    v_target = adder.combine(v_in, v_fir)
    node_v_dac[n] = v_target
    
    # 3. 8-bit SAR Quantization
    v_digital, q_err = sar.convert(v_target)
    d_out[n] = v_digital
    node_q_err[n] = q_err
    
    # 4. Amplify the residue voltage using the reused comparator D-amp
    v_amp_residue = d_amp.amplify(q_err)
    
    # 5. Feed amplified residue back into the SC filter delay line
    fir_filter.z1 = v_amp_residue

# =====================================================================
# Plotting Waveforms and Spectral Performance
# =====================================================================
plt.figure(figsize=(12, 8))

# Time-domain Waveform Subplots
plt.subplot(2, 1, 1)
plt.plot(t[:100]*1e6, v_in_seq[:100], label='Input ($V_{in}$)', alpha=0.8)
plt.step(t[:100]*1e6, d_out[:100], label='SAR Digital Output ($D_{out}$)', where='post')
plt.plot(t[:100]*1e6, node_v_fir[:100], label='FIR Feedback ($V_{fir}$)', linestyle='--')
plt.title('Transient Waveforms (First 100 Samples)')
plt.xlabel('Time ($\mu$s)')
plt.ylabel('Voltage (V)')
plt.legend(loc='upper right')
plt.grid(True)

# Power Spectral Density (PSD)
plt.subplot(2, 1, 2)
window = np.blackman(N_samples)
d_out_fft = np.fft.fft(d_out * window)
psd = 20 * np.log10(np.abs(d_out_fft[:N_samples//2]) / (N_samples / 2))
freqs = np.fft.fftfreq(N_samples, 1/fs)[:N_samples//2]

plt.semilogx(freqs, psd, label='Output Spectrum (w/ NS)')
# Draw OSR Bandwidth limit line
plt.axvline(fs / (2 * OSR), color='red', linestyle=':', label=f'In-band Limit ({int(fs/(2*OSR)/1e3)} kHz)')
plt.title('Output PSD with 2nd-Order Complex Noise Shaping')
plt.xlabel('Frequency (Hz)')
plt.ylabel('Amplitude (dBFS)')
plt.ylim([-140, 0])
plt.legend(loc='lower left')
plt.grid(True, which="both", ls="-")

plt.tight_layout()
plt.show()