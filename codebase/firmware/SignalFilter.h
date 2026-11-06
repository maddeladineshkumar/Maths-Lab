/**
 * @file SignalFilter.h
 * @brief CRT-Nano: Efficient Embedded Digital Filtering and Envelope Extraction
 * @authors M. Dinesh Kumar (CB.AI.U4AID25126) & Malepati Venkata Sai Sujan (CB.AI.U4AID25129)
 */

#ifndef SIGNAL_FILTER_H
#define SIGNAL_FILTER_H

#include <Arduino.h>

class LowPassFilterEMA {
public:
    LowPassFilterEMA(float alpha = 0.15f) : _alpha(alpha), _filtered(512.0f), _initialized(false) {}

    void reset(float initial_val = 512.0f) {
        _filtered = initial_val;
        _initialized = false;
    }

    float update(float sample) {
        if (!_initialized) {
            _filtered = sample;
            _initialized = true;
        } else {
            _filtered = _alpha * sample + (1.0f - _alpha) * _filtered;
        }
        return _filtered;
    }

    float getValue() const {
        return _filtered;
    }

private:
    float _alpha;
    float _filtered;
    bool  _initialized;
};

class BaselineTracker {
public:
    BaselineTracker() {
        reset();
    }

    void reset() {
        _count = 0;
        _sum = 0.0;
        _sum_sq = 0.0;
        _min_val = 1023;
        _max_val = 0;
    }

    void push(int16_t sample) {
        _count++;
        _sum += sample;
        _sum_sq += ((double)sample * (double)sample);
        if (sample < _min_val) _min_val = sample;
        if (sample > _max_val) _max_val = sample;
    }

    uint16_t getCount() const { return _count; }

    float getMean() const {
        return (_count > 0) ? (float)(_sum / _count) : 512.0f;
    }

    float getStandardDeviation() const {
        if (_count < 2) return 0.0f;
        double mean = _sum / _count;
        double variance = (_sum_sq / _count) - (mean * mean);
        return (variance > 0.0) ? (float)sqrt(variance) : 0.0f;
    }

    int16_t getPeakToPeak() const {
        return (_max_val >= _min_val) ? (_max_val - _min_val) : 0;
    }

private:
    uint16_t _count;
    double   _sum;
    double   _sum_sq;
    int16_t  _min_val;
    int16_t  _max_val;
};

#endif // SIGNAL_FILTER_H
