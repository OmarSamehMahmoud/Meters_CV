#include "reading_engine.h"

void printMeterReading(const MeterReadingResult &result) {
  Serial.println();
  Serial.println("========== WATER METER RESULT ==========");

  if (result.integerDigitsAvailable) {
    Serial.printf("Integer register : %s m3\n", result.integerDigits);
  } else {
    Serial.println("Integer register : NOT AVAILABLE (digit model not installed)");
  }

  static const float weights[ROTARY_DIAL_COUNT] = {
    0.1f, 0.01f, 0.001f, 0.0001f
  };

  bool allDialsCalibrated = true;
  float fractional = 0.0f;

  for (uint8_t i = 0; i < ROTARY_DIAL_COUNT; ++i) {
    const RotaryDetection &dial = result.dials[i];
    Serial.printf("%-8s : ", DIAL_NAMES[i]);

    if (!dial.detected) {
      Serial.println("POINTER NOT DETECTED");
      allDialsCalibrated = false;
      continue;
    }

    Serial.printf("angle=%6.1f deg, red_pixels=%u, confidence=%.2f",
                  dial.angleDeg, dial.redPixelCount, dial.confidence);

    if (dial.valueCalibrated) {
      Serial.printf(", digit=%.2f\n", dial.dialDigit);
      fractional += dial.dialDigit * weights[i];
    } else {
      Serial.println(", value=NEEDS CALIBRATION");
      allDialsCalibrated = false;
    }
  }

  if (result.integerDigitsAvailable && allDialsCalibrated) {
    Serial.printf("Fractional part  : %.4f m3\n", fractional);
    Serial.printf("Total            : %s + %.4f m3\n",
                  result.integerDigits, fractional);
  } else {
    Serial.println("FINAL READING    : NEEDS REVIEW");
    Serial.println("No uncalibrated or missing value is guessed.");
  }

  Serial.println("========================================");
}
