#pragma once

#include <Arduino.h>
#include "../vision/red_pointer_detector.h"

struct MeterReadingResult {
  bool integerDigitsAvailable;
  char integerDigits[REGISTER_DIGIT_COUNT + 1];
  RotaryDetection dials[ROTARY_DIAL_COUNT];
  bool complete;
  float readingM3;
};

void printMeterReading(const MeterReadingResult &result);
