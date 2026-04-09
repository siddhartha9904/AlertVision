"""
AlertVision — FastAPI Web Server
Serves the dashboard and provides WebSocket for real-time video analysis.
"""

import asyncio
import base64
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from video_capture import VideoCapture
from analyzer import AggressionAnalyzer
from state_machine import StateMachine
from visualizer import Visualizer
from alert_logger import AlertLogger
import config

app = FastAPI(title="AlertVision", version="1.0.0")

# Serve static frontend files
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Global state
analyzer = AggressionAnalyzer()
visualizer = Visualizer()
alert_logger = AlertLogger()
active_sessions = {}
incident_history = []


@app.get("/")
async def root():
    """Serve the main dashboard page."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/stats")
async def get_stats():
    """Get current detection statistics."""
    total = len(incident_history)
    critical = sum(1 for i in incident_history if i.get("status") == "aggressive")
    warnings = sum(1 for i in incident_history if i.get("status") == "suspicious")
    safe = sum(1 for i in incident_history if i.get("status") == "normal")
    return {
        "total_incidents": total,
        "critical_alerts": critical,
        "warnings": warnings,
        "safe_events": safe,
    }


@app.get("/api/incidents")
async def get_incidents():
    """Get incident history."""
    return incident_history[-50:]  # Last 50


@app.get("/api/analytics")
async def get_analytics():
    """Get hourly activity data for charts."""
    hourly = {}
    for i in incident_history:
        hour = i.get("hour", "00:00")
        hourly[hour] = hourly.get(hour, 0) + 1

    dist = {"aggressive": 0, "suspicious": 0, "normal": 0}
    for i in incident_history:
        s = i.get("status", "normal")
        dist[s] = dist.get(s, 0) + 1

    return {"hourly": hourly, "distribution": dist}


@app.get("/api/system")
async def get_system_info():
    """Get system information."""
    return {
        "version": "1.0.0",
        "ai_model": config.GEMINI_MODEL,
        "api_status": "Connected",
        "active_cameras": len(active_sessions),
    }


def draw_annotations(frame, result):
    """Draw bounding boxes and labels on a frame using the Visualizer.

    Returns the annotated frame.
    """
    fsm = StateMachine()
    state = fsm.update(result)
    annotated = visualizer.draw(frame.copy(), result, state)
    return annotated


def frame_to_base64(frame):
    """Encode an OpenCV frame to base64 JPEG string."""
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buffer).decode('utf-8')


@app.websocket("/ws/feed/{camera_id}")
async def websocket_feed(websocket: WebSocket, camera_id: str):
    """WebSocket endpoint for live video feed analysis.

    Client sends base64-encoded frames, server analyzes and returns results.
    """
    await websocket.accept()
    fsm = StateMachine()
    active_sessions[camera_id] = True
    print(f"[WebSocket] Camera {camera_id} connected")

    try:
        while True:
            # Receive frame from client
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "frame":
                # Decode base64 frame
                img_data = base64.b64decode(msg["data"])
                np_arr = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if frame is None:
                    continue

                # Analyze with Gemini
                result = analyzer.analyze_frame(frame)
                state = fsm.update(result)

                # Log if alert triggered
                if fsm.should_alert():
                    alert_logger.log_alert(frame, result)

                # Draw bounding boxes on the frame
                annotated = visualizer.draw(frame.copy(), result, state)
                annotated_b64 = frame_to_base64(annotated)

                # Record incident
                now = datetime.now()
                incident = {
                    "id": len(incident_history) + 1,
                    "camera": camera_id,
                    "status": result.get("status", "normal"),
                    "confidence": result.get("confidence", 0.0),
                    "description": result.get("description", ""),
                    "timestamp": now.isoformat(),
                    "time": now.strftime("%H:%M"),
                    "hour": now.strftime("%H:00"),
                    "state": state,
                    "regions": result.get("regions", []),
                }
                incident_history.append(incident)

                # Send result back to client
                await websocket.send_text(json.dumps({
                    "type": "analysis",
                    "result": result,
                    "state": state,
                    "incident": incident,
                    "annotated_frame": annotated_b64,
                }))

    except WebSocketDisconnect:
        print(f"[WebSocket] Camera {camera_id} disconnected")
    finally:
        active_sessions.pop(camera_id, None)


@app.post("/api/analyze-upload")
async def analyze_upload(file: UploadFile = File(...)):
    """Analyze an uploaded video file frame by frame.

    Returns annotated frames with bounding boxes drawn on them.
    """
    contents = await file.read()

    # Save to a temp file (cross-platform)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(contents)
        temp_path = tmp.name

    try:
        cap = cv2.VideoCapture(temp_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        duration = total_frames / fps if fps > 0 else 0

        results = []

        # Sample frames every ~2 seconds throughout the video
        interval_frames = int(fps * 2)
        if interval_frames < 1:
            interval_frames = 1

        sample_indices = list(range(0, total_frames, interval_frames))

        # Cap at 20 frames max to avoid excessive API calls
        if len(sample_indices) > 20:
            step = len(sample_indices) // 20
            sample_indices = sample_indices[::step][:20]

        for idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                continue

            # Analyze frame with Gemini
            result = analyzer.analyze_frame(frame)
            timestamp_sec = idx / fps

            # Draw bounding boxes on the frame
            annotated = draw_annotations(frame, result)
            annotated_b64 = frame_to_base64(annotated)

            # Also keep the original frame as base64 for reference
            original_b64 = frame_to_base64(frame)

            frame_result = {
                "frame_index": idx,
                "timestamp": f"{timestamp_sec:.1f}s",
                "timestamp_sec": round(timestamp_sec, 1),
                "result": result,
                "annotated_frame": annotated_b64,
                "original_frame": original_b64,
            }
            results.append(frame_result)

            # Also record as incident
            now = datetime.now()
            incident = {
                "id": len(incident_history) + 1,
                "camera": "UPLOAD",
                "status": result.get("status", "normal"),
                "confidence": result.get("confidence", 0.0),
                "description": result.get("description", ""),
                "timestamp": now.isoformat(),
                "time": now.strftime("%H:%M"),
                "hour": now.strftime("%H:00"),
                "state": result.get("status", "normal"),
                "regions": result.get("regions", []),
            }
            incident_history.append(incident)

        cap.release()

        return {
            "filename": file.filename,
            "total_frames": total_frames,
            "fps": round(fps, 1),
            "duration": f"{duration:.1f}s",
            "frames_analyzed": len(results),
            "analyses": results,
        }
    finally:
        os.remove(temp_path)


if __name__ == "__main__":
    import uvicorn
    print("=" * 55)
    print("  AlertVision — Web Dashboard")
    print("  Open http://localhost:8000 in your browser")
    print("=" * 55)
    uvicorn.run(app, host="0.0.0.0", port=8000)
