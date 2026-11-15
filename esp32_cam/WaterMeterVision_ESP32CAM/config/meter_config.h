#pragma once

#include <Arduino.h>

// IMPORTANT:
// These values describe the FINAL ESP32-CAM image after the camera is
// rigidly mounted. They are NOT copied from the PC reference-photo presets.
// Measure them from a real ESP32-CAM frame before enabling calibrated output.

static constexpr bool METER_GEOMETRY_CALIBRATED = false;
static constexpr bool ROTARY_ANGLE_CALIBRATED = false;
static constexpr bool DIGIT_MODEL_AVAILABLE = false;

// Normalized [0..1] coordinates in the ESP32-CAM captured frame.
// Replace these placeholders after camera mounting and frame inspection.
struct NormalizedRect {
  float x1;
  float y1;
  float x2;
  float y2;
};

struct RotaryDialConfig {
  const char *name;
  float centerX;
  float centerY;
  float radius;
  float zeroAngleDeg;  // Angle where the dial reads exactly 0.
  bool clockwise;      // Direction of increasing values.
  float weight;        // Future quality weighting; currently diagnostic only.
};

// Keep labels in the physically verified meter order.
static const char *const DIAL_NAMES[4] = {
  "X0.1", "X0.01", "X0.001", "X0.0001"
};

// TODO: calibrate these values from the actual ESP32-CAM capture.
// Values are intentionally zero and processing is disabled until calibrated.
static const NormalizedRect INTEGER_REGISTER_ROI = {0.0f, 0.0f, 0.0f, 0.0f};

static const RotaryDialConfig ROTARY_DIALS[4] = {
  {"X0.1",     0.0f, 0.0f, 0.0f, 0.0f, true, 1.0f},
  {"X0.01",    0.0f, 0.0f, 0.0f, 0.0f, true, 1.0f},
  {"X0.001",   0.0f, 0.0f, 0.0f, 0.0f, true, 1.0f},
  {"X0.0001",  0.0f, 0.0f, 0.0f, 0.0f, true, 1.0f}
};

static constexpr uint8_t REGISTER_DIGIT_COUNT = 5;
static constexpr uint8_t ROTARY_DIAL_COUNT = 4;
static constexpr uint8_t RED_ANGLE_BINS = 180;
