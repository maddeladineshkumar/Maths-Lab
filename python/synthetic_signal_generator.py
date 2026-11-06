"""
synthetic_signal_generator.py
CRT-Nano Project: Synthetic Optical Signal Generator for Capillary Refill Time (CRT90)
Authors: M. Dinesh Kumar (CB.AI.U4AID25126) & Malepati Venkata Sai Sujan (CB.AI.U4AID25129)
Course: 23MAT204 - Lab Exam: Frugal Healthcare AI / Edge Device Challenge
Instructor: Dr. Suman Dutta

Mathematical Model Implementation from Section 9 of Proposal:
  x(t) = R0 - kappa * v(t) + a * v(t) * p(t) + d(t) + n(t)
  v(t) = 1 - (1 - v_min) * exp(-(t - t0) / tau)  for t >= t0
  CRT90 = tau * ln((1 - v_min) / 0.1)
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional


def generate_cardiac_pulse(t: np.ndarray, hr_bpm: float = 72.0) -> np.ndarray:
    """
    Generates a realistic normalized pulsatile PPG waveform p(t) in range [0, 1]
    with a primary systolic peak, dicrotic notch, and diastolic decay.
    """
    f_hr = hr_bpm / 60.0
    phase = (2.0 * np.pi * f_hr * t) % (2.0 * np.pi)
    
    # Modelled as sum of harmonic components matching human finger PPG morphology
    p = (
        0.55 * np.sin(phase - 0.2) +
        0.30 * np.sin(2.0 * phase - 1.1) +
        0.12 * np.sin(3.0 * phase - 2.2) +
        0.05 * np.sin(4.0 * phase - 3.1)
    )
    # Normalize to [0, 1]
    p_norm = (p - np.min(p)) / (np.max(p) - np.min(p) + 1e-12)
    return p_norm


def generate_crt_trace(
    true_crt90: float = 2.0,
    v_min: float = 0.20,
    hr_bpm: float = 75.0,
    snr_db: float = 22.0,
    fs: float = 100.0,
    t_baseline: float = 3.0,
    t_press: float = 3.0,
    t_recovery_window: float = 8.0,
    r0: float = 512.0,          # Baseline ADC mid-range (10-bit ADC: 0-1023)
    kappa: float = 240.0,       # Optical reflectance swing
    pulsatile_amp: float = 45.0,# AC amplitude
    drift_type: str = "none",   # "none", "linear", "sinusoidal"
    drift_mag: float = 15.0,
    artifact_type: str = "none",# "none", "motion_recovery", "finger_lift", "weak_blanch"
    random_seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generates a full synthetic capillary refill trial conforming to the formal
    mathematical model in Section 9 of the CRT-Nano project proposal.
    
    Returns a dictionary with timestamps, raw signal, components, and ground truth parameters.
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    # Calculate time constant tau from operational definition CRT90 = tau * ln((1 - v_min) / 0.1)
    # If 1 - v_min <= 0.1, tissue did not blanch past 90%, so tau is undefined/small
    effective_ratio = max((1.0 - v_min) / 0.1, 1.0001)
    tau = true_crt90 / np.log(effective_ratio)

    t_total = t_baseline + t_press + t_recovery_window
    n_samples = int(np.round(t_total * fs))
    t = np.linspace(0.0, t_total, n_samples, endpoint=False)

    t_press_start = t_baseline
    t_release = t_baseline + t_press  # t0 in proposal

    # Compute continuous tissue blood volume v(t) in [0, 1]
    v = np.ones_like(t)

    for i, ti in enumerate(t):
        if ti < t_press_start:
            # Baseline: fully perfused
            v[i] = 1.0
        elif ti < t_release:
            # Pressing phase: blanching evacuation of capillary blood
            # Smooth transition to v_min using tanh press profile
            press_elapsed = ti - t_press_start
            decay_rate = 12.0 # rapid compression within ~0.2s
            transition = 0.5 * (1.0 + np.tanh(decay_rate * (press_elapsed - 0.15)))
            target_vmin = 0.85 if artifact_type == "weak_blanch" else v_min
            v[i] = 1.0 - transition * (1.0 - target_vmin)
        else:
            # Recovery phase: exponential capillary reperfusion
            # v(t) = 1 - (1 - v_min) * exp(-(t - t0) / tau)
            rec_elapsed = ti - t_release
            refill_vmin = 0.85 if artifact_type == "weak_blanch" else v_min
            v[i] = 1.0 - (1.0 - refill_vmin) * np.exp(-rec_elapsed / tau)

    # Generate cardiac pulsatile waveform p(t)
    p = generate_cardiac_pulse(t, hr_bpm=hr_bpm)

    # Baseline drift d(t)
    if drift_type == "linear":
        d = np.linspace(-drift_mag, drift_mag, n_samples)
    elif drift_type == "sinusoidal":
        f_resp = 0.25 # 15 breaths per minute
        d = drift_mag * np.sin(2.0 * np.pi * f_resp * t)
    else:
        d = np.zeros_like(t)

    # Pure noiseless signal: x_clean(t) = R0 - kappa * (1 - v(t)) + a * v(t) * p(t) + d(t)
    # Note: As blood leaves (v drops), tissue blanches, reflectance increases or transmission changes.
    # In reflectance PPG, blanching reduces red/IR hemoglobin absorption, increasing returned light.
    # We follow Eq (1): x(t) = R0 - kappa * v(t) + a * v(t) * p(t) + d(t) + n(t)
    # Or inverting so that v=1 is baseline:
    # Baseline DC = R0 - kappa; at v=vmin (blanched), x_dc = R0 - kappa * vmin > R0 - kappa
    # Pulsatile amplitude scales with local blood volume v(t)
    x_clean = (r0 - kappa * v) + (pulsatile_amp * v * (p - 0.5)) + d

    # Calculate signal power for noise calibration
    # Exclude DC baseline offset to define realistic biological SNR
    ac_and_recovery_var = np.var(x_clean - r0)
    if ac_and_recovery_var < 1e-4:
        ac_and_recovery_var = 1.0

    noise_var = ac_and_recovery_var / (10.0 ** (snr_db / 10.0))
    noise_std = np.sqrt(noise_var)
    noise = np.random.normal(0.0, noise_std, size=n_samples)

    # Add 50 Hz power-line interference (small ambient hum)
    hum = 0.15 * noise_std * np.sin(2.0 * np.pi * 50.0 * t)
    n = noise + hum

    x = x_clean + n

    # Inject specific realistic artifacts if requested
    if artifact_type == "motion_recovery":
        # Sudden motion spike 1.2s after release
        t_art = t_release + 1.2
        idx_art = np.where((t >= t_art) & (t <= t_art + 0.45))[0]
        if len(idx_art) > 0:
            x[idx_art] += 120.0 * np.sin(np.linspace(0, np.pi, len(idx_art)))
    elif artifact_type == "finger_lift":
        # Finger removed at 2.0s into recovery
        t_lift = t_release + 2.0
        idx_lift = np.where(t >= t_lift)[0]
        if len(idx_lift) > 0:
            # Ambient light saturation or floating ADC
            x[idx_lift] = 1010.0 + np.random.normal(0, 3.0, len(idx_lift))
            v[idx_lift] = 0.0

    # Clip to 10-bit ADC range [0, 1023]
    x = np.clip(x, 0.0, 1023.0)

    return {
        "t": t,
        "x": x,
        "x_clean": x_clean,
        "v_true": v,
        "p": p,
        "d": d,
        "noise": n,
        "fs": fs,
        "t_baseline": t_baseline,
        "t_press": t_press,
        "t_release": t_release,
        "true_crt90": true_crt90,
        "tau": tau,
        "v_min": v_min,
        "hr_bpm": hr_bpm,
        "snr_db": snr_db,
        "artifact_type": artifact_type
    }
