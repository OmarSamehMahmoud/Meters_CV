# WaterMeterVision ESP32-CAM firmware

Two independent firmware targets are maintained:

- `WaterMeterVision_ESP32CAM/`: experimental standalone on-device capture/vision diagnostic.
- `WaterMeterVision_HTTP_Stream/`: **network camera firmware for the 8-camera PC dashboard**.

## 8-camera HTTP stream firmware

Open `WaterMeterVision_HTTP_Stream/WaterMeterVision_HTTP_Stream.ino` in Arduino IDE. It targets AI Thinker ESP32-CAM + OV2640 and connects as a station to the laptop's private Mobile Hotspot. It does not create eight separate Wi-Fi networks.

Before flashing each board:
- Set `WIFI_SSID` and `WIFI_PASSWORD` to the laptop hotspot credentials.
- Set a unique `CAMERA_INDEX` from 1 through 8.
- Confirm `LAN_GATEWAY` and `LAN_SUBNET` match the laptop hotspot adapter from `ipconfig`.
- Check the planned static IP is unused.

The example mapping is `192.168.137.201` through `192.168.137.208`, with gateway `192.168.137.1`. This is only an example; change it if the laptop hotspot uses another subnet.

Each board serves:
- Status page: `http://CAMERA_IP/`
- MJPEG stream: `http://CAMERA_IP:81/stream`

Select **AI Thinker ESP32-CAM**, enable PSRAM, upload using GPIO0-to-GND boot mode, then disconnect GPIO0 from GND and reset. Open Serial Monitor at 115200 baud to read the camera's assigned IP and stream URL.

The stream is VGA JPEG with an approximately 10 FPS ceiling. Test one camera first, then add the other seven. The full network setup and dashboard instructions are in [docs/eight_camera_local_http_architecture.md](../docs/eight_camera_local_http_architecture.md).

## Standalone vision firmware

The separate `WaterMeterVision_ESP32CAM/` sketch remains an experimental on-device diagnostic target. Its current capture and dial processing are not the HTTP streaming firmware and are not a validated meter reader. See the sketch folder's configuration and calibration notes before using it.
