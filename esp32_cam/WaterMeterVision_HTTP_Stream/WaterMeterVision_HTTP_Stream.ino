/*
 * WaterMeterVision - ESP32-CAM HTTP Stream (8-camera LAN)
 * Target: AI Thinker ESP32-CAM + OV2640
 *
 * Each board joins ONE private laptop hotspot (no internet required),
 * receives a unique static IP, and serves:
 *   http://CAMERA_IP/         device status page
 *   http://CAMERA_IP:81/stream  MJPEG stream for the PC dashboard
 *
 * Set CAMERA_INDEX to a unique value from 1 to 8 on each board.
 * Configure WIFI_SSID / WIFI_PASSWORD and LAN_GATEWAY to match the laptop.
 */

#include "esp_camera.h"
#include <Arduino.h>
#include <WiFi.h>
#include "esp_http_server.h"

// -------------------- PER-BOARD CONFIGURATION --------------------
#define CAMERA_INDEX 1  // Set uniquely: 1..8

static const char *WIFI_SSID = "MeterVision-Offline";
static const char *WIFI_PASSWORD = "ChangeThis123"; // At least 8 characters

// Windows Mobile Hotspot commonly uses 192.168.137.1.
// Confirm with ipconfig before flashing all cameras.
static const IPAddress LAN_GATEWAY(192, 168, 137, 1);
static const IPAddress LAN_SUBNET(255, 255, 255, 0);
static const uint8_t CAMERA_IP_LAST_OCTET = 200 + CAMERA_INDEX;
static const IPAddress CAMERA_IP(192, 168, 137, CAMERA_IP_LAST_OCTET);
// -----------------------------------------------------------------

#if CAMERA_INDEX < 1 || CAMERA_INDEX > 8
#error "CAMERA_INDEX must be between 1 and 8"
#endif

// AI Thinker ESP32-CAM + OV2640 pin map
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

static httpd_handle_t statusServer = nullptr;
static httpd_handle_t streamServer = nullptr;

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
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
#endif
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 14;
  config.fb_count = psramFound() ? 2 : 1;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;
#endif

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[CAMERA] Init failed: 0x%X\n", err);
    return false;
  }
  sensor_t *sensor = esp_camera_sensor_get();
  if (sensor) {
    sensor->set_framesize(sensor, FRAMESIZE_VGA);
    sensor->set_quality(sensor, 14);
  }
  return true;
}

static esp_err_t statusHandler(httpd_req_t *req) {
  const String ip = WiFi.localIP().toString();
  String page = "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>";
  page += "<title>WaterMeterVision Camera</title></head><body style='font:16px Arial;background:#101820;color:#eef;padding:28px'>";
  page += "<h2>WaterMeterVision · Camera ";
  page += String(CAMERA_INDEX);
  page += "</h2><p>Status: ONLINE</p><p>Static IP: " + ip + "</p><p>MJPEG stream: ";
  page += "<a style='color:#55dfb0' href='http://" + ip + ":81/stream'>http://" + ip + ":81/stream</a></p>";
  page += "<p>Local-only camera endpoint. No cloud or internet required.</p></body></html>";
  httpd_resp_set_type(req, "text/html");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  return httpd_resp_send(req, page.c_str(), page.length());
}

static esp_err_t streamHandler(httpd_req_t *req) {
  static const char *BOUNDARY = "\r\n--frame\r\n";
  static const char *PART_HEADER = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";
  esp_err_t result = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
  if (result != ESP_OK) return result;
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store, no-cache, must-revalidate");

  while (true) {
    camera_fb_t *frame = esp_camera_fb_get();
    if (!frame) {
      Serial.println("[STREAM] Frame capture failed");
      return ESP_FAIL;
    }

    char header[80];
    const size_t headerLen = snprintf(header, sizeof(header), PART_HEADER, frame->len);
    result = httpd_resp_send_chunk(req, BOUNDARY, strlen(BOUNDARY));
    if (result == ESP_OK) result = httpd_resp_send_chunk(req, header, headerLen);
    if (result == ESP_OK) result = httpd_resp_send_chunk(req, (const char *)frame->buf, frame->len);
    esp_camera_fb_return(frame);

    if (result != ESP_OK) break;
    delay(100); // Approx. 10 FPS ceiling; keeps Wi-Fi load manageable.
  }
  return result;
}

static void startHttpServers() {
  httpd_config_t statusConfig = HTTPD_DEFAULT_CONFIG();
  statusConfig.server_port = 80;
  statusConfig.ctrl_port = 32768;
  httpd_uri_t statusUri = {};
  statusUri.uri = "/";
  statusUri.method = HTTP_GET;
  statusUri.handler = statusHandler;
  if (httpd_start(&statusServer, &statusConfig) == ESP_OK) {
    httpd_register_uri_handler(statusServer, &statusUri);
  }

  httpd_config_t streamConfig = HTTPD_DEFAULT_CONFIG();
  streamConfig.server_port = 81;
  streamConfig.ctrl_port = 32769;
  streamConfig.max_uri_handlers = 4;
  streamConfig.stack_size = 8192;
  httpd_uri_t streamUri = {};
  streamUri.uri = "/stream";
  streamUri.method = HTTP_GET;
  streamUri.handler = streamHandler;
  if (httpd_start(&streamServer, &streamConfig) == ESP_OK) {
    httpd_register_uri_handler(streamServer, &streamUri);
  }
}

static void connectToLaptopHotspot() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  if (!WiFi.config(CAMERA_IP, LAN_GATEWAY, LAN_SUBNET, LAN_GATEWAY, LAN_GATEWAY)) {
    Serial.println("[NETWORK] Static IP configuration failed");
  }

  Serial.printf("[NETWORK] Joining SSID: %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.printf("[NETWORK] Connected. Camera %u IP: %s\n", CAMERA_INDEX,
                WiFi.localIP().toString().c_str());
  Serial.printf("[NETWORK] Status page: http://%s/\n", WiFi.localIP().toString().c_str());
  Serial.printf("[NETWORK] Stream URL : http://%s:81/stream\n", WiFi.localIP().toString().c_str());
}

void setup() {
  Serial.begin(115200);
  delay(800);
  Serial.println();
  Serial.println("=== WaterMeterVision HTTP Camera ===");
  Serial.printf("[CONFIG] CAMERA_INDEX=%u\n", CAMERA_INDEX);
  Serial.printf("[CONFIG] Static IP=%s\n", CAMERA_IP.toString().c_str());

  if (!initializeCamera()) {
    Serial.println("[FATAL] Camera initialization failed. Check AI Thinker board, ribbon and power.");
    while (true) delay(1000);
  }

  connectToLaptopHotspot();
  startHttpServers();
  Serial.println("[SYSTEM] HTTP camera stream is ready.");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[NETWORK] Wi-Fi disconnected; reconnecting...");
    WiFi.reconnect();
    delay(1500);
  } else {
    delay(1000);
  }
}
