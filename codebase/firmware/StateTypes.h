/**
 * @file StateTypes.h
 * @brief CRT-Nano: Data structures, State Enums, and Configuration Constants
 * @authors M. Dinesh Kumar (CB.AI.U4AID25126) & Malepati Venkata Sai Sujan (CB.AI.U4AID25129)
 * @course 23MAT204 - Lab Exam: Frugal Healthcare AI / Edge Device Challenge
 * @instructor Dr. Suman Dutta
 */

#ifndef STATE_TYPES_H
#define STATE_TYPES_H

#include <Arduino.h>

// Finite State Machine States (Section 10.1, Figure 5 of Proposal)
enum DeviceState {
    STATE_IDLE,       // 0: Waiting for finger contact
    STATE_BASELINE,   // 1: Acquiring stable pre-press optical baseline (3 seconds)
    STATE_PRESS,      // 2: Tissue compression & blanching phase (manual or servo)
    STATE_RELEASE,    // 3: Release event marked (timestamp t0 registered)
    STATE_RECOVERY,   // 4: Monitoring optical reperfusion trajectory
    STATE_REPORT,     // 5: Telemetry output, estimation summary & audio feedback
    STATE_INVALID     // 6: Fault handling & error reporting
};

// Fault Diagnostic Codes (Section 10.3, Table 5 of Proposal)
enum FaultCode {
    FAULT_NONE = 0,
    FAULT_F1_SIGNAL_OUT_OF_RANGE = 1, // Saturation or open-circuit
    FAULT_F2_BASELINE_UNSTABLE   = 2, // Excessive motion/drift before press
    FAULT_F3_INSUFFICIENT_BLANCH = 3, // Inadequate pressure applied
    FAULT_F4_MOTION_ARTEFACT     = 4, // Sudden jerk or tremor during refill
    FAULT_F5_ESTIMATOR_DIVERGENCE= 5, // Disagreement between candidate estimators
    FAULT_F6_FINGER_DETACHED     = 6  // Premature sensor release
};

// Configuration & Calibration Constants
struct FirmwareConfig {
    static const uint16_t SAMPLING_RATE_HZ = 100;       // 100 Hz sampling (10 ms period)
    static const uint16_t BASELINE_DURATION_MS = 3000;  // 3.0 s baseline window
    static const uint16_t PRESS_DURATION_MS    = 3000;  // 3.0 s pressing hold window
    static const uint16_t RECOVERY_TIMEOUT_MS  = 7000;  // 7.0 s maximum recovery window
    
    // Pin Definitions
    static const uint8_t PIN_PPG_ANALOG   = A0; // Optical sensor analog output
    static const uint8_t PIN_THERMISTOR   = A1; // Optional NTC thermistor divider
    static const uint8_t PIN_MODE_SELECT  = 2;  // Pushbutton / jumper (INPUT_PULLUP)
    static const uint8_t PIN_PIEZO_BUZZER = 8;  // Audio status output
    static const uint8_t PIN_SERVO_PWM    = 9;  // Optional SG90 micro servo PWM
    static const uint8_t PIN_STATUS_LED   = 13; // Onboard debug LED
    
    // Quality Gate Thresholds
    static const int16_t ADC_MIN_PLAUSIBLE = 25;   // Below this -> disconnected / dark
    static const int16_t ADC_MAX_PLAUSIBLE = 995;  // Above this -> saturated ambient light
    static const int16_t MIN_BLANCH_SWING  = 35;   // Minimum required blanching drop (ADC counts)
    static const int16_t MAX_BASELINE_DEV  = 30;   // Maximum allowed baseline standard deviation
    static const int16_t MAX_RECOVERY_JERK = 80;   // Maximum sample-to-sample slope during recovery
    
    // Recovery Target
    static const uint8_t THRESHOLD_PERCENT = 90;   // CRT90 definition (90% return to baseline)
    static const uint8_t DWELL_SAMPLES     = 15;   // 150 ms sustained hold to confirm refill
};

// Trial Measurement Data Container
struct MeasurementRecord {
    uint32_t t_start_ms;
    uint32_t t_release_ms;
    int16_t  baseline_dc;
    int16_t  baseline_std;
    int16_t  blanch_min;
    int16_t  blanch_depth;
    uint16_t crt90_ms;
    FaultCode fault;
    bool     is_valid;
};

#endif // STATE_TYPES_H
