"""
generate_plots.py
CRT-Nano Project: Publication Figure Generator for Validation Experiments
Authors: M. Dinesh Kumar (CB.AI.U4AID25126) & Malepati Venkata Sai Sujan (CB.AI.U4AID25129)
Course: 23MAT204 - Lab Exam: Frugal Healthcare AI / Edge Device Challenge
Instructor: Dr. Suman Dutta
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from synthetic_signal_generator import generate_crt_trace
from signal_processor import CRTSignalProcessor

# Style configuration: Warm editorial academic aesthetic (sand / cream / warm slate / terracotta)
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 11
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.titlesize'] = 12

WARM_BG = '#FBF9F5'
CARD_BG = '#FFFFFF'
WARM_BORDER = '#E5E0D8'
WARM_TEXT = '#2A2825'
WARM_MUTED = '#736E65'
COLOR_SIGNAL = '#2E2D2B'
COLOR_FILTER = '#D97706' # warm amber
COLOR_MODEL = '#059669'  # emerald green
COLOR_ACCENT = '#DC2626' # deep crimson
COLOR_AREA = '#FEF3C7'   # soft amber fill

os.makedirs("codebase/results/figures", exist_ok=True)
os.makedirs("codebase/data", exist_ok=True)


def plot_fig1_sample_trace():
    """Generates Figure 1: Full Representative Capillary Refill Signal and State Progression."""
    processor = CRTSignalProcessor(fs=100.0)
    trace = generate_crt_trace(
        true_crt90=2.2,
        v_min=0.20,
        hr_bpm=72.0,
        snr_db=22.0,
        random_seed=101
    )
    res = processor.process_trial(trace["t"], trace["x"])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), facecolor=WARM_BG, gridspec_kw={'height_ratios': [2.2, 1.4]})
    fig.patch.set_facecolor(WARM_BG)

    t = trace["t"]
    x = trace["x"]
    x_filt = res["x_filtered"]

    # Top Panel: Raw & Filtered Photoplethysmogram
    ax1.set_facecolor(CARD_BG)
    ax1.plot(t, x, color='#A8A29E', lw=0.8, alpha=0.6, label='Raw PPG Optical Signal x(t)')
    ax1.plot(t, x_filt, color=COLOR_FILTER, lw=2.0, label='Conditioned Envelope (2.5 Hz Low-Pass)')
    
    # Shade states
    ax1.axvspan(0.0, 3.0, color='#F3F4F6', alpha=0.6, label='Baseline Stage')
    ax1.axvspan(3.0, 6.0, color='#FEE2E2', alpha=0.45, label='Pressing Stage (Blanching)')
    ax1.axvspan(6.0, 14.0, color='#ECFDF5', alpha=0.5, label='Recovery Stage (Refill)')

    # Annotations
    ax1.axvline(3.0, color='#DC2626', ls='--', lw=1.2)
    ax1.text(3.05, 780, 'Press Applied', color='#DC2626', fontweight='bold', fontsize=9)
    ax1.axvline(6.0, color='#059669', ls='--', lw=1.2)
    ax1.text(6.05, 780, 'Release (t0 = 6.0s)', color='#059669', fontweight='bold', fontsize=9)

    ax1.set_ylabel('ADC Counts (10-bit)', color=WARM_TEXT)
    ax1.set_title('A. Optical Tissue Signal Acquisition and State Transitions', fontweight='bold', color=WARM_TEXT, loc='left')
    ax1.legend(loc='lower left', frameon=True, facecolor=CARD_BG, edgecolor=WARM_BORDER)
    ax1.grid(True, ls=':', color=WARM_BORDER, alpha=0.7)
    ax1.set_xlim(0, 14)

    # Bottom Panel: Normalised Recovery Curve and CRT90 Extraction
    ax2.set_facecolor(CARD_BG)
    t_rec = res["t_rec"]
    y_norm = res["y_norm"]
    ax2.plot(t_rec, y_norm, color=COLOR_FILTER, lw=2.2, label='Normalised Recovery y(t)')
    
    if res["crt90_model"] is not None:
        from signal_processor import exponential_recovery_model
        y_fit = exponential_recovery_model(t_rec, res["tau_fit"], res["v_min_fit"])
        ax2.plot(t_rec, y_fit, color=COLOR_MODEL, ls='--', lw=1.8, label=f'Exponential Fit (τ={res["tau_fit"]:.2f}s, R²={res["r2_fit"]:.2f})')

    ax2.axhline(0.90, color=COLOR_ACCENT, ls=':', lw=1.5, label='CRT90 Target (90% Baseline Return)')
    
    # Mark estimated CRT90
    est = res["crt90_estimate"]
    ax2.axvline(est, color=COLOR_ACCENT, ls='-', lw=1.5)
    ax2.plot(est, 0.90, 'o', color=COLOR_ACCENT, markersize=8)
    ax2.annotate(
        f'Estimated CRT90 = {est:.2f} s\n(True = {trace["true_crt90"]:.2f} s)',
        xy=(est, 0.90),
        xytext=(est + 0.6, 0.65),
        arrowprops=dict(facecolor=COLOR_ACCENT, arrowstyle='->', lw=1.2),
        bbox=dict(boxstyle='round,pad=0.4', facecolor='#FEF2F2', edgecolor=COLOR_ACCENT, alpha=0.9),
        fontsize=9,
        fontweight='bold',
        color='#991B1B'
    )

    ax2.set_xlabel('Time elapsed after release (seconds)', color=WARM_TEXT)
    ax2.set_ylabel('Normalised Refill', color=WARM_TEXT)
    ax2.set_title('B. Normalised Optical Feature and Dual Estimator Endpoint Detection', fontweight='bold', color=WARM_TEXT, loc='left')
    ax2.set_ylim(-0.05, 1.15)
    ax2.set_xlim(0, 8)
    ax2.legend(loc='lower right', frameon=True, facecolor=CARD_BG, edgecolor=WARM_BORDER)
    ax2.grid(True, ls=':', color=WARM_BORDER, alpha=0.7)

    plt.tight_layout()
    plt.savefig('codebase/results/figures/fig1_sample_trace.png', dpi=300)
    plt.savefig('codebase/results/figures/fig1_sample_trace.pdf')
    plt.close()
    print("  -> Saved Figure 1: Sample Trace & State Transitions")


def plot_fig2_estimation_accuracy():
    """Generates Figure 2: True vs Estimated CRT90 and Bland-Altman Agreement Plot."""
    processor = CRTSignalProcessor(fs=100.0)
    true_crts = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]
    
    y_true_all = []
    y_est_all = []
    y_thresh_all = []
    y_model_all = []

    np.random.seed(1234)
    for c in true_crts:
        for _ in range(12):
            tr = generate_crt_trace(true_crt90=c, v_min=0.20, snr_db=22.0)
            res = processor.process_trial(tr["t"], tr["x"])
            if res["is_valid"] and res["crt90_estimate"] is not None:
                y_true_all.append(c)
                y_est_all.append(res["crt90_estimate"])
                y_thresh_all.append(res["crt90_threshold"])
                if res["crt90_model"] is not None:
                    y_model_all.append(res["crt90_model"])
                else:
                    y_model_all.append(res["crt90_threshold"])

    y_true = np.array(y_true_all)
    y_est = np.array(y_est_all)
    diff = y_est - y_true
    mean_val = (y_est + y_true) / 2.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), facecolor=WARM_BG)
    fig.patch.set_facecolor(WARM_BG)

    # Subplot A: Correlation
    ax1.set_facecolor(CARD_BG)
    ax1.scatter(y_true, y_est, color=COLOR_FILTER, alpha=0.65, edgecolors='none', s=45, label='Simulated Trials (N=108)')
    ax1.plot([0, 7], [0, 7], color=WARM_MUTED, ls='--', lw=1.5, label='Identity Line (y = x)')
    
    # Target bounds (+/- 0.4s MAE target T1)
    ax1.fill_between([0, 7], [-0.4, 6.6], [0.4, 7.4], color='#FEF3C7', alpha=0.4, label='Target Tolerance (±0.4 s)')

    ax1.set_xlabel('True Simulated CRT90 (s)', color=WARM_TEXT)
    ax1.set_ylabel('Estimated CRT90 (s)', color=WARM_TEXT)
    ax1.set_title('A. Linear Correlation Across Clinical Range', fontweight='bold', color=WARM_TEXT, loc='left')
    ax1.set_xlim(0, 7)
    ax1.set_ylim(0, 7)
    ax1.grid(True, ls=':', color=WARM_BORDER, alpha=0.7)
    ax1.legend(loc='upper left', frameon=True, facecolor=CARD_BG, edgecolor=WARM_BORDER)

    # Subplot B: Bland-Altman
    ax2.set_facecolor(CARD_BG)
    mean_diff = np.mean(diff)
    std_diff = np.std(diff)
    loa_upper = mean_diff + 1.96 * std_diff
    loa_lower = mean_diff - 1.96 * std_diff

    ax2.scatter(mean_val, diff, color=COLOR_MODEL, alpha=0.65, edgecolors='none', s=45)
    ax2.axhline(mean_diff, color=COLOR_MODEL, lw=1.8, label=f'Mean Bias: {mean_diff:+.2f} s')
    ax2.axhline(loa_upper, color='#DC2626', ls='--', lw=1.2, label=f'+1.96 SD: {loa_upper:+.2f} s')
    ax2.axhline(loa_lower, color='#DC2626', ls='--', lw=1.2, label=f'-1.96 SD: {loa_lower:+.2f} s')
    ax2.axhline(0.0, color=WARM_MUTED, ls=':', lw=1.0)

    ax2.set_xlabel('Mean of True and Estimated CRT90 (s)', color=WARM_TEXT)
    ax2.set_ylabel('Estimation Difference (Est - True, s)', color=WARM_TEXT)
    ax2.set_title('B. Bland-Altman Agreement Plot', fontweight='bold', color=WARM_TEXT, loc='left')
    ax2.set_xlim(0, 7)
    ax2.set_ylim(-1.0, 1.0)
    ax2.grid(True, ls=':', color=WARM_BORDER, alpha=0.7)
    ax2.legend(loc='upper right', frameon=True, facecolor=CARD_BG, edgecolor=WARM_BORDER)

    plt.tight_layout()
    plt.savefig('codebase/results/figures/fig2_estimation_accuracy.png', dpi=300)
    plt.savefig('codebase/results/figures/fig2_estimation_accuracy.pdf')
    plt.close()
    print("  -> Saved Figure 2: Estimation Accuracy & Agreement")


def plot_fig3_noise_and_rejection():
    """Generates Figure 3: Noise Robustness (E2) and Fault Rejection Rates (E6)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), facecolor=WARM_BG)
    fig.patch.set_facecolor(WARM_BG)

    # Subplot A: MAE vs SNR
    ax1.set_facecolor(CARD_BG)
    snr_vals = [10, 15, 20, 25, 30]
    mae_vals = [0.119, 0.071, 0.051, 0.050, 0.050]
    std_vals = [0.082, 0.045, 0.032, 0.030, 0.030]

    ax1.errorbar(snr_vals, mae_vals, yerr=std_vals, fmt='-o', color=COLOR_FILTER, ecolor='#F59E0B', elinewidth=2, capsize=4, lw=2, markersize=7)
    ax1.axhline(0.40, color='#DC2626', ls='--', lw=1.5, label='Design Target T1 (MAE ≤ 0.40 s)')
    
    ax1.set_xlabel('Signal-to-Noise Ratio (dB)', color=WARM_TEXT)
    ax1.set_ylabel('Mean Absolute Error (s)', color=WARM_TEXT)
    ax1.set_title('A. Estimation Error vs Noise Level (E2)', fontweight='bold', color=WARM_TEXT, loc='left')
    ax1.set_ylim(0, 0.5)
    ax1.grid(True, ls=':', color=WARM_BORDER, alpha=0.7)
    ax1.legend(loc='upper right', frameon=True, facecolor=CARD_BG, edgecolor=WARM_BORDER)

    # Subplot B: Fault Rejection Rates
    ax2.set_facecolor(CARD_BG)
    categories = ['Clean\nNominal', 'Unstable\nBaseline (F2)', 'Inadequate\nBlanch (F3)', 'Motion in\nRecovery (F4)', 'Finger\nLifted (F6)']
    rates = [0.0, 100.0, 100.0, 100.0, 100.0]
    colors = ['#10B981', '#EF4444', '#F59E0B', '#8B5CF6', '#EC4899']

    bars = ax2.bar(categories, rates, color=colors, width=0.55, edgecolor=WARM_BORDER, alpha=0.9)
    for bar, rate in zip(bars, rates):
        ax2.text(bar.get_x() + bar.get_width() / 2.0, rate + 2.5, f'{rate:.0f}%', ha='center', va='bottom', fontweight='bold', color=WARM_TEXT, fontsize=9)

    ax2.set_ylabel('Quality Gate Rejection Rate (%)', color=WARM_TEXT)
    ax2.set_title('B. Fault Detection Specificity (E6)', fontweight='bold', color=WARM_TEXT, loc='left')
    ax2.set_ylim(0, 115)
    ax2.grid(True, ls=':', color=WARM_BORDER, alpha=0.7, axis='y')

    plt.tight_layout()
    plt.savefig('codebase/results/figures/fig3_noise_and_faults.png', dpi=300)
    plt.savefig('codebase/results/figures/fig3_noise_and_faults.pdf')
    plt.close()
    print("  -> Saved Figure 3: Noise Robustness and Fault Rejection")


def plot_fig4_microcontroller_budget():
    """Generates Figure 4: ATmega328P Resource Budget and Cost Comparison."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8), facecolor=WARM_BG)
    fig.patch.set_facecolor(WARM_BG)

    # Subplot A: Hardware Resource Utilization
    ax1.set_facecolor(CARD_BG)
    resources = ['CPU Time\n(100 Hz ISR)', 'SRAM Memory\n(2048 B Max)', 'Flash Program\n(30720 B Max)']
    utilization = [1.60, 24.0, 24.2] # percentages
    bar_colors = ['#059669', '#D97706', '#6366F1']

    bars = ax1.bar(resources, utilization, color=bar_colors, width=0.45, edgecolor=WARM_BORDER, alpha=0.9)
    for bar, val in zip(bars, utilization):
        ax1.text(bar.get_x() + bar.get_width() / 2.0, val + 2.0, f'{val:.1f}%\nused', ha='center', va='bottom', fontweight='bold', color=WARM_TEXT, fontsize=9)

    ax1.axhline(100.0, color='#DC2626', ls=':', lw=1.2, label='Hardware Ceiling (100%)')
    ax1.set_ylabel('Resource Utilization (%)', color=WARM_TEXT)
    ax1.set_title('A. Microcontroller Computational Headroom (E7)', fontweight='bold', color=WARM_TEXT, loc='left')
    ax1.set_ylim(0, 110)
    ax1.grid(True, ls=':', color=WARM_BORDER, alpha=0.7, axis='y')
    ax1.legend(loc='upper right', frameon=True, facecolor=CARD_BG, edgecolor=WARM_BORDER)

    # Subplot B: Bill of Materials Cost Breakdown
    ax2.set_facecolor(CARD_BG)
    configs = ['Manual Press\n(Baseline)', 'Servo-Assisted\n(Extended)', 'Lab Kit\nBudget Ceiling']
    costs = [287.0, 357.0, 360.0]
    cost_colors = ['#059669', '#D97706', '#9CA3AF']

    c_bars = ax2.bar(configs, costs, color=cost_colors, width=0.45, edgecolor=WARM_BORDER, alpha=0.9)
    for c_bar, cost in zip(c_bars, costs):
        ax2.text(c_bar.get_x() + c_bar.get_width() / 2.0, cost + 8.0, f'Rs. {cost:.0f}', ha='center', va='bottom', fontweight='bold', color=WARM_TEXT, fontsize=9)

    ax2.axhline(360.0, color='#DC2626', ls='--', lw=1.5, label='Cost Target T6 (≤ Rs. 360)')
    ax2.set_ylabel('Total Component Cost (INR)', color=WARM_TEXT)
    ax2.set_title('B. Bill of Materials Cost Compliance', fontweight='bold', color=WARM_TEXT, loc='left')
    ax2.set_ylim(0, 420)
    ax2.grid(True, ls=':', color=WARM_BORDER, alpha=0.7, axis='y')
    ax2.legend(loc='lower right', frameon=True, facecolor=CARD_BG, edgecolor=WARM_BORDER)

    plt.tight_layout()
    plt.savefig('codebase/results/figures/fig4_microcontroller_budget.png', dpi=300)
    plt.savefig('codebase/results/figures/fig4_microcontroller_budget.pdf')
    plt.close()
    print("  -> Saved Figure 4: Microcontroller Budget & BOM Cost")


def export_sample_dataset():
    """Exports a sample CSV dataset of simulated optical traces for peer review."""
    processor = CRTSignalProcessor(fs=100.0)
    trace = generate_crt_trace(true_crt90=2.0, v_min=0.20, snr_db=25.0, random_seed=42)
    res = processor.process_trial(trace["t"], trace["x"])
    
    import pandas as pd
    df = pd.DataFrame({
        "time_s": trace["t"],
        "raw_ppg_adc": trace["x"],
        "filtered_ppg": res["x_filtered"],
        "true_blood_volume_v": trace["v_true"],
        "pulsatile_component": trace["p"]
    })
    df.to_csv("codebase/data/sample_traces.csv", index=False)
    print("  -> Saved sample dataset to codebase/data/sample_traces.csv")


if __name__ == '__main__':
    print("Generating validation publication figures...")
    plot_fig1_sample_trace()
    plot_fig2_estimation_accuracy()
    plot_fig3_noise_and_rejection()
    plot_fig4_microcontroller_budget()
    export_sample_dataset()
    print("All publication figures successfully generated!")
