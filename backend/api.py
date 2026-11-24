from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.watermeter.live_service import service

app = FastAPI(title="RAGURA API", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class CalibrationPayload(BaseModel):
    roi: list[float] = Field(min_length=4, max_length=4)
    dials: list[dict] = Field(min_length=4, max_length=4)


class TriggerAllPayload(BaseModel):
    workers: int = Field(default=4, ge=1, le=8)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "RAGURA"}


@app.get("/api/overview")
def overview():
    return service.overview()


@app.get("/api/cameras/{channel_id}/frame")
def camera_frame(channel_id: str):
    data = service.frame_jpeg(channel_id)
    if data is None:
        raise HTTPException(status_code=503, detail="No frame available")
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})



@app.get("/api/cameras/{channel_id}/aligned-frame")
def aligned_camera_frame(channel_id: str):
    data = service.aligned_frame_jpeg(channel_id)
    if data is None:
        raise HTTPException(status_code=503, detail="No frame available")
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/cameras/{channel_id}/calibration")
def get_calibration(channel_id: str):
    try:
        return service.get_calibration(channel_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Camera channel not found")


@app.put("/api/cameras/{channel_id}/calibration")
def set_calibration(channel_id: str, payload: CalibrationPayload):
    try:
        return service.set_calibration(channel_id, payload.model_dump())
    except KeyError:
        raise HTTPException(status_code=404, detail="Camera channel not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))



@app.post("/api/cameras/{channel_id}/alignment/reference")
def save_alignment_reference(channel_id: str):
    try:
        return service.set_alignment_reference(channel_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Camera channel not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/cameras/{channel_id}/alignment")
def get_alignment_status(channel_id: str):
    try:
        return service.alignment_status(channel_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Camera channel not found")


@app.post("/api/cameras/{channel_id}/trigger")
def trigger(channel_id: str):
    try:
        return service.trigger(channel_id)
    except (KeyError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/trigger-all")
def trigger_all(payload: TriggerAllPayload):
    try:
        return service.trigger_all(payload.workers)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
