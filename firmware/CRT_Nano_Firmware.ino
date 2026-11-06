/**
 * @file CRT_Nano_Firmware.ino
 * @brief CRT-Nano Production-Grade Embedded Firmware for Arduino Nano V3
 * @authors M. Dinesh Kumar (CB.AI.U4AID25126) & Malepati Venkata Sai Sujan (CB.AI.U4AID25129)
 * @course 23MAT204 - Lab Exam: Frugal Healthcare AI / Edge Device Challenge
 * @instructor Dr. Suman Dutta
 * @institution Amrita Vishwa Vidyapeetham - School of AI
 * 
 * Hardware Target: Arduino Nano V3 (ATmega328P @ 16 MHz, 5V)
 * Sensor: Generic Optical Reflectance PPG Module (PulseSensor clone)
 * Actuator/Output: Piezo Buzzer (Pin D8), Optional SG90 Servo (Pin D9)
 */

#include "StateTypes.h"
#include "SignalFilter.h"

// System Objects
DeviceState currentState = STATE_IDLE;
FaultCode currentFault = FAULT_NONE;
LowPassFilterEMA ppgFilter(0.15f); // ~2.5 Hz cutoff at 100 Hz sampling
BaselineTracker baselineTracker;
MeasurementRecord currentRecord;

// State Timing & Sampling Control
uint32_t lastSampleTimeMicros = 0;
const uint32_t SAMPLE_INTERVAL_MICROS = 10000; // 100 Hz (10,000 us)
uint32_t stateEnterTimeMs = 0;
uint16_t dwellCounter = 0;
float minBlanchObserved = 1023.0f;
float lastFilteredSample = 512.0f;

// Sound Generator Helpers
void playTone(uint16_t freq, uint16_t duration_ms) {
    tone(FirmwareConfig::PIN_PIEZO_BUZZER, freq, duration_ms);
}

void playCueBeep(uint8_t count, uint16_t freq = 1000) {
    for (uint8_t i = 0; i < count; i++) {
        playTone(freq, 70);
        delay(90);
    }
}

void playSuccessFanfare() {
    tone(FirmwareConfig::PIN_PIEZO_BUZZER, 587, 100); delay(110);
    tone(FirmwareConfig::PIN_PIEZO_BUZZER, 880, 150); delay(160);
    tone(FirmwareConfig::PIN_PIEZO_BUZZER, 1175, 250); delay(260);
}

void playErrorBuzzer() {
    tone(FirmwareConfig::PIN_PIEZO_BUZZER, 400, 150); delay(170);
    tone(FirmwareConfig::PIN_PIEZO_BUZZER, 260, 300); delay(320);
}

// Transition Helper
void changeState(DeviceState newState) {
    currentState = newState;
    stateEnterTimeMs = millis();
    dwellCounter = 0;
    
    // Visual indicator
    digitalWrite(FirmwareConfig::PIN_STATUS_LED, (newState != STATE_IDLE));
}

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 1500); // Wait for serial console on USB
    
    pinMode(FirmwareConfig::PIN_PPG_ANALOG, INPUT);
    pinMode(FirmwareConfig::PIN_STATUS_LED, OUTPUT);
    pinMode(FirmwareConfig::PIN_PIEZO_BUZZER, OUTPUT);
    pinMode(FirmwareConfig::PIN_MODE_SELECT, INPUT_PULLUP);
    
    // Boot Banner
    Serial.println(F("\n========================================================"));
    Serial.println(F("           CRT-Nano: Capillary Refill Time System       "));
    Serial.println(F(" Authors: M. Dinesh Kumar (25126) & Sujan (25129)       "));
    Serial.println(F(" Course: 23MAT204 - Dr. Suman Dutta, Amrita School of AI"));
    Serial.println(F(" Firmware v2.4 (ATmega328P @ 16 MHz, 100 Hz ISR/Loop)   "));
    Serial.println(F("========================================================"));
    Serial.println(F("[SYSTEM READY] Place finger gently over PPG sensor."));
    
    playTone(1046, 120); // High C ready tone
    changeState(STATE_IDLE);
}

void loop() {
    // Precise 100 Hz Sampling Timer
    uint32_t currentMicros = micros();
    if (currentMicros - lastSampleTimeMicros < SAMPLE_INTERVAL_MICROS) {
        return;
    }
    lastSampleTimeMicros = currentMicros;

    // 1. Data Acquisition
    int16_t rawADC = analogRead(FirmwareConfig::PIN_PPG_ANALOG);
    float filteredVal = ppgFilter.update((float)rawADC);
    float sampleDiff = fabsf(filteredVal - lastFilteredSample);
    lastFilteredSample = filteredVal;
    
    uint32_t nowMs = millis();
    uint32_t elapsedStateMs = nowMs - stateEnterTimeMs;

    // 2. State Machine Logic
    switch (currentState) {
        case STATE_IDLE: {
            // Check for finger placement: plausible ADC range and slight pulse dynamics
            if (rawADC >= 100 && rawADC <= 920) {
                dwellCounter++;
                if (dwellCounter >= 80) { // Stable placement for 0.8 seconds
                    Serial.println(F("[EVENT] Finger detected! Hold still for baseline calibration..."));
                    baselineTracker.reset();
                    playCueBeep(1, 880);
                    changeState(STATE_BASELINE);
                }
            } else {
                dwellCounter = 0;
            }
            break;
        }

        case STATE_BASELINE: {
            baselineTracker.push(rawADC);

            // Premature finger lift check
            if (rawADC < FirmwareConfig::ADC_MIN_PLAUSIBLE || rawADC > FirmwareConfig::ADC_MAX_PLAUSIBLE) {
                currentFault = FAULT_F1_SIGNAL_OUT_OF_RANGE;
                changeState(STATE_INVALID);
                break;
            }

            if (elapsedStateMs >= FirmwareConfig::BASELINE_DURATION_MS) {
                float baseMean = baselineTracker.getMean();
                float baseStd  = baselineTracker.getStandardDeviation();
                
                currentRecord.baseline_dc = (int16_t)baseMean;
                currentRecord.baseline_std = (int16_t)baseStd;

                // Quality Check F2: Baseline Stability
                if (baseStd > FirmwareConfig::MAX_BASELINE_DEV) {
                    Serial.print(F("[WARN] Baseline unstable (std="));
                    Serial.print(baseStd);
                    Serial.println(F("). Motion detected."));
                    currentFault = FAULT_F2_BASELINE_UNSTABLE;
                    changeState(STATE_INVALID);
                    break;
                }

                Serial.print(F("[BASELINE OK] Mean DC: "));
                Serial.print(baseMean);
                Serial.print(F(" | Pulsatile Std: "));
                Serial.println(baseStd);
                Serial.println(F("[ACTION] Press firmly on fingertip now (blanching)!"));
                
                playCueBeep(2, 600); // Double low-beep prompt to apply pressure
                minBlanchObserved = filteredVal;
                changeState(STATE_PRESS);
            }
            break;
        }

        case STATE_PRESS: {
            // Track maximum blanching excursion (lowest blood volume point)
            if (filteredVal < minBlanchObserved) {
                minBlanchObserved = filteredVal;
            }

            if (elapsedStateMs >= FirmwareConfig::PRESS_DURATION_MS) {
                float blanchDepth = fabsf((float)currentRecord.baseline_dc - minBlanchObserved);
                currentRecord.blanch_min = (int16_t)minBlanchObserved;
                currentRecord.blanch_depth = (int16_t)blanchDepth;

                // Quality Check F3: Adequate blanching excursion
                if (blanchDepth < FirmwareConfig::MIN_BLANCH_SWING) {
                    Serial.print(F("[WARN] Inadequate blanching excursion (delta="));
                    Serial.print(blanchDepth);
                    Serial.println(F(")."));
                    currentFault = FAULT_F3_INSUFFICIENT_BLANCH;
                    changeState(STATE_INVALID);
                    break;
                }

                Serial.print(F("[BLANCH OK] Depth: "));
                Serial.print(blanchDepth);
                Serial.println(F(" counts. Release finger INSTANTLY!"));

                playTone(1320, 150); // Sharp high-pitch cue to release
                changeState(STATE_RELEASE);
            }
            break;
        }

        case STATE_RELEASE: {
            currentRecord.t_release_ms = millis();
            Serial.println(F("[RECOVERY] Monitoring capillary refill trajectory..."));
            changeState(STATE_RECOVERY);
            break;
        }

        case STATE_RECOVERY: {
            // Quality Check F6: Sudden finger lift
            if (rawADC > FirmwareConfig::ADC_MAX_PLAUSIBLE || rawADC < FirmwareConfig::ADC_MIN_PLAUSIBLE) {
                currentFault = FAULT_F6_FINGER_DETACHED;
                changeState(STATE_INVALID);
                break;
            }

            // Quality Check F4: Motion jerk artifact during recovery
            if (sampleDiff > FirmwareConfig::MAX_RECOVERY_JERK) {
                currentFault = FAULT_F4_MOTION_ARTEFACT;
                changeState(STATE_INVALID);
                break;
            }

            // Calculate normalized refill progress y in [0, 100]%
            float span = (float)currentRecord.baseline_dc - (float)currentRecord.blanch_min;
            if (span < 1.0f) span = 1.0f;
            float currentProgress = ((filteredVal - (float)currentRecord.blanch_min) / span) * 100.0f;

            // Stream live telemetry for plotting (comma-separated format)
            if (elapsedStateMs % 100 == 0) {
                Serial.print(F("DATA,"));
                Serial.print((float)elapsedStateMs / 1000.0f, 2);
                Serial.print(F(","));
                Serial.print(filteredVal, 1);
                Serial.print(F(","));
                Serial.println(currentProgress, 1);
            }

            // Target condition: Reach and sustain 90% refill (CRT90)
            if (currentProgress >= FirmwareConfig::THRESHOLD_PERCENT) {
                dwellCounter++;
                if (dwellCounter >= FirmwareConfig::DWELL_SAMPLES) {
                    // Confirmed refill!
                    uint32_t dwellTimeMs = (uint32_t)FirmwareConfig::DWELL_SAMPLES * 10;
                    uint32_t totalElapsed = nowMs - currentRecord.t_release_ms;
                    uint32_t refillElapsed = (totalElapsed > dwellTimeMs) ? (totalElapsed - dwellTimeMs) : 0;
                    currentRecord.crt90_ms = (uint16_t)refillElapsed;
                    currentRecord.is_valid = true;
                    currentRecord.fault = FAULT_NONE;
                    changeState(STATE_REPORT);
                    break;
                }
            } else {
                dwellCounter = 0;
            }

            // Timeout condition
            if (elapsedStateMs >= FirmwareConfig::RECOVERY_TIMEOUT_MS) {
                Serial.println(F("[WARN] Recovery exceeded timeout window (7s)."));
                currentRecord.crt90_ms = FirmwareConfig::RECOVERY_TIMEOUT_MS;
                currentRecord.is_valid = true; // Mark as prolonged rather than error
                currentRecord.fault = FAULT_NONE;
                changeState(STATE_REPORT);
            }
            break;
        }

        case STATE_REPORT: {
            Serial.println(F("\n================= TRIAL REPORT ================="));
            Serial.print(F("Status:          VALID MEASUREMENT\n"));
            Serial.print(F("Estimated CRT90: "));
            float crt_sec = (float)currentRecord.crt90_ms / 1000.0f;
            Serial.print(crt_sec, 2);
            Serial.println(F(" seconds"));
            
            Serial.print(F("Clinical Band:   "));
            if (crt_sec < 2.0f) {
                Serial.println(F("NORMAL (< 2.0 s)"));
            } else if (crt_sec <= 3.0f) {
                Serial.println(F("BORDERLINE (2.0 - 3.0 s)"));
            } else {
                Serial.println(F("PROLONGED (> 3.0 s)"));
            }

            Serial.print(F("Baseline Mean:   ")); Serial.print(currentRecord.baseline_dc); Serial.println(F(" counts"));
            Serial.print(F("Blanch Delta:    ")); Serial.print(currentRecord.blanch_depth); Serial.println(F(" counts"));
            Serial.println(F("================================================\n"));

            playSuccessFanfare();
            delay(3000); // Hold display
            Serial.println(F("[READY] Remove finger or place next finger for trial."));
            changeState(STATE_IDLE);
            break;
        }

        case STATE_INVALID: {
            Serial.println(F("\n[!] MEASUREMENT REJECTED BY QUALITY GATE"));
            Serial.print(F("Fault Code: "));
            switch (currentFault) {
                case FAULT_F1_SIGNAL_OUT_OF_RANGE:
                    Serial.println(F("F1 - Signal out of range or sensor saturated.")); break;
                case FAULT_F2_BASELINE_UNSTABLE:
                    Serial.println(F("F2 - Baseline unstable. Hand movement detected.")); break;
                case FAULT_F3_INSUFFICIENT_BLANCH:
                    Serial.println(F("F3 - Insufficient pressing force. Finger did not blanch.")); break;
                case FAULT_F4_MOTION_ARTEFACT:
                    Serial.println(F("F4 - Motion artifact during recovery trajectory.")); break;
                case FAULT_F5_ESTIMATOR_DIVERGENCE:
                    Serial.println(F("F5 - Signal model divergence.")); break;
                case FAULT_F6_FINGER_DETACHED:
                    Serial.println(F("F6 - Premature finger release during observation.")); break;
                default:
                    Serial.println(F("Unknown fault.")); break;
            }
            Serial.println(F("Remediation: Rest finger comfortably on sensor, remain still, and press firmly when prompted."));
            playErrorBuzzer();
            delay(2500);
            changeState(STATE_IDLE);
            break;
        }
    }
}
