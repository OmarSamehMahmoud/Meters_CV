/*
 * WaterMeterVision - AI Thinker ESP32-CAM
 * Standalone firmware foundation (no PC runtime, no web server).
 *
 * Phase 1: initialize OV2640, verify PSRAM, capture JPEG frames,
 * and report camera diagnostics through Serial Monitor.
 *
 * Meter recognition is intentionally not fabricated in this phase.
 * Digit and rotary-pointer algorithms will be added after validating
 * the camera image geometry on the physical meter.
 */

#include "esp_camera.h"
#include "img_converters.h"
#include <Arduino.h>
#include <esp_arduino_version.h>
#include <esp_heap_caps.h>
#include "config/meter_config.h"
#include "vision/red_pointer_detector.h"
#include "meter/reading_engine.h"

// AI Thinker ESP32-CAM + OV2640 pin mapping
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

static const uint32_t SERIAL_BAUD_RATE = 115200;
static const uint32_t CAPTURE_INTERVAL_MS = 5000;
static uint8_t *g_rgbBuffer = nullptr;
static constexpr uint16_t FRAME_WIDTH = 320;
static constexpr uint16_t FRAME_HEIGHT = 240;

static bool initializeCamera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
#else
  // ESP32 Arduino core 2.x uses the historical "sscb" spelling.
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
#endif
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
#endif

  const esp_err_t result = esp_camera_init(&config);
  if (result != ESP_OK) {
    Serial.printf("[CAMERA] Initialization failed: 0x%04X\n", result);
    return false;
  }

  sensor_t *sensor = esp_camera_sensor_get();
  if (sensor != nullptr) {
    sensor->set_framesize(sensor, FRAMESIZE_QVGA);
    sensor->set_brightness(sensor, 0);
    sensor->set_contrast(sensor, 1);
    sensor->set_saturation(sensor, -1);
  }

  return true;
}

static void processMeterFrame(const uint8_t *rgb, uint16_t width, uint16_t height) {
  MeterReadingResult result = {};
  result.integerDigitsAvailable = false;
  result.complete = false;

  if (!METER_GEOMETRY_CALIBRATED) {
    Serial.println("[CALIBRATION] Meter geometry is not configured.");
    Serial.println("[CALIBRATION] Capture and inspect a frame from the final fixed camera mount.");
    printMeterReading(result);
    return;
  }

  for (uint8_t i = 0; i < ROTARY_DIAL_COUNT; ++i) {
    result.dials[i] = detectRedPointer(
        rgb, width, height, ROTARY_DIALS[i], ROTARY_ANGLE_CALIBRATED);
  }

  // No integer-digit model is bundled yet. Never synthesize the five digits.
  printMeterReading(result);
}

static void captureDiagnosticFrame() {
  camera_fb_t *frame = esp_camera_fb_get();

  if (frame == nullptr) {
    Serial.println("[CAMERA] Capture failed: frame buffer is null");
    return;
  }

  Serial.println("\\n========== CAMERA FRAME ==========");
  Serial.printf("Width       : %u px\\n", frame->width);
  Serial.printf("Height      : %u px\\n", frame->height);
  Serial.printf("Format      : %s\\n",
                frame->format == PIXFORMAT_JPEG ? "JPEG" : "OTHER");
  Serial.printf("Image bytes : %u\\n", static_cast<unsigned int>(frame->len));
  Serial.printf("PSRAM       : %s\\n", psramFound() ? "AVAILABLE" : "NOT FOUND");

  if (g_rgbBuffer == nullptr) {
    Serial.println("[VISION] RGB buffer unavailable.");
  } else if (!fmt2rgb888(frame->buf, frame->len, frame->format, g_rgbBuffer)) {
    Serial.println("[VISION] JPEG-to-RGB conversion failed.");
  } else {
    processMeterFrame(g_rgbBuffer, frame->width, frame->height);
  }

  Serial.println("==================================");
  esp_camera_fb_return(frame);
}

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  delay(1000);

  Serial.println();
  Serial.println("========================================");
  Serial.println(" WaterMeterVision - ESP32-CAM");
  Serial.println(" Standalone firmware / Serial output");
  Serial.println("========================================");

  Serial.printf("[MEMORY] Free heap: %u bytes\n",
                static_cast<unsigned int>(ESP.getFreeHeap()));
  Serial.printf("[MEMORY] PSRAM: %s\n", psramFound() ? "AVAILABLE" : "NOT FOUND");
  if (psramFound()) {
    Serial.printf("[MEMORY] PSRAM size: %u bytes\n",
                  static_cast<unsigned int>(ESP.getPsramSize()));
  }

  if (!initializeCamera()) {
    Serial.println("[FATAL] Camera setup failed. Check board selection, camera cable and power.");
    while (true) {
      delay(1000);
    }
  }

  Serial.println("[CAMERA] OV2640 initialized successfully.");

  const size_t rgbBytes = (size_t)FRAME_WIDTH * FRAME_HEIGHT * 3;
  g_rgbBuffer = (uint8_t *)heap_caps_malloc(rgbBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (g_rgbBuffer == nullptr) {
    g_rgbBuffer = (uint8_t *)heap_caps_malloc(rgbBytes, MALLOC_CAP_8BIT);
  }
  Serial.printf("[VISION] RGB buffer: %s (%u bytes)\\n",
                g_rgbBuffer ? "READY" : "ALLOCATION FAILED",
                static_cast<unsigned int>(rgbBytes));

  Serial.println("[SYSTEM] Local processing every 5 seconds; output via Serial only.");
  Serial.printf("[CONFIG] Geometry calibrated: %s\\n", METER_GEOMETRY_CALIBRATED ? "YES" : "NO");
  Serial.printf("[CONFIG] Rotary angle calibrated: %s\\n", ROTARY_ANGLE_CALIBRATED ? "YES" : "NO");
}

void loop() {
  captureDiagnosticFrame();
  delay(CAPTURE_INTERVAL_MS);
}
