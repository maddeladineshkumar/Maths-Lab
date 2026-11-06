"""
signal_processor.py
CRT-Nano Project: Signal Processing Engine & Dual Recovery Estimator
Authors: M. Dinesh Kumar (CB.AI.U4AID25126) & Malepati Venkata Sai Sujan (CB.AI.U4AID25129)
Course: 23MAT204 - Lab Exam: Frugal Healthcare AI / Edge Device Challenge
Instructor: Dr. Suman Dutta

Features:
- Dual Estimators:
  1. Threshold Crossing (90% baseline-normalised return with stability dwell check)
  2. Non-linear Least-Squares Exponential Model Fit: y(t) = 1 - (1 - v_min)*exp(-(t-t0)/tau)
- Formal Quality Gate & Fault Handler (F1 to F6 from Proposal Table 5)
- Microcontroller-compatible integer/fixed-point equivalent math
"""

import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import butter, filtfilt
from typing import Dict, Any, List, Optional, Tuple


def butter_lowpass_filter(data: np.ndarray, cutoff: float, fs: float, order: int = 2) -> np.ndarray:
    """Applies a zero-phase 2nd order Butterworth low-pass filter to smooth PPG signals."""
    nyq = 0.5 * fs
    normal_cutoff = min(cutoff / nyq, 0.99)
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)


def exponential_recovery_model(t_rel: np.ndarray, tau: float, v_min: float) -> np.ndarray:
    """Analytical exponential recovery curve: v(t) = 1 - (1 - v_min) * exp(-t_rel / tau)"""
    return 1.0 - (1.0 - v_min) * np.exp(-t_rel / np.maximum(tau, 1e-4))


class CRTSignalProcessor:
    def __init__(self, fs: float = 100.0):
        self.fs = fs
        self.dt = 1.0 / fs

    def process_trial(
        self,
        t: np.ndarray,
        x: np.ndarray,
        t_press_start: float = 3.0,
        t_release: float = 6.0,
        recovery_duration: float = 7.0
    ) -> Dict[str, Any]:
        """
        Runs the full CRT-Nano processing pipeline on a measured optical trial.
        Evaluates pre-press baseline, press depth, release inflection, recovery trajectory,
        both estimators, and all 6 proposal quality gates.
        """
        faults: List[str] = []
        is_valid = True
        warnings: List[str] = []

        # 0. Defensive input validation (Empty or mismatched arrays)
        if len(x) == 0 or len(t) == 0 or len(x) != len(t):
            return {
                "is_valid": False,
                "status": "INVALID",
                "crt90_estimate": None,
                "crt90_threshold": None,
                "crt90_model": None,
                "best_estimator": "None (Empty / Mismatched Input)",
                "classification": "REJECTED (INVALID_INPUT_DATA)",
                "faults": ["F1_SIGNAL_OUT_OF_RANGE"],
                "warnings": ["EMPTY_OR_MISMATCHED_INPUT_ARRAYS"],
                "base_dc": 0.0,
                "base_std": 0.0,
                "blanch_depth": 0.0,
                "r2_fit": 0.0,
                "tau_fit": 0.0,
                "v_min_fit": 0.0,
                "t_rec": np.array([]),
                "y_norm": np.array([]),
                "x_filtered": np.array([])
            }

        # Check for non-finite values (NaN / Inf)
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(t)):
            faults.append("F1_SIGNAL_OUT_OF_RANGE")
            warnings.append("NON_FINITE_DATA_DETECTED")
            x = np.nan_to_num(x, nan=-1.0, posinf=1025.0, neginf=-1.0)
            t = np.nan_to_num(t, nan=0.0, posinf=0.0, neginf=0.0)

        # 1. Basic boundary check (F1: Out of range / disconnected)
        if np.any(x < 15.0) or np.any(x > 1015.0):
            faults.append("F1_SIGNAL_OUT_OF_RANGE")

        # 2. Baseline Extraction & Stability (F2)
        # Compute slow DC baseline via 1.0-second moving average
        win_size = int(self.fs)
        kernel = np.ones(win_size) / win_size
        x_dc_smooth = np.convolve(x, kernel, mode='same')

        idx_base = np.where((t >= 0.6) & (t < t_press_start - 0.2))[0]
        if len(idx_base) < int(self.fs * 1.0):
            faults.append("F1_INSUFFICIENT_BASELINE_DATA")
            base_dc = float(np.mean(x[:int(self.fs)]))
            base_std = 999.0
        else:
            base_dc = float(np.mean(x_dc_smooth[idx_base]))
            base_dc_std = float(np.std(x_dc_smooth[idx_base]))
            base_dc_ptp = float(np.ptp(x_dc_smooth[idx_base]))
            base_std = float(np.std(x[idx_base]))
            if base_dc_std > 12.0 or base_dc_ptp > 48.0:
                faults.append("F2_BASELINE_UNSTABLE")

        # Filter signal with 2.5 Hz low-pass for slow capillary envelope tracking
        try:
            x_filtered = butter_lowpass_filter(x, cutoff=2.5, fs=self.fs, order=2)
        except Exception:
            x_filtered = x.copy()

        # 3. Press Phase & Blanching Depth (F3)
        idx_press = np.where((t >= t_press_start + 0.5) & (t <= t_release))[0]
        if len(idx_press) > 0:
            press_min_raw = float(np.min(x[idx_press]))
            press_min_filt = float(np.min(x_filtered[idx_press]))
            blanch_depth = abs(base_dc - press_min_filt)
            if blanch_depth < 30.0:  # Inadequate blanching force
                faults.append("F3_NO_DETECTABLE_BLANCH")
        else:
            press_min_filt = base_dc
            blanch_depth = 0.0
            faults.append("F3_NO_PRESS_PHASE")

        # 4. Finger Lift Check (F6)
        # Sudden divergence or near-saturation in the second half
        idx_rec_all = np.where(t >= t_release)[0]
        if len(idx_rec_all) > 0:
            rec_tail = x[idx_rec_all]
            if np.mean(rec_tail[-int(self.fs):]) > 1000.0:
                faults.append("F6_FINGER_REMOVED_MID_CYCLE")

        # 5. Extract Recovery Interval
        t_rec_end = min(t_release + recovery_duration, t[-1])
        idx_rec = np.where((t >= t_release) & (t <= t_rec_end))[0]
        if len(idx_rec) < int(self.fs * 0.5):
            faults.append("F1_INSUFFICIENT_RECOVERY_DATA")
            warnings.append("TRUNCATED_OR_MISSING_RECOVERY_PHASE")
        t_rec = t[idx_rec] - t_release
        x_rec = x_filtered[idx_rec]

        # 6. Motion Artefact Check during recovery (F4)
        if len(x_rec) > 5:
            rec_diff = np.diff(x_rec) * self.fs
            rec_diff2 = np.diff(rec_diff) * self.fs
            max_slope = np.max(np.abs(rec_diff))
            max_accel = np.max(np.abs(rec_diff2))
            if max_slope > 580.0 or max_accel > 5200.0:
                faults.append("F4_MOTION_ARTEFACT_IN_RECOVERY")

        # Normalize recovery curve y_norm(t) in [0, 1]
        # In our model: R0 - kappa*v. At baseline v=1, x = R0 - kappa (trough).
        # At blanch v=vmin, x = R0 - kappa*vmin (peak reflectance).
        # Therefore, as tissue refills with blood, x drops back from blanch peak to baseline.
        # Alternatively, if sensor polarity is inverted (absorption vs reflectance),
        # we compute normalized recovery towards baseline:
        x_blanch = press_min_filt
        span = base_dc - x_blanch
        if abs(span) < 1e-4:
            span = 1.0

        # Feature normalization towards baseline
        y_norm = (x_rec - x_blanch) / span
        # Clamp bounds
        y_norm = np.clip(y_norm, -0.1, 1.2)

        # 7. Estimator 1: Baseline-Normalised Threshold Crossing (90%)
        # Target: y_norm >= 0.90 with a 150ms continuous hold requirement
        target_thresh = 0.90
        hold_samples = int(0.15 * self.fs)
        crt90_threshold: Optional[float] = None

        for i in range(len(y_norm) - hold_samples):
            if np.all(y_norm[i : i + hold_samples] >= target_thresh):
                crt90_threshold = float(t_rec[i])
                break

        if crt90_threshold is None:
            # If it never sustained 90%, check if it touched 90% anywhere
            idx_touch = np.where(y_norm >= target_thresh)[0]
            if len(idx_touch) > 0:
                crt90_threshold = float(t_rec[idx_touch[0]])
            else:
                crt90_threshold = float(recovery_duration)  # Capped at timeout
                warnings.append("THRESHOLD_NOT_REACHED_WITHIN_WINDOW")

        # 8. Estimator 2: Non-linear Exponential Curve Fitting
        # Model: y(t) = 1.0 - (1.0 - v_min_est) * exp(-t / tau)
        # CRT90_est = tau * ln((1.0 - v_min_est) / 0.1)
        crt90_model: Optional[float] = None
        r2_fit: float = 0.0
        tau_fit: float = 0.0
        v_min_fit: float = 0.0

        if len(t_rec) > 10 and "F4_MOTION_ARTEFACT_IN_RECOVERY" not in faults and "F6_FINGER_REMOVED_MID_CYCLE" not in faults:
            try:
                # Parameterization: y(t) = 1.0 - (1.0 - y0) * exp(-t / tau)
                def exp_rec_fit(t_val, tau_val, y0_val):
                    return 1.0 - (1.0 - y0_val) * np.exp(-t_val / np.maximum(tau_val, 1e-4))

                popt, _ = curve_fit(
                    exp_rec_fit,
                    t_rec,
                    y_norm,
                    p0=[1.0, 0.0],
                    bounds=([0.05, -0.4], [8.0, 0.5]),
                    maxfev=1000
                )
                tau_fit, y0_fit = popt
                y_pred = exp_rec_fit(t_rec, tau_fit, y0_fit)
                
                # Goodness of fit R^2
                ss_res = np.sum((y_norm - y_pred) ** 2)
                ss_tot = np.sum((y_norm - np.mean(y_norm)) ** 2) + 1e-12
                r2_fit = float(1.0 - (ss_res / ss_tot))

                ratio = max((1.0 - y0_fit) / 0.10, 1.01)
                crt90_model = float(tau_fit * np.log(ratio))
                v_min_fit = y0_fit

                if r2_fit < 0.65:
                    warnings.append(f"LOW_MODEL_FIT_R2_{r2_fit:.2f}")

            except Exception as e:
                warnings.append(f"MODEL_FIT_CONVERGENCE_FAILURE: {str(e)}")
                crt90_model = None

        # 9. Estimator Disagreement Check (F5)
        if crt90_threshold is not None and crt90_model is not None:
            disagreement = abs(crt90_threshold - crt90_model)
            if disagreement > 1.25:
                faults.append(f"F5_ESTIMATOR_DISAGREEMENT_{disagreement:.2f}s")

        # Determine overall validity
        if len(faults) > 0:
            is_valid = False

        # Consensus estimate (strictly guarded by quality gate)
        if not is_valid:
            consensus_crt90 = None
            best_estimator = "Rejected by Quality Gate"
            classification = f"REJECTED ({'; '.join(faults)})"
        elif crt90_model is not None and r2_fit >= 0.80 and not any(f.startswith("F5") for f in faults):
            consensus_crt90 = 0.6 * crt90_model + 0.4 * crt90_threshold
            best_estimator = "Exponential Model Fitting (Weighted)"
            classification = "Normal (< 2.0 s)" if consensus_crt90 < 2.0 else ("Borderline (2.0 - 3.0 s)" if consensus_crt90 <= 3.0 else "Prolonged (> 3.0 s)")
        elif crt90_threshold is not None:
            consensus_crt90 = crt90_threshold
            best_estimator = "Threshold Crossing (90%)"
            classification = "Normal (< 2.0 s)" if consensus_crt90 < 2.0 else ("Borderline (2.0 - 3.0 s)" if consensus_crt90 <= 3.0 else "Prolonged (> 3.0 s)")
        else:
            consensus_crt90 = None
            best_estimator = "None"
            classification = "UNKNOWN"

        return {
            "is_valid": is_valid,
            "status": "VALID" if is_valid else "INVALID",
            "crt90_estimate": consensus_crt90,
            "crt90_threshold": crt90_threshold,
            "crt90_model": crt90_model,
            "best_estimator": best_estimator,
            "classification": classification,
            "faults": faults,
            "warnings": warnings,
            "base_dc": base_dc,
            "base_std": base_std,
            "blanch_depth": blanch_depth,
            "r2_fit": r2_fit,
            "tau_fit": tau_fit,
            "v_min_fit": v_min_fit,
            "t_rec": t_rec,
            "y_norm": y_norm,
            "x_filtered": x_filtered
        }
