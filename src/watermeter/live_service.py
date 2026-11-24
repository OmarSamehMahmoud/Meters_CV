from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np

from src.watermeter.camera_stream import LatestFrameCamera
from src.watermeter.ai_edge_pc import analyze_ai_edge

ROOT = Path(__file__).resolve().parents[2]
CHANNELS = json.loads((ROOT / "configs" / "camera_channels.json").read_text(encoding="utf-8"))["cameras"]
PRESETS = json.loads((ROOT / "configs" / "reference_presets.json").read_text(encoding="utf-8"))["reference_presets"]
CALIBRATION_PATH = ROOT / "data" / "meter_calibrations.json"
ALIGNMENT_DIR = ROOT / "data" / "alignment_references"
ORB_FEATURES = 1800
HISTORY_DB = ROOT / "data" / "ragura_readings.sqlite3"
def channel_geometry(channel):
    preset = channel.get("preset", next(iter(PRESETS)))
    cfg = PRESETS[preset]
    return list(cfg["integer_register_roi"]), [dict(d) for d in cfg["dials"]]


def align_to_reference(frame, reference):
    """Align a live frame to its saved reference using ORB features and RANSAC."""
    if frame is None or reference is None:
        return frame, {"status": "not_configured", "matches": 0, "inliers": 0,
                       "inlier_ratio": 0.0, "message": "No reference frame configured."}
    ref_h, ref_w = reference.shape[:2]
    gray_ref = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    gray_live = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=ORB_FEATURES, scaleFactor=1.2, nlevels=8,
                         edgeThreshold=19, fastThreshold=12)
    kp_ref, des_ref = orb.detectAndCompute(gray_ref, None)
    kp_live, des_live = orb.detectAndCompute(gray_live, None)
    if des_ref is None or des_live is None or len(kp_ref) < 8 or len(kp_live) < 8:
        return frame, {"status": "failed", "matches": 0, "inliers": 0,
                       "inlier_ratio": 0.0, "message": "Not enough visual features; improve focus or lighting."}
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(des_live, des_ref, k=2)
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance]
    if len(good) < 12:
        return frame, {"status": "failed", "matches": len(good), "inliers": 0,
                       "inlier_ratio": 0.0, "message": "Too few reliable feature matches."}
    src = np.float32([kp_live[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    matrix, mask = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
        ransacReprojThreshold=4.0, maxIters=2500, confidence=0.99, refineIters=10)
    inliers = int(mask.sum()) if mask is not None else 0
    ratio = inliers / max(1, len(good))
    if matrix is None or inliers < 8 or ratio < 0.25:
        return frame, {"status": "failed", "matches": len(good), "inliers": inliers,
                       "inlier_ratio": round(ratio, 3),
                       "message": "Reference alignment is unstable; check camera position and reference image."}
    aligned = cv2.warpAffine(frame, matrix, (ref_w, ref_h), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    scale = float(math.sqrt(matrix[0, 0] ** 2 + matrix[1, 0] ** 2))
    rotation = float(math.degrees(math.atan2(matrix[1, 0], matrix[0, 0])))
    return aligned, {"status": "aligned", "matches": len(good), "inliers": inliers,
                     "inlier_ratio": round(ratio, 3), "scale": round(scale, 4),
                     "rotation_degrees": round(rotation, 2),
                     "message": "Live frame aligned to the saved reference."}


def analyze(frame, roi, dials, channel_id, alignment=None):
    # RAGURA now uses the upstream pretrained TFLite models only.
    # It deliberately does not silently fall back to EasyOCR or color heuristics.
    return analyze_ai_edge(frame, roi, dials, channel_id, alignment, expected_digits=5)


class LiveMeterService:
    def __init__(self):
        self.channels = [dict(c) for c in CHANNELS]
        self.cameras = {}
        self.calibrations = {}
        self.results = {}
        self.alignment_references = {}
        self.lock = threading.RLock()
        self._init_history_db()
        for ch in self.channels:
            url = ch["stream_url"].strip()
            if url and url not in self.cameras:
                self.cameras[url] = LatestFrameCamera(url)
            self.calibrations[ch["id"]] = channel_geometry(ch)
        ALIGNMENT_DIR.mkdir(parents=True, exist_ok=True)
        for ch in self.channels:
            ref_path = ALIGNMENT_DIR / (ch["id"] + ".jpg")
            if ref_path.exists():
                reference = cv2.imread(str(ref_path))
                if reference is not None:
                    self.alignment_references[ch["id"]] = reference
        if CALIBRATION_PATH.exists():
            try:
                saved = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
                for channel_id, cfg in saved.items():
                    if channel_id in self.calibrations and isinstance(cfg, dict):
                        roi, dials = cfg.get("roi"), cfg.get("dials")
                        if isinstance(roi, list) and len(roi) == 4 and isinstance(dials, list) and len(dials) == 4:
                            self.calibrations[channel_id] = ([float(v) for v in roi], dials)
            except (OSError, ValueError, TypeError):
                pass


    def _connect_history(self):
        HISTORY_DB.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(HISTORY_DB), timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_history_db(self):
        with self._connect_history() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                reading_m3 REAL NOT NULL,
                captured_at TEXT NOT NULL,
                status TEXT NOT NULL,
                validation_json TEXT NOT NULL,
                reviewed_at TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_readings_channel_status ON readings(channel_id, status, id)")

    def _record_candidate(self, channel_id, reading, captured_at):
        with self._connect_history() as db:
            previous = db.execute(
                "SELECT reading_m3, captured_at FROM readings WHERE channel_id=? AND status='accepted' ORDER BY id DESC LIMIT 1",
                (channel_id,)).fetchone()
            checks = []
            if previous is None:
                checks.append({"code": "baseline_missing", "passed": False,
                               "message": "No accepted baseline exists; verify the first reading manually."})
            elif float(reading) < float(previous["reading_m3"]):
                checks.append({"code": "counter_decreased", "passed": False,
                               "message": "Candidate is lower than the last accepted reading."})
            else:
                checks.append({"code": "monotonic_counter", "passed": True,
                               "message": "Candidate is not lower than the last accepted reading."})
            validation = {"status": "needs_review" if not all(x["passed"] for x in checks) else "pending_review",
                          "checks": checks,
                          "previous_accepted_m3": float(previous["reading_m3"]) if previous else None,
                          "automatic_acceptance": False}
            cursor = db.execute(
                "INSERT INTO readings(channel_id,reading_m3,captured_at,status,validation_json) VALUES(?,?,?,?,?)",
                (channel_id, float(reading), captured_at, validation["status"], json.dumps(validation)))
            return {"record_id": cursor.lastrowid, **validation}

    def accept_reading(self, channel_id, record_id):
        with self._connect_history() as db:
            row = db.execute("SELECT * FROM readings WHERE id=? AND channel_id=?",
                             (int(record_id), channel_id)).fetchone()
            if row is None:
                raise KeyError(record_id)
            if row["status"] == "accepted":
                return {"record_id": int(record_id), "status": "accepted", "already_accepted": True}
            previous = db.execute(
                "SELECT reading_m3 FROM readings WHERE channel_id=? AND status='accepted' ORDER BY id DESC LIMIT 1",
                (channel_id,)).fetchone()
            if previous and float(row["reading_m3"]) < float(previous["reading_m3"]):
                raise ValueError("Cannot accept a lower counter value without an explicit meter-reset workflow.")
            db.execute("UPDATE readings SET status='accepted', reviewed_at=? WHERE id=?",
                       (time.strftime("%Y-%m-%d %H:%M:%S"), int(record_id)))
            return {"record_id": int(record_id), "status": "accepted",
                    "reading_m3": float(row["reading_m3"])}

    def reading_history(self, channel_id, limit=50):
        if channel_id not in self.calibrations:
            raise KeyError(channel_id)
        with self._connect_history() as db:
            rows = db.execute(
                "SELECT id,reading_m3,captured_at,status,validation_json,reviewed_at FROM readings WHERE channel_id=? ORDER BY id DESC LIMIT ?",
                (channel_id, max(1, min(int(limit), 200)))).fetchall()
        return {"channel_id": channel_id, "readings": [
            {"record_id": int(row["id"]), "reading_m3": float(row["reading_m3"]),
             "captured_at": row["captured_at"], "status": row["status"],
             "validation": json.loads(row["validation_json"]),
             "reviewed_at": row["reviewed_at"]} for row in rows]}

    def _persist_calibrations(self):
        CALIBRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            snapshot = {channel_id: {"roi": list(roi), "dials": dials}
                        for channel_id, (roi, dials) in self.calibrations.items()}
        temporary = CALIBRATION_PATH.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        temporary.replace(CALIBRATION_PATH)


    def set_alignment_reference(self, channel_id):
        if channel_id not in self.calibrations:
            raise KeyError(channel_id)
        cam = self.camera_for(channel_id)
        frame = cam.latest() if cam else None
        if frame is None:
            raise RuntimeError("No camera frame available to save as reference.")
        ALIGNMENT_DIR.mkdir(parents=True, exist_ok=True)
        path = ALIGNMENT_DIR / (channel_id + ".jpg")
        ok = cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 94])
        if not ok:
            raise RuntimeError("Could not write the alignment reference image.")
        reference = cv2.imread(str(path))
        with self.lock:
            self.alignment_references[channel_id] = reference
        return {"channel_id": channel_id, "status": "reference_saved",
                "reference_size": [int(reference.shape[1]), int(reference.shape[0])],
                "message": "Reference frame saved locally."}

    def alignment_status(self, channel_id):
        if channel_id not in self.calibrations:
            raise KeyError(channel_id)
        with self.lock:
            reference = self.alignment_references.get(channel_id)
            has_reference = reference is not None
            size = [int(reference.shape[1]), int(reference.shape[0])] if has_reference else None
        return {"channel_id": channel_id, "configured": has_reference,
                "reference_size": size,
                "status": "reference_ready" if has_reference else "not_configured"}

    def camera_for(self, channel_id):
        ch = next((c for c in self.channels if c["id"] == channel_id), None)
        return self.cameras.get(ch["stream_url"]) if ch else None

    def overview(self):
        items = []
        for ch in self.channels:
            cam = self.camera_for(ch["id"])
            frame = cam.latest() if cam else None
            with self.lock:
                result = self.results.get(ch["id"])
            items.append({
                **ch,
                "online": bool(cam and cam.connected and frame is not None),
                "last_error": cam.last_error if cam else "No stream URL",
                "has_frame": frame is not None,
                "result": result,
            })
        return {"channels": items, "online_channels": sum(x["online"] for x in items),
                "total_channels": len(items), "unique_streams": len(self.cameras),
                "mode": "demo_shared_stream" if len(self.cameras) < len(self.channels) else "multi_camera"}

    def frame_jpeg(self, channel_id):
        cam = self.camera_for(channel_id)
        frame = cam.latest() if cam else None
        if frame is None:
            return None
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
        return encoded.tobytes() if ok else None


    def aligned_frame_jpeg(self, channel_id):
        cam = self.camera_for(channel_id)
        frame = cam.latest() if cam else None
        if frame is None:
            return None
        with self.lock:
            reference = self.alignment_references.get(channel_id)
        if reference is not None:
            aligned, status = align_to_reference(frame, reference)
            if status["status"] == "aligned":
                frame = aligned
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
        return encoded.tobytes() if ok else None

    def get_calibration(self, channel_id):
        if channel_id not in self.calibrations:
            raise KeyError(channel_id)
        with self.lock:
            roi, dials = self.calibrations[channel_id]
            return {"channel_id": channel_id, "roi": list(roi), "dials": [dict(d) for d in dials]}

    def set_calibration(self, channel_id, payload):
        if channel_id not in self.calibrations:
            raise KeyError(channel_id)
        roi = payload.get("roi")
        dials = payload.get("dials")
        if not isinstance(roi, list) or len(roi) != 4 or not isinstance(dials, list) or len(dials) != 4:
            raise ValueError("Calibration requires a 4-value ROI and 4 dials.")
        if not all(0 <= float(v) <= 1 for v in roi):
            raise ValueError("ROI coordinates must be normalized between 0 and 1.")
        with self.lock:
            self.calibrations[channel_id] = ([float(v) for v in roi], dials)
        try:
            self._persist_calibrations()
        except OSError as exc:
            raise ValueError(f"Could not persist calibration: {exc}") from exc
        return {"channel_id": channel_id, "roi": roi, "dials": dials}

    def trigger(self, channel_id):
        cam = self.camera_for(channel_id)
        frame = cam.latest() if cam else None
        if frame is None:
            raise RuntimeError("No frame received from this camera.")
        with self.lock:
            roi, dials = self.calibrations[channel_id]
            reference = self.alignment_references.get(channel_id)
        alignment = {"status": "not_configured", "matches": 0, "inliers": 0,
                     "inlier_ratio": 0.0, "message": "Save a reference frame to enable automatic alignment."}
        aligned = frame.copy()
        if reference is not None:
            aligned, alignment = align_to_reference(frame.copy(), reference)
        result, annotated = analyze(aligned, roi, dials, channel_id, alignment)
        if alignment["status"] == "failed":
            result["status"] = "alignment_failed"
            result["candidate_reading_m3"] = None
            result["warning"] = "Reading suppressed because image alignment failed. " + alignment["message"]
        if result.get("candidate_reading_m3") is not None and alignment["status"] != "failed":
            result["validation"] = self._record_candidate(
                channel_id, result["candidate_reading_m3"], result["captured_at"])
            result["status"] = result["validation"]["status"]
        with self.lock:
            self.results[channel_id] = result
        return result

    def trigger_all(self, workers=4):
        jobs = []
        for ch in self.channels:
            cam = self.camera_for(ch["id"])
            frame = cam.latest() if cam else None
            if frame is not None:
                with self.lock:
                    roi, dials = self.calibrations[ch["id"]]
                    reference = self.alignment_references.get(ch["id"])
                jobs.append((ch["id"], frame.copy(), roi, dials, reference))
        if not jobs:
            raise RuntimeError("No camera frames are available.")
        outcomes = []
        with ThreadPoolExecutor(max_workers=max(1, min(int(workers), 8))) as pool:
            def run_job(cid, frame, roi, dials, reference):
                alignment = {"status": "not_configured", "matches": 0, "inliers": 0,
                             "inlier_ratio": 0.0, "message": "No reference configured."}
                aligned = frame
                if reference is not None:
                    aligned, alignment = align_to_reference(frame, reference)
                result, annotated = analyze(aligned, roi, dials, cid, alignment)
                if alignment["status"] == "failed":
                    result["status"] = "alignment_failed"
                    result["candidate_reading_m3"] = None
                    result["warning"] = "Reading suppressed because image alignment failed. " + alignment["message"]
                elif result.get("candidate_reading_m3") is not None:
                    result["validation"] = self._record_candidate(
                        cid, result["candidate_reading_m3"], result["captured_at"])
                    result["status"] = result["validation"]["status"]
                return result, annotated
            futures = {pool.submit(run_job, cid, f, r, d, ref): cid for cid, f, r, d, ref in jobs}
            for future in as_completed(futures):
                cid = futures[future]
                try:
                    result, annotated = future.result()
                    with self.lock:
                        self.results[cid] = result
                    outcomes.append({"channel_id": cid, "ok": True, "result": result})
                except Exception as exc:
                    outcomes.append({"channel_id": cid, "ok": False, "error": str(exc)})
        return {"processed": len(outcomes), "outcomes": outcomes}


service = LiveMeterService()
