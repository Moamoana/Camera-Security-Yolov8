"""
FastAPI Backend for Smart Security System
Integrates ESP32-CAM, ESP32 Buzzer, and AI Detection
"""

from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import asyncio
import json
import os
from datetime import datetime, timedelta
import cv2
import requests
import numpy as np
from pathlib import Path
import logging
import config
from security_system import SecuritySystem
from training_manager import TrainingManager
from camera_manager import CameraManager

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# FASTAPI APP INITIALIZATION
# ============================================

app = FastAPI(
    title="Smart Security System",
    description="AI-powered security system with ESP32 integration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
Path(config.IMAGES_DIR).mkdir(parents=True, exist_ok=True)
Path("static").mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================
# GLOBAL STATE
# ============================================

security_system: Optional[SecuritySystem] = None
system_active = False
connected_websockets = []
training_manager = TrainingManager()
camera_manager = CameraManager()
camera_manager.add_ip_camera("ESP32-CAM", config.ESP32_CAM_STREAM_URL)
camera_manager.select_camera("esp32-cam")

# ============================================
# PYDANTIC MODELS
# ============================================

class SystemStatus(BaseModel):
    active: bool
    esp32_cam_status: str
    esp32_buzzer_status: str
    detections_today: int
    unknown_today: int
    known_today: int
    last_alert: Optional[str]
    uptime: int

class DetectionSettings(BaseModel):
    person_confidence: Optional[float] = None
    min_detections: Optional[int] = None
    known_confidence: Optional[float] = None
    alert_cooldown: Optional[int] = None
    save_images: Optional[bool] = None

class AlertRequest(BaseModel):
    pattern: int = 1

class Detection(BaseModel):
    id: int
    type: str
    confidence: float
    timestamp: str
    date: str
    time: str
    image_path: Optional[str] = None

# ============================================
# STARTUP/SHUTDOWN EVENTS
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize security system on startup"""
    global security_system
    
    logger.info("Starting Smart Security System...")
    
    try:
        security_system = SecuritySystem(
            esp32_cam_url=config.ESP32_CAM_STREAM_URL,
            esp32_buzzer_url=config.ESP32_BUZZER_ALERT_URL,
            face_model_path=config.FACE_RECOGNITION_MODEL,
            person_conf=config.PERSON_CONFIDENCE,
            known_conf=config.KNOWN_CONFIDENCE,
            min_detections=config.MIN_DETECTIONS,
            save_images=config.SAVE_IMAGES,
            images_dir=config.IMAGES_DIR,
            camera_manager=camera_manager
        )
        logger.info("Security system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize security system: {e}")
        security_system = None

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global security_system, system_active
    
    logger.info("Shutting down Smart Security System...")
    
    if security_system and system_active:
        security_system.stop()
        system_active = False
        
    for ws in connected_websockets:
        try:
            await ws.close()
        except:
            pass
    
    logger.info("Shutdown complete")

# ============================================
# WEB PAGES
# ============================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "esp32_cam_ip": config.ESP32_CAM_IP,
            "esp32_buzzer_ip": config.ESP32_BUZZER_IP
        }
    )

@app.get("/controls", response_class=HTMLResponse)
async def controls_page(request: Request):
    """Controls page"""
    return templates.TemplateResponse("controls.html", {"request": request})

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Logs page"""
    return templates.TemplateResponse("logs.html", {"request": request})

@app.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request):
    """Image gallery page"""
    return templates.TemplateResponse("gallery.html", {"request": request})

@app.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request):
    """Statistics page"""
    return templates.TemplateResponse("statistics.html", {"request": request})

# ============================================
# API ENDPOINTS - SYSTEM CONTROL
# ============================================

@app.post("/api/start")
async def start_system(background_tasks: BackgroundTasks):
    """Start the security system"""
    global system_active, security_system
    
    if not security_system:
        raise HTTPException(status_code=500, detail="Security system not initialized")
    
    if system_active:
        return {"status": "already_running", "message": "System is already running"}
    
    background_tasks.add_task(run_security_system)
    system_active = True
    
    logger.info("Security system started")
    return {"status": "success", "message": "Security system started"}

@app.post("/api/stop")
async def stop_system():
    """Stop the security system"""
    global system_active, security_system
    
    if not security_system:
        raise HTTPException(status_code=500, detail="Security system not initialized")
    
    if not system_active:
        return {"status": "already_stopped", "message": "System is not running"}
    
    security_system.stop()
    system_active = False
    
    logger.info("Security system stopped")
    return {"status": "success", "message": "Security system stopped"}

@app.get("/api/status")
async def get_status():
    """Get system status"""
    global security_system, system_active
    
    if not security_system:
        return {
            "active": False,
            "esp32_cam_status": "disconnected",
            "esp32_buzzer_status": "disconnected",
            "error": "System not initialized"
        }
 
    stats = security_system.get_stats()
    esp32_cam_status = check_esp32_status(config.ESP32_CAM_STATUS_URL)
    esp32_buzzer_status = check_esp32_status(config.ESP32_BUZZER_STATUS_URL)
    detections_24h = security_system.get_24h_stats()
    
    return {
        "active": system_active,
        "esp32_cam_status": esp32_cam_status,
        "esp32_buzzer_status": esp32_buzzer_status,
        "detections_today": stats.get('total_detections', 0),
        "unknown_today": detections_24h.get('unknown', 0),
        "known_today": detections_24h.get('known', 0),
        "images_saved": stats.get('images_saved', 0),
        "false_positives_blocked": stats.get('false_positives_blocked', 0),
        "last_alert": get_last_alert_time(),
        "uptime": stats.get('uptime', 0)
    }

# ============================================
# API ENDPOINTS - SETTINGS
# ============================================

@app.get("/api/settings")
async def get_settings():
    """Get current settings"""
    return {
        "person_confidence": config.PERSON_CONFIDENCE,
        "min_detections": config.MIN_DETECTIONS,
        "known_confidence": config.KNOWN_CONFIDENCE,
        "alert_cooldown": config.ALERT_COOLDOWN,
        "save_images": config.SAVE_IMAGES,
        "frame_skip": config.FRAME_SKIP,
        "buzzer_pattern": config.BUZZER_PATTERN
    }

@app.put("/api/settings")
async def update_settings(settings: DetectionSettings):
    """Update detection settings"""
    global security_system
    
    if not security_system:
        raise HTTPException(status_code=500, detail="Security system not initialized")
    
    if settings.person_confidence is not None:
        config.PERSON_CONFIDENCE = settings.person_confidence
        security_system.person_conf = settings.person_confidence
    
    if settings.min_detections is not None:
        config.MIN_DETECTIONS = settings.min_detections
        security_system.min_detections = settings.min_detections
    
    if settings.known_confidence is not None:
        config.KNOWN_CONFIDENCE = settings.known_confidence
        security_system.known_conf = settings.known_confidence
    
    if settings.alert_cooldown is not None:
        config.ALERT_COOLDOWN = settings.alert_cooldown
        security_system.alert_cooldown = settings.alert_cooldown
    
    if settings.save_images is not None:
        config.SAVE_IMAGES = settings.save_images
        security_system.save_images = settings.save_images
    
    logger.info(f"Settings updated: {settings}")
    return {"status": "success", "message": "Settings updated", "settings": await get_settings()}

# ============================================
# API ENDPOINTS - ESP32 CONTROL
# ============================================

@app.post("/api/buzzer/test")
async def test_buzzer():
    """Test the buzzer"""
    try:
        response = requests.get(config.ESP32_BUZZER_TEST_URL, timeout=5)
        if response.status_code == 200:
            logger.info("Buzzer test successful")
            return {"status": "success", "message": "Buzzer test successful"}
        else:
            raise HTTPException(status_code=500, detail="Buzzer test failed")
    except Exception as e:
        logger.error(f"Buzzer test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/buzzer/alert")
async def trigger_alert(alert: AlertRequest):
    """Manually trigger buzzer alert"""
    try:
        url = f"{config.ESP32_BUZZER_ALERT_URL}?pattern={alert.pattern}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            logger.info(f"Manual alert triggered: pattern {alert.pattern}")
            return {"status": "success", "message": f"Alert pattern {alert.pattern} triggered"}
        else:
            raise HTTPException(status_code=500, detail="Alert failed")
    except Exception as e:
        logger.error(f"Alert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/esp32/status")
async def get_esp32_status():
    """Get ESP32 devices status"""
    return {
        "camera": check_esp32_status(config.ESP32_CAM_STATUS_URL),
        "buzzer": check_esp32_status(config.ESP32_BUZZER_STATUS_URL),
        "camera_url": config.ESP32_CAM_IP,
        "buzzer_url": config.ESP32_BUZZER_IP
    }

# ============================================
# API ENDPOINTS - DETECTIONS & LOGS
# ============================================

@app.get("/api/detections")
async def get_detections(limit: int = 100, type: Optional[str] = None):
    """Get detection history"""
    global security_system
    
    if not security_system:
        return []
    
    detections = security_system.get_detections(limit=limit, type_filter=type)
    return detections

@app.get("/api/detections/{detection_id}")
async def get_detection(detection_id: int):
    """Get specific detection"""
    global security_system
    
    if not security_system:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    detection = security_system.get_detection_by_id(detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    return detection

@app.get("/api/stats")
async def get_statistics():
    """Get system statistics"""
    global security_system
    
    if not security_system:
        return {}
    
    return security_system.get_detailed_stats()

# ============================================
# API ENDPOINTS - IMAGES
# ============================================

@app.get("/api/images")
async def get_images(type: Optional[str] = None, limit: int = 50):
    """Get saved images"""
    images = []
    
    base_path = Path(config.IMAGES_DIR)

    if type == "unknown":
        search_paths = [base_path / "unknown"]
    elif type == "known":
        search_paths = [base_path / "known"]
    else:
        search_paths = [base_path / "unknown", base_path / "known"]

    for path in search_paths:
        if path.exists():
            for img_file in sorted(path.glob("full_*.jpg"), reverse=True)[:limit]:
                images.append({
                    "filename": img_file.name,
                    "path": str(img_file),
                    "type": "unknown" if "unknown" in str(img_file) else "known",
                    "timestamp": datetime.fromtimestamp(img_file.stat().st_mtime).isoformat(),
                    "size": img_file.stat().st_size
                })
    
    return images[:limit]

@app.get("/api/images/{filename}")
async def get_image(filename: str):
    """Get a specific image file"""
    for subdir in ["unknown", "known"]:
        image_path = Path(config.IMAGES_DIR) / subdir / filename
        if image_path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(image_path)
    
    raise HTTPException(status_code=404, detail="Image not found")

@app.delete("/api/images/{filename}")
async def delete_image(filename: str):
    """Delete an image"""
    for subdir in ["unknown", "known"]:
        full_path = Path(config.IMAGES_DIR) / subdir / filename
        crop_path = Path(config.IMAGES_DIR) / subdir / filename.replace("full_", "crop_")
        
        if full_path.exists():
            full_path.unlink()
            if crop_path.exists():
                crop_path.unlink()
            logger.info(f"Deleted image: {filename}")
            return {"status": "success", "message": "Image deleted"}
    
    raise HTTPException(status_code=404, detail="Image not found")

# ============================================
# STREAMING ENDPOINTS
# ============================================

@app.get("/api/stream")
async def video_stream():
    """Stream processed video with detection boxes"""
    global security_system
    if not security_system:
        raise HTTPException(status_code=500, detail="Security system not initialized")
    
    async def generate():
        """Generate video frames"""
        while True:
            frame = security_system.current_frame
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                ret, buffer = cv2.imencode('.jpg', blank)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            await asyncio.sleep(0.033)
    
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# ============================================
# WEBSOCKET ENDPOINTS
# ============================================

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket for real-time events"""
    await websocket.accept()
    connected_websockets.append(websocket)
    
    try:
        while True:
            if security_system:
                stats = security_system.get_stats()
                await websocket.send_json({
                    "type": "stats_update",
                    "data": stats
                })
            
            await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_websockets.remove(websocket)

# ============================================
# TRAINING & CAMERA MANAGEMENT ENDPOINTS
# ============================================


@app.get("/api/cameras")
async def get_cameras():
    """Get list of available cameras"""
    return camera_manager.get_cameras()

@app.post("/api/camera/select")
async def select_camera(request: dict):
    """Select a camera"""
    global system_active, security_system
    
    camera_id = request.get("camera_id")
    
    if system_active and security_system:
        security_system.stop()
        system_active = False
        logger.info("Stopped detection to switch camera")
    
    result = camera_manager.select_camera(camera_id)
    return result

@app.get("/api/camera/current")
async def get_current_camera():
    """Get currently selected camera"""
    camera = camera_manager.get_current_camera()
    if camera:
        return camera
    return {"id": None, "name": "None selected"}

@app.post("/api/camera/add")
async def add_ip_camera(request: dict):
    """Add IP camera"""
    name = request.get("name")
    url = request.get("url")
    
    if not name or not url:
        raise HTTPException(status_code=400, detail="Name and URL required")
    
    return camera_manager.add_ip_camera(name, url)

@app.get("/api/camera/test/{camera_id}")
async def test_camera(camera_id: str):
    """Test camera connection"""
    return camera_manager.test_camera(camera_id)

# ---------- Data Collection ----------

@app.post("/api/training/start-capture")
async def start_capture(request: dict):
    """Start capturing images for training"""
    person_name = request.get("person_name")
    camera_source = request.get("camera_source", "unknown")
    auto = request.get("auto", True)
    target = request.get("target", 300)
    
    if not person_name:
        raise HTTPException(status_code=400, detail="Person name required")
    
    return training_manager.start_capture(person_name, camera_source, auto, target)

@app.post("/api/training/capture-frame")
async def capture_frame():
    """Capture current frame from camera"""
    ret, frame = camera_manager.read_frame()
    
    if not ret or frame is None:
        raise HTTPException(status_code=500, detail="Failed to read frame from camera")
    
    return training_manager.capture_frame(frame)

@app.post("/api/training/stop-capture")
async def stop_capture():
    """Stop capturing images"""
    return training_manager.stop_capture()

@app.get("/api/training/capture-status")
async def get_capture_status():
    """Get current capture status"""
    return {
        "capturing": training_manager.capturing,
        "person": training_manager.capture_person,
        "camera": training_manager.capture_camera,
        "count": training_manager.captured_count,
        "target": training_manager.target_count
    }

@app.get("/api/training/datasets")
async def get_datasets():
    """Get all collected datasets"""
    return training_manager.get_datasets()

@app.delete("/api/training/dataset/{dataset_name}")
async def delete_dataset(dataset_name: str):
    """Delete a dataset"""
    return training_manager.delete_dataset(dataset_name)

# ---------- Model Training ----------

@app.post("/api/training/start")
async def start_training(request: dict):
    """Start model training"""
    model_name = request.get("model_name")
    selected_datasets = request.get("datasets", [])
    epochs = request.get("epochs", 100)
    batch = request.get("batch", 16)
    imgsz = request.get("imgsz", 640)
    
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name required")
    
    if not selected_datasets:
        raise HTTPException(status_code=400, detail="No datasets selected")
    
    return training_manager.start_training(model_name, selected_datasets, epochs, batch, imgsz)

@app.get("/api/training/status")
async def get_training_status():
    """Get training progress"""
    return training_manager.get_training_progress()

@app.post("/api/training/stop")
async def stop_training():
    """Stop training (if possible)"""
    return training_manager.stop_training()

# ---------- Model Management ----------

@app.get("/api/training/models")
async def get_models():
    """Get all trained models"""
    return training_manager.get_models()

@app.get("/api/training/model/{model_name}")
async def get_model_info(model_name: str):
    """Get model details"""
    return training_manager.get_model_info(model_name)

@app.post("/api/training/load-model")
async def load_model(request: dict):
    """Load/activate a trained model"""
    global security_system, system_active
    
    model_name = request.get("model_name")
    
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name required")
   
    model_path = training_manager.models_dir / model_name / "weights" / "best.pt"
    
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model not found")
   
    if system_active and security_system:
        security_system.stop()
        system_active = False
   
    config.FACE_RECOGNITION_MODEL = str(model_path)
   
    security_system = SecuritySystem(
        esp32_cam_url=config.ESP32_CAM_STREAM_URL,
        esp32_buzzer_url=config.ESP32_BUZZER_ALERT_URL,
        face_model_path=str(model_path),
        person_conf=config.PERSON_CONFIDENCE,
        known_conf=config.KNOWN_CONFIDENCE,
        min_detections=config.MIN_DETECTIONS,
        save_images=config.SAVE_IMAGES,
        images_dir=config.IMAGES_DIR,
        camera_manager=camera_manager
    )
    
    logger.info(f"Loaded model: {model_name}")
    
    return {
        "status": "loaded",
        "model": model_name,
        "path": str(model_path)
    }

@app.delete("/api/training/model/{model_name}")
async def delete_model(model_name: str):
    """Delete a trained model"""
    return training_manager.delete_model(model_name)

# ---------- Training Preview Stream ----------

@app.get("/api/training/preview")
async def training_preview():
    """Stream from selected camera for training preview"""
    async def generate():
        while True:
            ret, frame = camera_manager.read_frame()
            
            if ret and frame is not None:
                if training_manager.capturing:
                    cv2.putText(frame, f"Capturing: {training_manager.captured_count}/{training_manager.target_count}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(blank, "No Camera Selected", (150, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                ret, buffer = cv2.imencode('.jpg', blank)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            await asyncio.sleep(0.033)
    
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# ============================================
# WEB PAGES
# ============================================

@app.get("/train", response_class=HTMLResponse)
async def training_page(request: Request):
    """Training and model management page"""
    return templates.TemplateResponse("training.html", {"request": request})

# ============================================
# HELPER FUNCTIONS
# ============================================

def check_esp32_status(url: str) -> str:
    """Check if ESP32 is online"""
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return "online"
        else:
            return "error"
    except:
        return "offline"

def get_last_alert_time() -> Optional[str]:
    """Get time of last unknown person alert"""
    global security_system
    
    if not security_system:
        return None
    
    detections = security_system.get_detections(limit=1, type_filter="unknown")
    if detections:
        return detections[0].get('timestamp')
    
    return None

async def run_security_system():
    """Run security system in background"""
    global security_system, system_active
    
    if not security_system:
        logger.error("Cannot start system: not initialized")
        return
    
    try:
        logger.info("Starting security monitoring...")
        import threading
        monitoring_thread = threading.Thread(target=security_system.start, daemon=True)
        monitoring_thread.start()
    except Exception as e:
        logger.error(f"Security system error: {e}")
        system_active = False

# ============================================
# MAIN
# ============================================

def main():
    """Run FastAPI server"""
    logger.info("="*70)
    logger.info("SMART SECURITY SYSTEM - FASTAPI SERVER")
    logger.info("="*70)
    logger.info(f"ESP32-CAM: {config.ESP32_CAM_IP}")
    logger.info(f"ESP32 Buzzer: {config.ESP32_BUZZER_IP}")
    logger.info(f"Face Model: {config.FACE_RECOGNITION_MODEL}")
    logger.info(f"Web Interface: http://{config.HOST}:{config.PORT}")
    logger.info("="*70)
    
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower()
    )

if __name__ == "__main__":
    main()