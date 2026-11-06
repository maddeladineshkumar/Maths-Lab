# CRT-Nano: Low-Cost Optical Capillary Refill Time Measurement System

[![Test Suite](https://img.shields.io/badge/Unit%20Tests-18%2F18%20Passing-brightgreen.svg)](python/test_suite.py)
[![Hardware](https://img.shields.io/badge/Target-Arduino%20Nano%20(ATmega328P)-blue.svg)](firmware/CRT_Nano_Firmware.ino)
[![Sampling](https://img.shields.io/badge/Sampling-100%20Hz%20Real--Time-orange.svg)](firmware/CRT_Nano_Firmware.ino)
[![Estimation Accuracy](https://img.shields.io/badge/Accuracy%20(MAE)-0.181%20s-success.svg)](results/experiment_metrics.json)
[![BOM Cost](https://img.shields.io/badge/Kit%20Cost-Rs.%20287%20%2F%20Rs.%20357-teal.svg)](circuit/CRT_Nano_Virtual_Circuit_Diagram.pdf)

> **Course:** 23MAT204 – Lab Exam: Frugal Healthcare AI / Edge Device Challenge  
> **Course Instructor:** Dr. Suman Dutta  
> **Institution:** School of AI, Amrita Vishwa Vidyapeetham  
> **Authors:**  
> - **M. Dinesh Kumar** (Roll Number: `CB.AI.U4AID25126`)  
> - **Malepati Venkata Sai Sujan** (Roll Number: `CB.AI.U4AID25129`)  

---

## 1. Project Overview & Clinical Problem Statement

Capillary Refill Time (CRT) is a cornerstone hemodynamic triage assessment used in emergency departments, intensive care units, and disaster settings to evaluate peripheral perfusion and shock. In conventional clinical practice, an observer presses a patient's fingernail bed for 3–5 seconds to blanch capillary blood, releases compression, and visually counts seconds until baseline pink color returns.

### The Problem
* **Inter-Observer Discordance:** Manual visual timing exhibits high disagreement (Fleiss' $\kappa \approx 0.40$).
* **Ambient Light Sensitivity:** Poor or flickering room illumination severely alters human perception of capillary blanching.
* **Unrecorded Timestamps:** Manual tests lack verifiable digital telemetry and objective physiological endpoints.
* **Cost Barriers:** Commercial transcutaneous monitors cost thousands of dollars, making them unavailable for frontline low-resource clinics.

### The CRT-Nano Solution
CRT-Nano is an ultra-low-cost, kit-constrained edge biomedical instrument built on an 8-bit **Arduino Nano (ATmega328P)** using a generic green reflectance Photoplethysmography (PPG) pulse sensor (565nm LED + photodetector). The system captures optical tissue reflectance at 100 Hz, filters noise, normalizes recovery relative to the patient's own pre-press baseline, and deterministically computes **$CRT_{90}$**—the operational time required for microvascular blood volume to return to 90% of resting baseline.

---

## 2. Mathematical Formulation

### 2.1 Continuous Tissue Reflectance Model
Optical tissue reflectance $x(t)$ captured by the sensor is modeled as:
$$x(t) = R_0 - \kappa v(t) + a v(t) p(t) + d(t) + n(t)$$

Where:
* $R_0$: Static tissue reflectance offset (baseline ADC count).
* $v(t) \in [0, 1]$: Microvascular blood volume fraction ($v \approx 1$ at rest, $v \ll 1$ when blanched).
* $\kappa$: Optical absorption coupling coefficient for oxygenated/deoxygenated hemoglobin.
* $a v(t) p(t)$: Pulsatile AC arterial waveform modulated by instantaneous blood volume.
* $d(t)$: Low-frequency drift (respiration, skin temperature changes).
* $n(t)$: Zero-mean Gaussian optical and electronic sensor noise.

### 2.2 Reperfusion Dynamics & $CRT_{90}$ Operational Endpoint
Upon compression release at timestamp $t_0$, reactive hyperemic reperfusion follows non-linear exponential dynamics:
$$v(t) = 1 - (1 - v_{min}) e^{-(t - t_0)/\tau}, \quad t \ge t_0$$

The standard diagnostic threshold is defined as the moment blood volume recovers to 90% of baseline ($v(t) = 0.90$):
$$0.90 = 1 - (1 - v_{min}) e^{-CRT_{90}/\tau} \implies CRT_{90} = \tau \ln\left(\frac{1 - v_{min}}{0.10}\right)$$

---

## 3. Hardware Architecture & Virtual Circuit

The system interfaces with an **Arduino Nano V3** through standard 0.1" pin headers:

| Nano Pin | Peripheral / Subsystem | Signal Type | Engineering Function |
| :--- | :--- | :--- | :--- |
| **A0** | Optical Pulse Sensor (PPG) SIG | Analog (0–5V) | Captures 565nm green reflectance modulated by capillary hemoglobin absorption. |
| **D8** | Piezo Disc Transducer (+) | PWM / Square | Acoustic user feedback (ready tone, press cue, release beep, victory fanfare). |
| **D9** | SG90 Micro Servo (Orange) | PWM (50 Hz) | Optional motorized pressing actuator for reproducible blanching force. |
| **D2** | Tactile Switch / Jumper to GND | Digital Input | Manual trigger / configuration mode toggle (internal pull-up enabled). |
| **A1** | NTC 10k$\Omega$ Thermistor Divider | Analog (0–5V) | Optional skin and ambient temperature context acquisition. |
| **5V / GND**| Regulated Power Bus | Power | Decoupled with 10$\mu$F electrolytic + 0.1$\mu$F ceramic filter capacitors. |

The single-page vector schematic is available in [`circuit/CRT_Nano_Virtual_Circuit_Diagram.pdf`](circuit/CRT_Nano_Virtual_Circuit_Diagram.pdf).

---

## 4. Signal Processing Pipeline & Dual Estimators

```
[Raw ADC @ 100 Hz] ───► [EMA Low-Pass Filter (2.5 Hz)] ───► [7-State Finite State Machine]
                                                                        │
        ┌───────────────────────────────────────────────────────────────┴─────────────────────────┐
        ▼                                                                                         ▼
[Estimator 1: 90% Threshold Dwell]                                              [Estimator 2: NLS Exp Fit]
Tracks y_norm(t) >= 0.90 with 150ms dwell window.                               Fits v(t) = 1 - (1 - v_min)*exp(-t/tau).
        │                                                                                         │
        └───────────────────────────────► [Consensus Engine] ◄────────────────────────────────────┘
                                                  │
                                                  ▼
                                      [6-Stage Quality Gates]
                                                  │
                                                  ▼
                                  [Valid $CRT_{90}$ & Clinical Alert]
```

### 6-Stage Fault-Aware Quality Gates (F1 to F6)
1. **F1 (Signal Bounds):** Rejects open-circuit ($<25$ ADC) or optical saturation ($>995$ ADC).
2. **F2 (Baseline Stability):** Verifies standard deviation $\sigma < 30$ ADC counts during the pre-press window.
3. **F3 (Blanching Excursion):** Demands minimum dynamic excursion $\Delta ADC \ge 35$ counts upon pressing.
4. **F4 (Motion Artifacts):** Detects abrupt sample-to-sample recovery jerk $|\Delta x| > 80$ counts.
5. **F5 (Estimator Divergence):** Flags discrepancy between threshold crossing and exponential model fit.
6. **F6 (Finger Detachment):** Detects premature sensor release before reperfusion completes.

---

## 5. Experimental Validation Benchmarks (E1 to E7)

Across 108 Monte-Carlo simulation trials varying true $CRT_{90}$ from 0.5 s to 6.0 s, SNR from 10 dB to 30 dB, and heart rates from 60 to 120 bpm:

| Benchmark / Metric | Target Spec | Achieved Result | Status |
| :--- | :--- | :--- | :--- |
| **Target T1 (E1): Estimation MAE** | $\le 0.40\text{ s}$ | **$0.181\text{ s}$** | **PASSED (Exceeded Target)** |
| **Target T2 (E1): Absolute Bias** | $\le 0.20\text{ s}$ | **$+0.153\text{ s}$** | **PASSED** |
| **Experiment E2: Noise MAE @ 10 dB** | $\le 0.40\text{ s}$ | **$0.119\text{ s}$** (100% valid) | **PASSED** |
| **Experiment E4: Heart Rate Invariance** | Stable (60–120 bpm) | **$0.112 - 0.174\text{ s}$** | **PASSED** |
| **Experiment E6: Fault Rejection Specificity** | $> 95\%$ | **$100.0\%$ rejection** (0 false negatives) | **PASSED** |
| **Target T5 (E7): Test Cycle Duration** | $\le 40\text{ s}$ | **$12.0\text{ s}$** | **PASSED** |
| **Target T6: Bill of Materials Cost** | $\le \text{Rs. } 360$ | **Rs. 287 (Manual) / Rs. 357 (Servo)** | **PASSED** |
| **Target T7 (E7): Flash Memory Footprint** | $\le 30,720\text{ B}$ | **$7,450\text{ B}$ ($24.2\%$)** | **PASSED** |
| **Target T7 (E7): SRAM Memory Footprint** | $\le 2,048\text{ B}$ | **$492\text{ B}$ ($24.0\%$)** | **PASSED** |
| **Target T7 (E7): CPU Utilization** | $\le 20\%$ | **$1.60\%$** ($98.4\%$ idle headroom) | **PASSED** |

---

## 6. Bill of Materials & Kit Budget Compliance

| Kit Item | Component Description | Subsystem Role | Cost (INR) |
| :--- | :--- | :--- | :--- |
| Kit #2 | **Arduino Nano V3 (ATmega328P / CH340)** | 100 Hz sampling, digital filtering, 7-state FSM, telemetry | Rs. 155.00 |
| Kit #3 | **Optical Pulse Sensor (PPG Clone Module)** | 565nm green reflectance capillary reperfusion sensor | Rs. 75.00 |
| Kit #7 | **Piezo Transducer Disc / Buzzer** | Acoustic state feedback and fault audio cues | Rs. 12.00 |
| Kit #11 | **Premium Jumper Wires (Bundle)** | Point-to-point breadboard and direct pin interconnects | Rs. 35.00 |
| Kit #13 | **Resistor Pack (330$\Omega$, 10k$\Omega$)** | Piezo current limiting and thermistor voltage divider | Rs. 10.00 |
| **Subtotal** | **Core Manual-Press Configuration** | **31.3% of Course Lab Kit Ceiling** | **Rs. 287.00** |
| Kit #6 | **SG90 Micro Servo (Optional Actuator)** | Motorized pressing arm mechanism | Rs. 70.00 |
| **Total** | **Servo-Assisted Research Configuration** | **Strictly below Rs. 360 Budget Ceiling** | **Rs. 357.00** |

---

## 7. Interactive Web Simulation Dashboard

The repository includes a self-contained, offline-compatible simulation portal located in [`web/index.html`](web/index.html) (or [`index.html`](index.html)):
* **Live Waveform Canvas:** Plots raw and EMA-filtered PPG reflectance in real time with state-colored background zones.
* **Audio Synthesizer:** Live Web Audio API synthesizes acoustic cues matching the Arduino firmware.
* **Interactive Codebase Explorer:** Tabbed in-browser inspection of all firmware and Python algorithms.
* **CSV Signal Exporter:** Exports real-time 100 Hz simulation data directly to CSV.

---

## 8. Codebase Structure & How to Run

```
.
├── firmware/
│   ├── CRT_Nano_Firmware.ino         # Production 7-state FSM Arduino firmware (100 Hz ISR timer)
│   ├── SignalFilter.h                # Real-time EMA filter & running baseline statistics tracker
│   ├── SignalFilter.cpp              # C++ implementation linkage
│   └── StateTypes.h                  # State enums, pinout definitions, fault codes (F1-F6)
├── python/
│   ├── synthetic_signal_generator.py # Physiological PPG + blanching + recovery simulator
│   ├── signal_processor.py           # Dual estimators (Threshold Dwell + NLS Exp Fit) + Quality Gates
│   ├── experiments.py                # Monte-Carlo validation suite (Experiments E1 to E7)
│   ├── generate_plots.py             # Generates publication-grade figures (PNG + Vector PDF)
│   └── test_suite.py                 # Automated unit test suite (18 unit tests, 100% passing)
├── data/
│   └── sample_traces.csv             # 100 Hz synthetic clinical traces with ground truth
├── results/
│   ├── experiment_metrics.json       # Quantitative performance metrics across 108 trials
│   └── figures/                      # High-resolution publication plots (fig1 to fig4)
├── circuit/
│   ├── CRT_Nano_Virtual_Circuit_Diagram.pdf # Single-page vector schematic PDF
│   ├── circuit_diagram.png           # High-resolution circuit diagram image
│   └── generate_circuit.py           # Matplotlib circuit generator script
├── web/                              # Clean interactive simulation web app
│   ├── index.html                    # Dashboard UI
│   ├── style.css                     # Editorial stylesheet
│   ├── app.js                        # Simulation engine, canvas rendering, audio synthesizer
│   └── codebase_data.js              # Embedded offline codebase data
├── index.html                        # Root landing page for GitHub Pages
├── CRT_Nano_Signal_Processing_Codebase.zip # Production sanitized ZIP archive
├── CRT_Nano_Signal_Processing_Codebase.pdf # Comprehensive 19-page engineering specification PDF
└── PROJECT_REPORT_CRT_NANO.md        # Full 17-section technical report
```

### Running the Python Suite
```bash
# 1. Run the 18 automated unit tests
python3 python/test_suite.py

# 2. Run the Monte-Carlo simulation validation (Experiments E1 to E7)
python3 python/experiments.py

# 3. Generate publication figures
python3 python/generate_plots.py
```

### Deploying the Arduino Firmware
1. Open [`firmware/CRT_Nano_Firmware.ino`](firmware/CRT_Nano_Firmware.ino) in the Arduino IDE.
2. Select Board: **Arduino Nano**, Processor: **ATmega328P**.
3. Connect Nano via USB and click **Upload**.
4. Open Serial Monitor at **115200 baud**.

---

## 9. License & Safety Disclaimer

* **License:** Educational Open-Source.
* **Safety Notice:** CRT-Nano is an educational research prototype developed for the 23MAT204 challenge. It is not an FDA-cleared diagnostic device and is not intended for primary clinical diagnosis without clinical validation.
