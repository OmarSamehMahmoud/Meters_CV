# Eight-camera offline LAN architecture

## Final topology

Use the Windows laptop's **Mobile Hotspot** as one private Wi-Fi access point. Internet access is not required. All eight ESP32-CAM boards join this same hotspot in station mode; the laptop remains connected as the hotspot host and can reach every camera over the local subnet.

- No internet, cloud, MQTT or external router is required.
- One Wi-Fi network is shared by all cameras.
- Each ESP32-CAM has a unique static IPv4 address.
- Each camera serves a status page on port 80 and MJPEG on port 81 at `/stream`.
- The React dashboard talks to the local FastAPI process; FastAPI maintains one HTTP reader per camera URL and relays latest frames to the dashboard.
- Open each raw stream directly in a browser if needed; the dashboard also displays all eight simultaneously.

## Laptop hotspot setup (Windows)

1. Open **Settings → Network & internet → Mobile hotspot**.
2. Set a network name, for example `MeterVision-Offline`, and a password of at least 8 characters.
3. Turn Mobile Hotspot on. The laptop does not need internet access.
4. Open PowerShell and run `ipconfig`. Find the **Microsoft Wi-Fi Direct Virtual Adapter** / hotspot adapter IPv4 address and subnet mask.
5. The example firmware below assumes gateway `192.168.137.1` and subnet `255.255.255.0`. If your laptop shows a different gateway/subnet, change `LAN_GATEWAY`, `LAN_SUBNET`, and all eight URLs in `configs/camera_channels.json` to match.

### Static IP collision warning

Windows Mobile Hotspot does not provide a convenient DHCP reservation UI. Before using the example addresses, check that `192.168.137.201` through `.208` are unused and not currently leased to another device. If any address responds to ping or is already in use, choose another unused block in the same subnet and update both the firmware and JSON configuration. Never give two cameras the same IP.

## Flashing the eight cameras

Use the dedicated sketch:

`esp32_cam/WaterMeterVision_HTTP_Stream/WaterMeterVision_HTTP_Stream.ino`

For each physical ESP32-CAM:

1. Set `WIFI_SSID` and `WIFI_PASSWORD` to the Windows hotspot credentials.
2. Set `CAMERA_INDEX` to a unique number from 1 to 8.
3. Confirm `LAN_GATEWAY` and `LAN_SUBNET` match `ipconfig`.
4. Select **AI Thinker ESP32-CAM**, enable PSRAM, and upload.
5. Open Serial Monitor at 115200 baud. It prints the assigned IP and stream URL.
6. Repeat with the next `CAMERA_INDEX`.

| Camera | CAMERA_INDEX | Static IP | Direct MJPEG URL |
|---|---:|---|---|
| CAM 01 | 1 | 192.168.137.201 | http://192.168.137.201:81/stream |
| CAM 02 | 2 | 192.168.137.202 | http://192.168.137.202:81/stream |
| CAM 03 | 3 | 192.168.137.203 | http://192.168.137.203:81/stream |
| CAM 04 | 4 | 192.168.137.204 | http://192.168.137.204:81/stream |
| CAM 05 | 5 | 192.168.137.205 | http://192.168.137.205:81/stream |
| CAM 06 | 6 | 192.168.137.206 | http://192.168.137.206:81/stream |
| CAM 07 | 7 | 192.168.137.207 | http://192.168.137.207:81/stream |
| CAM 08 | 8 | 192.168.137.208 | http://192.168.137.208:81/stream |

The sketch provides a device information page at `http://CAMERA_IP/` and a multipart MJPEG stream at `http://CAMERA_IP:81/stream`. It uses VGA JPEG and limits the stream loop to approximately 10 FPS to moderate the load. Actual throughput depends on the laptop Wi-Fi adapter, radio conditions, camera power and browser/PC load.

## Dashboard configuration

The eight URLs are stored in `configs/camera_channels.json`. The React dashboard reads this configuration through the FastAPI service at backend startup. If you change URLs or IP addresses, restart the backend.

The API capture layer opens one reader for each unique stream URL. It does not duplicate connections to the same URL. In the eight-camera configuration, each tile therefore has an independent physical stream, status, latest frame and trigger result.

## Run the dashboard

Backend terminal, from repository root:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements-pc.txt
uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Bring-up sequence

1. Start the laptop hotspot and verify its gateway/subnet with `ipconfig`.
2. Flash only CAM 01 first; check the printed URL and open it from the laptop.
3. Verify the direct stream at `http://192.168.137.201:81/stream` (adjust for the actual subnet).
4. Add cameras one at a time, confirming a unique IP and direct stream for each.
5. Start/restart the FastAPI backend after editing `configs/camera_channels.json`.
6. Confirm all eight tiles show independent live feeds before testing Trigger All.

## Current limitations

- A single laptop Wi-Fi radio can host the hotspot and communicate with multiple station clients, but eight simultaneous VGA MJPEG streams are a meaningful 2.4 GHz load. Start at VGA/approximately 10 FPS; if frames drop, lower the frame rate or JPEG resolution/quality and test the actual installation.
- The example static addresses must be checked for DHCP collisions. A dedicated access point with DHCP reservations is the more robust production option, still fully offline.
- OCR and rotary-dial estimates remain experimental and are not approved for billing.
