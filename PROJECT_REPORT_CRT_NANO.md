# CRT-Nano: A Low-Cost Reflectance-Based Capillary Refill Time Measurement System with Optional Servo-Assisted Pressing

**Course:** 23MAT204 – Lab Exam: Frugal Healthcare AI / Edge Device Challenge  
**Course Instructor:** Dr. Suman Dutta  
**Academic Institution:** School of AI, Amrita Vishwa Vidyapeetham  
**Authors:**
- **M. Dinesh Kumar** (Roll Number: `CB.AI.U4AID25126`, 25126)
- **Malepati Venkata Sai Sujan** (Roll Number: `CB.AI.U4AID25129`)
**Date:** October 30, 2026  

---

## Executive Summary & Engineering Feasibility Statement

Conventional Capillary Refill Time (CRT) is a cornerstone bedside clinical indicator utilized across emergency triage, pediatric sepsis guidelines, and shock resuscitation protocols. However, the manual technique—applying fingertip pressure and visually estimating the return of pink skin tint—is plagued by inter-observer variation, ambient lighting bias, lack of digital timestamping, and subjective endpoints.

**CRT-Nano** explores whether an ultra-low-cost, kit-constrained architecture combining a generic reflectance Photoplethysmography (PPG) module with an 8-bit Arduino Nano (ATmega328P) can extract a standardized optical refill metric ($CRT_{90}$) without requiring costly commercial instrumentation or complex computer vision pipelines.

### Key Feasibility Findings:
1. **Mathematical & Algorithmic Feasibility:** By adopting a patient-referenced normalisation function $y(t) = \frac{x(t) - x_{blanch}}{x_{baseline} - x_{blanch}}$, the system removes sensitivity to absolute skin pigmentation and ambient light drift. A dual-estimator strategy (90% threshold crossing with 150ms stability dwell alongside Levenberg-Marquardt exponential fitting) achieved a Mean Absolute Error of **$0.181\text{ s}$** and estimation bias of **$+0.153\text{ s}$** across a clinical range of $0.5 - 6.0\text{ s}$, outperforming the design target ($\le 0.40\text{ s}$).
2. **Quality Gate Specificity:** Six algorithmic gates (F1 to F6) demonstrated **$100.0\%$ rejection specificity** against corrupted traces (tremor, weak blanching, recovery motion jerk, and finger detachment), preventing spurious clinical readings.
3. **Hardware & Resource Feasibility:** The full 100 Hz acquisition loop, digital filtering, 7-state finite state machine, and audio synthesis utilizes only **$1.60\%$ CPU load**, **$24.2\%$ Flash**, and **$24.0\%$ SRAM** on an ATmega328P.
4. **Economic Feasibility:** The core manual configuration is realized for **Rs. 287** (31.3% of kit value) and the servo-assisted version for **Rs. 357** (38.9% of kit value), both well within the Rs. 360 budget constraint.

---

## 1. Problem Statement & Motivation

Capillary refill time is clinically defined as the time taken for blood to return to distal capillaries following blanching induced by pressure. Prolonged CRT (> 2.0 or 3.0 seconds) correlates strongly with hypoperfusion, systemic vasoconstriction, dehydration, and septic shock.

### Limitations of the Conventional Bedside Method:
- **Observer Subjectivity:** Evaluators judge the endpoint by naked eye, leading to significant discordance between clinicians.
- **Ambient Lighting Vulnerability:** Dim hospital triage bays or fluorescent emergency ward lighting dramatically alters perceived skin tint.
- **Uncontrolled Mechanics:** The magnitude of applied pressure and compression duration varies substantially across practitioners.
- **Absence of Digital Record:** Manual stopwatches do not log continuous signal waveforms for retrospective quality auditing or trend tracking.

### Formal Engineering Problem Statement
Design an edge-compatible, kit-constrained embedded instrument that samples optical reflectance from a fingertip, identifies a release event $t_0$, computes a baseline-normalised optical recovery time ($CRT_{90}$), and outputs diagnostic status alongside signal quality warnings.

---

## 2. Mathematical Signal Model & Operational Definition

### 2.1 Forward Optical Model
Tissue optical reflectance measured by the photodetector is modeled as:
$$x(t) = R_0 - \kappa v(t) + a v(t) p(t) + d(t) + n(t)$$
where:
- $R_0$: Static baseline optical offset (ADC counts).
- $v(t) \in [0, 1]$: Normalized microvascular tissue blood volume.
- $\kappa$: Optical gain / absorption swing factor.
- $a$: Pulsatile arterial AC amplitude.
- $p(t)$: Periodic multi-harmonic cardiac waveform ($f_{HR} \in [0.8, 2.2\text{ Hz}]$).
- $d(t)$: Slow baseline drift (respiration at $\sim 0.25\text{ Hz}$, temperature drift).
- $n(t)$: Zero-mean Gaussian noise + 50 Hz power-line hum.

### 2.2 Reperfusion Trajectory
Following release at timestamp $t_0$, capillary refilling follows exponential reperfusion kinetics:
$$v(t) = 1 - (1 - v_{min}) e^{-(t - t_0)/\tau}, \quad t \ge t_0$$
where $v_{min}$ is the residual blood volume reached at maximum compression and $\tau$ is the characteristic capillary refilling time constant.

### 2.3 Operational Definition of $CRT_{90}$
Setting $v(t) = 0.90$ yields the operational recovery endpoint:
$$0.90 = 1 - (1 - v_{min}) e^{-CRT_{90}/\tau} \implies CRT_{90} = \tau \ln\left(\frac{1 - v_{min}}{0.1}\right)$$
For example, with nominal blanch depth $v_{min} = 0.20$:
$$CRT_{90} = \tau \ln(8) \approx 2.0794 \tau$$

---

## 3. Dual Estimator Architecture & Quality Gates

### Estimator 1: Baseline-Normalised Threshold Crossing
The recovery trajectory is normalized into feature space:
$$y(t) = \frac{x_{filt}(t) - x_{blanch}}{x_{base} - x_{blanch}}$$
The algorithm registers $t_{cross}$ as the earliest timestamp where $y(t) \ge 0.90$ continuously for a 150 ms dwell period ($15$ consecutive samples at 100 Hz). This dwell filter eliminates false triggering from high-frequency noise spikes.

### Estimator 2: Non-Linear Least Squares Exponential Model Fit
Fits the analytical model $y(t) = 1.0 - (1.0 - y_0) e^{-(t - t_0)/\tau}$ across the recovery segment using the Levenberg-Marquardt algorithm. It extracts $\tau$ and computes the goodness-of-fit metric $R^2$.

### Consensus Logic:
When $R^2 \ge 0.80$ and estimators agree within $1.25\text{ s}$:
$$CRT_{90}^{final} = 0.6 \cdot CRT_{90}^{model} + 0.4 \cdot CRT_{90}^{thresh}$$
Otherwise, the robust threshold estimator is used directly.

### Quality Gate Check Matrix (Table 5 of Proposal)
| Code | Condition Monitored | Trigger Threshold | Remediation / System Action |
| :--- | :--- | :--- | :--- |
| **F1** | Signal Saturation / Disconnect | $x < 25$ or $x > 995$ counts | Abort trial; prompt sensor repositioning |
| **F2** | Pre-press Baseline Instability | $\sigma_{base} > 30$ counts or drift $> 48$ counts | Reject; prompt user to hold hand still |
| **F3** | Insufficient Blanching Force | $\Delta ADC < 35$ counts | Inadequate pressure; do not compute CRT |
| **F4** | Recovery Motion Artifact | Slope $> 580$ or Acceleration $> 5200$ | Reject; prompt still recovery |
| **F5** | Estimator Disagreement / Low $R^2$ | $|CRT_{thresh} - CRT_{model}| > 1.25\text{ s}$ or $R^2 < 0.65$ | Flag low confidence warning |
| **F6** | Premature Finger Lift | Tail signal $> 1000$ counts mid-cycle | Immediate cycle abort; mark invalid |

---

## 4. Hardware Utilization, Circuit Design, & BOM Cost

### 4.1 Bill of Materials (Strictly Kit-Constrained)
| Component | Function / Subsystem | Lab Kit Price (INR) | Configuration |
| :--- | :--- | :--- | :--- |
| Arduino Nano V3 (CH340) | 16 MHz ATmega328P, ADC, FSM, UART | Rs. 155.00 | Core & Servo |
| PPG Pulse Sensor Module | Green LED + Photodetector (Pin A0) | Rs. 75.00 | Core & Servo |
| Piezo Transducer Disc | Acoustic status cues (Pin D8) | Rs. 12.00 | Core & Servo |
| Premium Jumper Wires | Interconnect wiring | Rs. 35.00 | Core & Servo |
| Carbon Film Resistors Pack | 330Ω piezo limiter, 10kΩ divider | Rs. 10.00 | Core & Servo |
| **Subtotal (Core Manual-Press)** | **Complete Standard Instrument** | **Rs. 287.00** | **31.3% of Kit** |
| TowerPro SG90 Micro Servo | Motorized press arm actuator (Pin D9) | Rs. 70.00 | Servo Option |
| **Total (Servo-Assisted Concept)**| **Motorized Research Instrument** | **Rs. 357.00** | **38.9% of Kit** |

*Budget Compliance:* Target T6 ($\le \text{Rs. } 360$) is satisfied in both configurations.

### 4.2 Circuit Architecture
- Single-point star ground to prevent actuator return currents from disturbing the high-impedance optical ADC line.
- Decoupling bus: 10µF electrolytic buffer in parallel with 0.1µF ceramic high-frequency bypass across 5V and GND.
- Series 330Ω resistor on Pin D8 to clamp piezo discharge current well within the ATmega328P 40mA absolute maximum pin rating.

---

## 5. Experimental Validation Results (E1 to E7)

| Experiment | Metric Evaluated | Target Specification | Experimental Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **E1** | Mean Absolute Error (MAE) | $\le 0.40\text{ s}$ | **$0.181\text{ s}$** | **PASSED** |
| **E1** | Estimation Bias | $\le \pm 0.20\text{ s}$ | **$+0.153\text{ s}$** | **PASSED** |
| **E2** | Noise Robustness @ 10 dB | Low degradation | **MAE = $0.119\text{ s}$** (100% valid) | **PASSED** |
| **E2** | Noise Robustness @ 25 dB | High precision | **MAE = $0.050\text{ s}$** | **PASSED** |
| **E4** | Heart Rate Invariance | 60, 90, 120 bpm | **MAE = $0.112 - 0.174\text{ s}$** | **PASSED** |
| **E6** | Fault Rejection Specificity | Rejection of bad traces | **$100.0\%$ Rejection** | **PASSED** |
| **E7** | MCU Active CPU Load | $\le 20\%$ | **$1.60\%$** (160µs per 10ms) | **PASSED** |
| **E7** | MCU SRAM Utilization | $\le 2048\text{ B}$ | **$492\text{ B}$ ($24.0\%$)** | **PASSED** |
| **E7** | MCU Flash Program Memory | $\le 30720\text{ B}$ | **$7450\text{ B}$ ($24.2\%$)** | **PASSED** |
| **E7** | Complete Test Cycle Duration | $\le 40\text{ s}$ | **$12.0\text{ s}$** | **PASSED** |

---

## 6. Safety, Clinical Positioning, & Ethical Considerations

1. **Research & Educational Prototype:** CRT-Nano is an engineering proof-of-concept. It is not an FDA/CE-cleared medical device and must never be used for autonomous triage or emergency diagnostic decision-making.
2. **Mechanical Safety (Servo Limitations):** A hobby servo provides angular position control, not direct tissue force feedback. A fixed angle does not guarantee uniform blanching pressure across varying finger diameters. Therefore, the manual-press method remains the primary safe baseline.
3. **Electrical Safety:** Powered exclusively from a 5V galvanically isolated USB source. No high-voltage circuits or direct electrical patient contacts exist.
4. **Hygiene:** Clinical deployment would require disposable optical film barriers or medical-grade silicone covers between patients.

---

## 7. Conclusion

CRT-Nano successfully demonstrates that an accessible Rs. 287 edge device can extract quantitative optical capillary refill times with sub-0.2 second accuracy. By integrating patient-referenced baseline normalisation, dual-estimator cross-validation, and rigorous quality gating, the platform bridges the gap between subjective visual observation and high-cost clinical monitoring instrumentation.
