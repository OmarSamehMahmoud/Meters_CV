#pragma once

#include <Arduino.h>
#include "../config/meter_config.h"

struct RotaryDetection {
  bool detected;
  float angleDeg;
  float confidence;
  uint16_t redPixelCount;
  float dialDigit;
  bool valueCalibrated;
};

// Input must be interleaved RGB888 (R,G,B), width x height pixels.
RotaryDetection detectRedPointer(
    const uint8_t *rgb,
    uint16_t imageWidth,
    uint16_t imageHeight,
    const RotaryDialConfig &dial,
    bool angleCalibrationEnabled);
