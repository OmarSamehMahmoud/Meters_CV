#include "red_pointer_detector.h"
#include <math.h>
#include <string.h>

static float normalizeDegrees(float value) {
  while (value < 0.0f) value += 360.0f;
  while (value >= 360.0f) value -= 360.0f;
  return value;
}

RotaryDetection detectRedPointer(
    const uint8_t *rgb,
    uint16_t imageWidth,
    uint16_t imageHeight,
    const RotaryDialConfig &dial,
    bool angleCalibrationEnabled) {

  RotaryDetection result = {};
  result.detected = false;
  result.valueCalibrated = false;

  if (rgb == nullptr || imageWidth == 0 || imageHeight == 0 ||
      dial.radius <= 0.0f || dial.centerX < 0.0f || dial.centerX > 1.0f ||
      dial.centerY < 0.0f || dial.centerY > 1.0f) {
    return result;
  }

  const float cx = dial.centerX * (imageWidth - 1);
  const float cy = dial.centerY * (imageHeight - 1);
  const float radiusPx = dial.radius * min(imageWidth, imageHeight);
  if (radiusPx < 5.0f) return result;

  static uint16_t angleHistogram[RED_ANGLE_BINS];
  memset(angleHistogram, 0, sizeof(angleHistogram));

  uint16_t totalRed = 0;
  uint16_t maxBin = 0;
  uint16_t maxVotes = 0;

  const int xMin = max(0, (int)(cx - radiusPx));
  const int xMax = min((int)imageWidth - 1, (int)(cx + radiusPx));
  const int yMin = max(0, (int)(cy - radiusPx));
  const int yMax = min((int)imageHeight - 1, (int)(cy + radiusPx));

  // Search the middle/outer portion of the dial. This rejects much of the
  // central hub and edge lettering; final limits need physical calibration.
  for (int y = yMin; y <= yMax; ++y) {
    for (int x = xMin; x <= xMax; ++x) {
      const float dx = x - cx;
      const float dy = y - cy;
      const float distance = sqrtf(dx * dx + dy * dy);
      if (distance < radiusPx * 0.16f || distance > radiusPx * 0.92f) continue;

      const size_t index = ((size_t)y * imageWidth + x) * 3;
      const uint8_t r = rgb[index];
      const uint8_t g = rgb[index + 1];
      const uint8_t b = rgb[index + 2];

      // Broad red mask. Tune only after checking the real sensor color response.
      if (r < 115 || (uint16_t)r < (uint16_t)g * 1.35f ||
          (uint16_t)r < (uint16_t)b * 1.25f || g > 150) {
        continue;
      }

      ++totalRed;
      float angle = atan2f(-dy, dx) * 57.2957795f;
      angle = normalizeDegrees(angle);
      uint16_t bin = (uint16_t)(angle * (RED_ANGLE_BINS / 360.0f));
      if (bin >= RED_ANGLE_BINS) bin = RED_ANGLE_BINS - 1;
      ++angleHistogram[bin];
    }
  }

  result.redPixelCount = totalRed;
  if (totalRed < 5) return result;

  // Smooth each bin with its two neighbors to tolerate a thick pointer.
  uint16_t smoothed[RED_ANGLE_BINS];
  for (uint16_t i = 0; i < RED_ANGLE_BINS; ++i) {
    const uint16_t prev = (i + RED_ANGLE_BINS - 1) % RED_ANGLE_BINS;
    const uint16_t next = (i + 1) % RED_ANGLE_BINS;
    smoothed[i] = angleHistogram[prev] + angleHistogram[i] + angleHistogram[next];
    if (smoothed[i] > maxVotes) {
      maxVotes = smoothed[i];
      maxBin = i;
    }
  }

  if (maxVotes < 3) return result;

  result.detected = true;
  result.angleDeg = (maxBin + 0.5f) * (360.0f / RED_ANGLE_BINS);
  result.confidence = (float)maxVotes / (float)totalRed;
  if (result.confidence > 1.0f) result.confidence = 1.0f;

  if (angleCalibrationEnabled) {
    float relative = result.angleDeg - dial.zeroAngleDeg;
    if (dial.clockwise) relative = -relative;
    relative = normalizeDegrees(relative);
    result.dialDigit = relative / 36.0f; // 10 equal divisions per revolution.
    result.valueCalibrated = true;
  }

  return result;
}
