"""
test_suite.py
CRT-Nano Project: Comprehensive Automated Verification & Unit Test Suite
Authors: M. Dinesh Kumar (CB.AI.U4AID25126) & Malepati Venkata Sai Sujan (CB.AI.U4AID25129)
Course: 23MAT204 - Lab Exam: Frugal Healthcare AI / Edge Device Challenge
Instructor: Dr. Suman Dutta
"""

import unittest
import numpy as np
from synthetic_signal_generator import generate_crt_trace, generate_cardiac_pulse
from signal_processor import CRTSignalProcessor, butter_lowpass_filter, exponential_recovery_model


class TestCRTSignalGenerator(unittest.TestCase):
    def test_pulse_shape_and_bounds(self):
        t = np.linspace(0, 2.0, 200)
        p = generate_cardiac_pulse(t, hr_bpm=60.0)
        self.assertEqual(len(p), 200)
        self.assertAlmostEqual(float(np.min(p)), 0.0, places=3)
        self.assertAlmostEqual(float(np.max(p)), 1.0, places=3)

    def test_trace_generation_bounds(self):
        tr = generate_crt_trace(true_crt90=2.0, snr_db=30.0, random_seed=42)
        self.assertTrue(np.all(tr["x"] >= 0.0))
        self.assertTrue(np.all(tr["x"] <= 1023.0))
        self.assertAlmostEqual(tr["true_crt90"], 2.0, places=4)
        self.assertGreater(tr["tau"], 0.0)

    def test_artifact_injection_motion(self):
        tr = generate_crt_trace(artifact_type="motion_recovery", random_seed=42)
        self.assertEqual(tr["artifact_type"], "motion_recovery")
        # Peak during recovery should be significantly higher due to motion burst
        idx_rec = np.where(tr["t"] >= tr["t_release"])[0]
        self.assertGreater(np.max(tr["x"][idx_rec]), 350.0)

    def test_artifact_injection_finger_lift(self):
        tr = generate_crt_trace(artifact_type="finger_lift", random_seed=42)
        idx_tail = np.where(tr["t"] >= tr["t_release"] + 2.5)[0]
        self.assertTrue(np.all(tr["x"][idx_tail] > 950.0))


class TestCRTSignalProcessor(unittest.TestCase):
    def setUp(self):
        self.proc = CRTSignalProcessor(fs=100.0)

    def test_clean_trace_estimation_accuracy(self):
        true_val = 2.0
        tr = generate_crt_trace(true_crt90=true_val, snr_db=30.0, v_min=0.20, random_seed=123)
        res = self.proc.process_trial(tr["t"], tr["x"])
        self.assertTrue(res["is_valid"], f"Expected clean trace to be valid, got faults: {res['faults']}")
        self.assertIsNotNone(res["crt90_estimate"])
        err = abs(res["crt90_estimate"] - true_val)
        self.assertLess(err, 0.35, f"Error {err:.3f} exceeds tolerance 0.35s")

    def test_short_crt_estimation(self):
        true_val = 0.8
        tr = generate_crt_trace(true_crt90=true_val, snr_db=25.0, v_min=0.20, random_seed=55)
        res = self.proc.process_trial(tr["t"], tr["x"])
        self.assertTrue(res["is_valid"])
        err = abs(res["crt90_estimate"] - true_val)
        self.assertLess(err, 0.40)

    def test_long_crt_estimation(self):
        true_val = 4.5
        tr = generate_crt_trace(true_crt90=true_val, snr_db=25.0, v_min=0.20, random_seed=77)
        res = self.proc.process_trial(tr["t"], tr["x"])
        self.assertTrue(res["is_valid"])
        err = abs(res["crt90_estimate"] - true_val)
        self.assertLess(err, 0.45)

    def test_fault_f1_sensor_saturation(self):
        t = np.linspace(0, 14, 1400)
        x = np.ones_like(t) * 1020.0 # saturated ADC
        res = self.proc.process_trial(t, x)
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("F1" in f for f in res["faults"]))

    def test_fault_f2_unstable_baseline(self):
        tr = generate_crt_trace(drift_type="sinusoidal", drift_mag=60.0, random_seed=88)
        res = self.proc.process_trial(tr["t"], tr["x"])
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("F2" in f for f in res["faults"]))

    def test_fault_f3_inadequate_blanch(self):
        tr = generate_crt_trace(artifact_type="weak_blanch", random_seed=99)
        res = self.proc.process_trial(tr["t"], tr["x"])
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("F3" in f for f in res["faults"]))

    def test_fault_f4_motion_during_recovery(self):
        tr = generate_crt_trace(artifact_type="motion_recovery", random_seed=111)
        res = self.proc.process_trial(tr["t"], tr["x"])
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("F4" in f for f in res["faults"]))

    def test_fault_f6_finger_lifted(self):
        tr = generate_crt_trace(artifact_type="finger_lift", random_seed=222)
        res = self.proc.process_trial(tr["t"], tr["x"])
        self.assertFalse(res["is_valid"])
        self.assertTrue(any("F6" in f for f in res["faults"]))

    def test_edge_case_flat_signal(self):
        t = np.linspace(0, 14, 1400)
        x = np.ones_like(t) * 512.0 # flat line
        res = self.proc.process_trial(t, x)
        self.assertFalse(res["is_valid"])
        self.assertIsNone(res["crt90_estimate"])
        self.assertTrue(any("F3" in f for f in res["faults"]))

    def test_edge_case_empty_array(self):
        res = self.proc.process_trial(np.array([]), np.array([]))
        self.assertFalse(res["is_valid"])
        self.assertIsNone(res["crt90_estimate"])
        self.assertTrue(any("F1" in f for f in res["faults"]))

    def test_edge_case_mismatched_lengths(self):
        t = np.linspace(0, 10, 1000)
        x = np.ones(500) * 512.0
        res = self.proc.process_trial(t, x)
        self.assertFalse(res["is_valid"])
        self.assertIsNone(res["crt90_estimate"])
        self.assertTrue(any("F1" in f for f in res["faults"]))

    def test_edge_case_nan_and_inf_inputs(self):
        t = np.linspace(0, 14, 1400)
        x = np.ones_like(t) * 512.0
        x[50] = np.nan
        x[120] = np.inf
        res = self.proc.process_trial(t, x)
        self.assertFalse(res["is_valid"])
        self.assertIsNone(res["crt90_estimate"])
        self.assertTrue(any("F1" in f for f in res["faults"]))
        self.assertTrue(res["classification"].startswith("REJECTED"))

    def test_edge_case_truncated_before_release(self):
        t = np.linspace(0, 5, 500)
        x = np.ones(500) * 512.0
        x[350:] = 200.0  # Blanch occurred, but trial was cut off before release
        res = self.proc.process_trial(t, x, t_press_start=3.0, t_release=6.0)
        self.assertFalse(res["is_valid"])
        self.assertIsNone(res["crt90_estimate"])
        self.assertTrue(any("F1" in f for f in res["faults"]))

    def test_invalid_trials_suppress_numeric_estimate(self):
        # All invalid trials must report None for crt90_estimate (Proposal Section 10.3)
        tr_weak = generate_crt_trace(artifact_type="weak_blanch", random_seed=42)
        res_weak = self.proc.process_trial(tr_weak["t"], tr_weak["x"])
        self.assertFalse(res_weak["is_valid"])
        self.assertIsNone(res_weak["crt90_estimate"])
        self.assertTrue(res_weak["classification"].startswith("REJECTED"))

        tr_motion = generate_crt_trace(artifact_type="motion_recovery", random_seed=42)
        res_motion = self.proc.process_trial(tr_motion["t"], tr_motion["x"])
        self.assertFalse(res_motion["is_valid"])
        self.assertIsNone(res_motion["crt90_estimate"])
        self.assertTrue(res_motion["classification"].startswith("REJECTED"))


if __name__ == "__main__":
    unittest.main()
