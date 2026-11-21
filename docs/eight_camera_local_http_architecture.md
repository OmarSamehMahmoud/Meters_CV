# Eight-camera local HTTP architecture

## What "direct HTTP" means

HTTP is the application protocol; it still needs a network link (TCP/IP). The standard AI Thinker ESP32-CAM has Wi-Fi but no built-in Ethernet port. The intended design is therefore **local HTTP over a private Wi-Fi link, with no internet, cloud, MQTT, or external router required**.

For one-camera bench testing, the ESP32-CAM can run in SoftAP mode and the PC can connect directly to its access point. The usual SoftAP address is `192.168.4.1`; verify the actual address printed by the firmware. This is a direct PC-to-camera link, but one PC Wi-Fi adapter normally connects to only one camera access point at a time.

For eight simultaneous cameras, use one private local access point. A convenient prototype is the Windows Mobile Hotspot on the PC, with internet sharing/WAN access not required. All eight ESP32-CAM boards join that same local network as stations. The PC talks to each camera directly by its local HTTP address. A small dedicated access point with its WAN port disconnected is another option.

If the requirement is **no Wi-Fi radio at all**, the standard ESP32-CAM board cannot provide that by itself; add compatible Ethernet hardware or use a different camera board with Ethernet.

## Example static address plan

The following is an example for a Windows hotspot whose PC-side gateway is `192.168.137.1`. Confirm the actual subnet with `ipconfig` before applying it. Choose addresses outside the DHCP allocation range and check that no other device uses them.

| Station | Example camera IP | MJPEG URL |
|---|---|---|
| CAM 01 | 192.168.137.181 | http://192.168.137.181:81/stream |
| CAM 02 | 192.168.137.182 | http://192.168.137.182:81/stream |
| CAM 03 | 192.168.137.183 | http://192.168.137.183:81/stream |
| CAM 04 | 192.168.137.184 | http://192.168.137.184:81/stream |
| CAM 05 | 192.168.137.185 | http://192.168.137.185:81/stream |
| CAM 06 | 192.168.137.186 | http://192.168.137.186:81/stream |
| CAM 07 | 192.168.137.187 | http://192.168.137.187:81/stream |
| CAM 08 | 192.168.137.188 | http://192.168.137.188:81/stream |

In the Arduino CameraWebServer station-mode sketch, configure a unique static address before calling `WiFi.begin`:

```cpp
IPAddress local_IP(192, 168, 137, 181); // change for each camera
IPAddress gateway(192, 168, 137, 1);    // confirm with ipconfig
IPAddress subnet(255, 255, 255, 0);

if (!WiFi.config(local_IP, gateway, subnet)) {
  Serial.println("Static IP configuration failed");
}
WiFi.begin(ssid, password);
```

Use a different `local_IP` for each ESP32-CAM. The example gateway and subnet are not universal; match the PC hotspot network. Keep the standard CameraWebServer stream endpoint, normally port 81 at `/stream`.

## Eight-channel software behavior

Configuration is stored in `configs/camera_channels.json`.

- Each channel has its own name, meter ID, stream URL, calibration ROI and four dial geometries.
- The capture layer maintains only the latest frame for each unique URL.
- Identical URLs are deliberately deduplicated into one HTTP stream reader. This prevents opening eight connections to one ESP32-CAM and overwhelming the board.
- In the current demo configuration, all eight logical channels point to `192.168.137.185`. All eight tiles therefore show the **same physical camera feed**. This tests the dashboard, independent calibration controls, individual triggers and Trigger All workflow; it does not simulate eight different camera viewpoints.
- When real cameras are installed, replace each channel's URL with its unique IP. The capture layer will then create one reader per unique camera URL.
- Trigger All snapshots the latest frame from each channel, then submits the eight independent analysis jobs to a bounded worker pool. The number of workers is adjustable in the sidebar.
- EasyOCR access is serialized with a lock for stability; image processing and pointer analysis can run in worker threads. On a CPU-only PC, increasing worker count does not guarantee faster OCR. Benchmark with the real camera resolution and lighting.

## Run

```powershell
git fetch origin
git switch feature/esp32cam-live-stream-demo
git pull origin feature/esp32cam-live-stream-demo
.venv\\Scripts\\Activate.ps1
pip install -r requirements-pc.txt
streamlit run live_app.py
```

Open the dashboard at `http://localhost:8501`.

## Test sequence

1. Start with the one working ESP32-CAM and confirm its stream URL opens from the PC.
2. Run the dashboard; the eight tiles should all show the same stream in demo mode.
3. Adjust the ROI/dial geometry independently in each channel's calibration panel.
4. Press a single channel's Trigger Read button.
5. Press Trigger All 8 and confirm eight separate result records are created.
6. Only after the UI workflow is stable, add cameras one at a time and assign unique static IPs.
7. Validate every station's frame sharpness, exposure, calibration, exact-read accuracy and recovery after camera power/network loss.

## Current limitations

The current OCR uses pretrained EasyOCR and the red-pointer logic is heuristic. The dial angle-to-value mapping and carry/rollover logic are not calibrated or validated. Results are experimental and must not be used for billing.
