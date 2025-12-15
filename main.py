from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
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

try:
    import config_new as config
except:
    import config

from security_system import SecuritySystem
from training_manager import TrainingManager
from camera_manager import CameraManager
from face_recognition_manager import FaceRecognitionManager
from telegram_notifier import TelegramNotifier
from image_manager import ImageManager
from websocket_handler import CameraWebSocketHandler

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Smart Security System",
    description="AI-powered security system with face recognition",
    version="2.0.0"
)

test_session = {
    'running': False,
    'start_time': None,
    'persons_detected': 0,
    'faces_detected': 0,
    'detections': [],
    'camera': None
}


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

security_system: Optional[SecuritySystem] = None
system_active = False
connected_websockets = []
training_manager = TrainingManager()
camera_manager = CameraManager()
camera_manager.detect_cameras(
    webcam_index=config.WEBCAM_INDEX,
    esp32_url=config.ESP32_CAM_STREAM_URL
)
camera_manager.select_camera('webcam')

ws_handler = CameraWebSocketHandler(buffer_size=getattr(config, 'WS_FRAME_BUFFER_SIZE', 2))

image_manager = ImageManager(
    base_dir=config.IMAGES_DIR,
    archive_hours=getattr(config, 'IMAGE_ARCHIVE_HOURS', 6),
    cleanup_interval_minutes=getattr(config, 'IMAGE_CLEANUP_INTERVAL_MINUTES', 30)
)

face_recognizer = None
if getattr(config, 'USE_FACE_RECOGNITION', True):
    try:
        face_recognizer = FaceRecognitionManager(
            known_faces_dir=getattr(config, 'KNOWN_FACES_DIR', 'known_faces'),
            encodings_cache=getattr(config, 'FACE_ENCODINGS_CACHE', 'face_encodings.pkl')
        )
        logger.info("Face recognition initialized")
    except Exception as e:
        logger.error(f"Failed to initialize face recognition: {e}")
        face_recognizer = None

telegram_notifier = None
if getattr(config, 'TELEGRAM_ENABLED', False):
    token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')
    if token and chat_id and token != "YOUR_BOT_TOKEN_HERE":
        try:
            telegram_notifier = TelegramNotifier(
                bot_token=token,
                chat_id=chat_id,
                cooldown_seconds=getattr(config, 'TELEGRAM_ALERT_COOLDOWN', 300)
            )
            if telegram_notifier.test_connection():
                logger.info("Telegram bot connected")
            else:
                telegram_notifier = None
        except Exception as e:
            logger.error(f"Failed to initialize Telegram: {e}")
            telegram_notifier = None

if hasattr(config, 'ESP32_CAM_STREAM_URL'):
    camera_manager.add_ip_camera("ESP32-CAM", config.ESP32_CAM_STREAM_URL)
    camera_manager.select_camera("esp32-cam")

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

@app.on_event("startup")
async def startup_event():
    global security_system
    
    logger.info("Starting Smart Security System...")
    
    if face_recognizer:
        known_persons = face_recognizer.get_known_persons()
        logger.info(f"Loaded {len(known_persons)} known persons")
    
    try:
        security_system = SecuritySystem(
            face_recognizer=face_recognizer,
            telegram_notifier=telegram_notifier,
            image_manager=image_manager,
            ws_handler=ws_handler,
            camera_manager=camera_manager
        )
        logger.info("Security system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize security system: {e}")
        security_system = None

@app.on_event("shutdown")
async def shutdown_event():
    global security_system, system_active
    
    logger.info("Shutting down Smart Security System...")
    
    if security_system and system_active:
        security_system.stop()
        system_active = False
        
    if image_manager:
        image_manager.stop_cleanup_thread()
        
    for ws in connected_websockets:
        try:
            await ws.close()
        except:
            pass
    
    logger.info("Shutdown complete")

@app.websocket("/ws/camera/{camera_id}")
async def websocket_camera_endpoint(websocket: WebSocket, camera_id: str):
    await ws_handler.handle_camera_connection(websocket, camera_id)

@app.websocket("/ws/live/{camera_id}")
async def websocket_live_feed(websocket: WebSocket, camera_id: str):
    await websocket.accept()
    
    try:
        while True:
            frame_data = ws_handler.get_latest_frame(camera_id)
            
            if frame_data:
                frame = frame_data['frame']
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                await websocket.send_bytes(buffer.tobytes())
            
            await asyncio.sleep(0.05)
    
    except:
        pass

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "esp32_cam_ip": getattr(config, 'ESP32_CAM_IP', ''),
            "esp32_buzzer_ip": getattr(config, 'ESP32_BUZZER_IP', '')
        }
    )

@app.get("/controls", response_class=HTMLResponse)
async def controls_page(request: Request):
    return templates.TemplateResponse("controls.html", {"request": request})

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    if Path("logs.html").exists():
        return FileResponse("logs.html")
    return templates.TemplateResponse("logs.html", {"request": request})

@app.get("/gallery", response_class=HTMLResponse)
async def gallery_page(request: Request):
    if Path("gallery.html").exists():
        return FileResponse("gallery.html")
    return templates.TemplateResponse("gallery.html", {"request": request})

@app.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request):
    return templates.TemplateResponse("statistics.html", {"request": request})

@app.get("/facecapture", response_class=HTMLResponse)
async def facecapture_page(request: Request):
    if Path("face_capture.html").exists():
        return FileResponse("face_capture.html")
    return templates.TemplateResponse("face_capture.html", {"request": request})

@app.get("/train", response_class=HTMLResponse)
async def training_page(request: Request):
    if Path("training.html").exists():
        return FileResponse("training.html")
    return templates.TemplateResponse("training.html", {"request": request})

@app.post("/api/start")
async def start_system(background_tasks: BackgroundTasks):
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
    global security_system, system_active
    
    if not security_system:
        return {
            "active": False,
            "esp32_cam_status": "disconnected",
            "telegram_status": "offline",
            "error": "System not initialized"
        }
 
    stats = security_system.get_stats()
    esp32_cam_status = check_esp32_status(config.ESP32_CAM_STATUS_URL)
    detections_24h = security_system.get_24h_stats()
    
    return {
        "active": system_active,
        "esp32_cam_status": esp32_cam_status,
        "telegram_status": "connected" if telegram_notifier else "offline",
        "detections_today": detections_24h.get('total', 0),
        "unknown_today": detections_24h.get('unknown', 0),
        "known_today": detections_24h.get('known', 0),
        "last_alert": get_last_alert_time(),
        "uptime": stats.get('uptime', 0),
        "cameras_connected": len(ws_handler.get_all_cameras()),
        "known_persons": len(face_recognizer.get_known_persons()) if face_recognizer else 0,
        "images_saved": detections_24h.get('total', 0),
        "false_positives_blocked": 0
    }

@app.get("/api/stats")
async def get_system_stats():
    global security_system
    
    if not security_system:
        raise HTTPException(status_code=500, detail="Security system not initialized")
    
    storage_stats = image_manager.get_storage_stats() if image_manager else {}
    ws_stats = ws_handler.get_stats()
    
    return {
        **security_system.get_detailed_stats(),
        "storage": storage_stats,
        "websocket": ws_stats,
        "known_persons": len(face_recognizer.get_known_persons()) if face_recognizer else 0
    }

@app.get("/api/detections")
async def get_detections(limit: int = 100, type: Optional[str] = None):
    global security_system
    
    if not security_system:
        return []
    
    return security_system.get_detections(limit=limit, type_filter=type)

@app.get("/api/detection/{detection_id}")
async def get_detection(detection_id: int):
    global security_system
    
    if not security_system:
        raise HTTPException(status_code=404, detail="Security system not initialized")
    
    detection = security_system.get_detection_by_id(detection_id)
    
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    
    return detection

@app.get("/api/stream")
async def video_stream():
    async def generate():
        while True:
            ret, frame = camera_manager.read_frame()
            if ret and frame is not None:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            await asyncio.sleep(0.033)
    
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.post("/api/settings")
async def update_settings(settings: DetectionSettings):
    global security_system
    
    if not security_system:
        raise HTTPException(status_code=500, detail="Security system not initialized")
    
    if settings.person_confidence is not None:
        security_system.person_conf = settings.person_confidence
    
    if settings.min_detections is not None:
        security_system.min_detections = settings.min_detections
    
    if settings.known_confidence is not None:
        security_system.known_conf = settings.known_confidence
    
    if settings.alert_cooldown is not None:
        security_system.alert_cooldown = settings.alert_cooldown
    
    if settings.save_images is not None:
        security_system.save_images = settings.save_images
    
    return {"status": "success", "message": "Settings updated"}

@app.get("/api/images")
async def get_images(limit: int = 50, type: str = "all"):
    if not image_manager:
        return []
    return image_manager.get_images(person_type=type, limit=limit)

@app.get("/api/images/{filename}")
async def get_image(filename: str):
    if not image_manager:
        raise HTTPException(status_code=404, detail="Image manager not available")
    
    for directory in [
        image_manager.recent_unknown,
        image_manager.recent_known,
        image_manager.archived_unknown,
        image_manager.archived_known
    ]:
        filepath = directory / filename
        if filepath.exists():
            return FileResponse(filepath)
    
    if Path(config.IMAGES_DIR).exists():
        for subdir in ['unknown', 'known']:
            filepath = Path(config.IMAGES_DIR) / subdir / filename
            if filepath.exists():
                return FileResponse(filepath)
    
    raise HTTPException(status_code=404, detail="Image not found")

@app.delete("/api/images/{filename}")
async def delete_image(filename: str):
    if not image_manager:
        success = False
        for subdir in ['unknown', 'known']:
            filepath = Path(config.IMAGES_DIR) / subdir / filename
            if filepath.exists():
                filepath.unlink()
                success = True
        return {"success": success}
    
    success = image_manager.delete_image(filename)
    return {"success": success}

@app.get("/api/cameras")
async def get_cameras():
    cameras = camera_manager.get_cameras()
    ws_cameras = ws_handler.get_all_cameras()
    return {
        "local_cameras": cameras,
        "websocket_cameras": ws_cameras
    }

@app.post("/api/cameras/add-ip")
async def add_ip_camera(request: dict):
    name = request.get("name")
    url = request.get("url")
    
    if not name or not url:
        raise HTTPException(status_code=400, detail="Name and URL required")
    
    return camera_manager.add_ip_camera(name, url)

@app.post("/api/cameras/select/{camera_id}")
async def select_camera(camera_id: str):
    return camera_manager.select_camera(camera_id)

@app.get("/api/face-recognition/persons")
async def get_known_persons():
    if not face_recognizer:
        return {"error": "Face recognition not available"}
    
    return face_recognizer.get_known_persons()

@app.post("/api/face-recognition/reload")
async def reload_face_encodings():
    if not face_recognizer:
        return {"error": "Face recognition not available"}
    
    success = face_recognizer.reload_encodings()
    return {"success": success}

@app.delete("/api/face-recognition/persons/{person_name}")
async def delete_known_person(person_name: str):
    if not face_recognizer:
        return {"error": "Face recognition not available"}
    
    success = face_recognizer.delete_person(person_name)
    return {"success": success}

@app.post("/api/training/register-person")
async def register_person(
    person_name: str = Form(...),
    frames: List[UploadFile] = File(...)
):
    if not face_recognizer:
        return {"error": "Face recognition not available"}
    
    try:
        temp_frames = []
        for frame_file in frames:
            contents = await frame_file.read()
            nparr = np.frombuffer(contents, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                temp_frames.append(frame)
        
        camera_name = camera_manager.get_current()['name'] if camera_manager.get_current() else 'Unknown'
        result = face_recognizer.capture_and_add_person(
            person_name=person_name,
            frames=temp_frames,
            camera_name=camera_name
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error registering person: {e}")
        return {"error": str(e)}

@app.post("/api/training/start-capture")
async def start_capture(request: dict):
    person_name = request.get("person_name", "")
    camera_source = request.get("camera", "current")
    auto = request.get("auto", True)
    target = request.get("target", 300)
    
    if not person_name:
        raise HTTPException(status_code=400, detail="Person name required")
    
    return training_manager.start_capture(person_name, camera_source, auto, target)

@app.post("/api/training/capture-frame")
async def capture_frame():
    ret, frame = camera_manager.read_frame()
    
    if not ret or frame is None:
        raise HTTPException(status_code=500, detail="Failed to read frame from camera")
    
    return training_manager.capture_frame(frame)

@app.post("/api/training/stop-capture")
async def stop_capture():
    return training_manager.stop_capture()

@app.get("/api/training/capture-status")
async def get_capture_status():
    return {
        "capturing": training_manager.capturing,
        "person": training_manager.capture_person,
        "camera": training_manager.capture_camera,
        "count": training_manager.captured_count,
        "target": training_manager.target_count
    }

@app.get("/api/training/datasets")
async def get_datasets():
    return training_manager.get_datasets()

@app.delete("/api/training/dataset/{dataset_name}")
async def delete_dataset(dataset_name: str):
    return training_manager.delete_dataset(dataset_name)

@app.post("/api/training/start")
async def start_training(request: dict):
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
    return training_manager.get_training_progress()

@app.post("/api/training/stop")
async def stop_training():
    return training_manager.stop_training()

@app.get("/api/training/models")
async def get_models():
    return training_manager.get_models()

@app.get("/api/training/model/{model_name}")
async def get_model_info(model_name: str):
    return training_manager.get_model_info(model_name)

@app.delete("/api/training/model/{model_name}")
async def delete_model(model_name: str):
    return training_manager.delete_model(model_name)

@app.get("/api/training/preview")
async def training_preview():
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

@app.get("/api/cameras/list")
async def list_cameras():
    return camera_manager.list_all()

@app.post("/api/cameras/switch")
async def switch_camera(data: dict):
    camera_id = data.get('camera_id')
    success = camera_manager.select_camera(camera_id)
    return {'success': success, 'current': camera_manager.get_current()}

@app.get("/api/cameras/current")
async def current_camera():
    return camera_manager.get_current() or {'name': 'None'}

@app.post("/api/test/start")
async def start_test(data: dict):
    global test_session, system_active, security_system
    
    if not system_active:
        security_system.start()
        system_active = True
        logger.info("Started detection for test")
    
    test_session = {
        'running': True,
        'start_time': datetime.now(),
        'persons_detected': 0,
        'faces_detected': 0,
        'detections': [],
        'camera': camera_manager.get_current()['name'] if camera_manager.get_current() else 'Unknown'
    }
    
    return {'success': True, 'message': 'Test started'}

@app.get("/api/test/results")
async def get_test_results():
    return test_session

@app.post("/api/test/mark-false")
async def mark_false_positive(data: dict):
    detection_id = data.get('id')
    if 'false_positives' not in test_session:
        test_session['false_positives'] = []
    test_session['false_positives'].append(detection_id)
    return {'success': True}

@app.post("/api/test/stop")
async def stop_test():
    global test_session, system_active, security_system
    
    test_session['running'] = False
    test_session['end_time'] = datetime.now()
    
    if system_active and security_system:
        security_system.stop()
        system_active = False
        logger.info("Stopped detection after test")
    
    return {'success': True, 'message': 'Test stopped'}

@app.get("/test")
async def test_page(request: Request):
    global system_active, security_system
    
    if system_active and security_system:
        security_system.stop()
        system_active = False
        logger.info("Stopped detection for model testing")
    
    return templates.TemplateResponse("model_test.html", {"request": request})

@app.get("/face-capture")
async def face_capture_page(request: Request):
    global system_active, security_system
    
    if system_active and security_system:
        security_system.stop()
        system_active = False
        logger.info("Stopped detection for face capture")
        
    camera_manager.release()
    
    return templates.TemplateResponse("face_capture.html", {"request": request})

@app.post("/api/train/register-person")
async def register_person(
    person_name: str = Form(...),
    frames: List[UploadFile] = File(...)
):
    """Register a new person by capturing their face from uploaded frames"""
    if not face_recognizer:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Face recognition not available"}
        )
    
    if not person_name or not person_name.strip():
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Person name is required"}
        )
    
    person_name = person_name.strip()
    logger.info(f"Registering person: {person_name} with {len(frames)} frames")
    
    # Convert uploaded files to numpy arrays
    frame_arrays = []
    for i, frame_file in enumerate(frames):
        try:
            contents = await frame_file.read()
            logger.info(f"Frame {i}: received {len(contents)} bytes, filename={frame_file.filename}, content_type={frame_file.content_type}")
            
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is not None:
                logger.info(f"Frame {i}: decoded to shape={img.shape}, dtype={img.dtype}")
                frame_arrays.append(img)
            else:
                logger.warning(f"Failed to decode frame {i} - cv2.imdecode returned None")
        except Exception as e:
            logger.error(f"Error processing frame {i}: {e}")
    
    if not frame_arrays:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "No valid frames received"}
        )
    
    # Use face recognition manager to add person
    result = face_recognizer.capture_and_add_person(
        person_name=person_name,
        frames=frame_arrays,
        camera_name="Browser Camera"
    )
    
    if result.get("error"):
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": result["error"]}
        )
    
    return {
        "success": True,
        "person_name": person_name,
        "photos_saved": result.get("encodings_added", 0),
        "encodings_added": result.get("encodings_added", 0),
        "total_encodings": result.get("total_encodings", 0)
    }

@app.post("/api/telegram/test")
async def test_telegram():
    if not telegram_notifier:
        return {"error": "Telegram not configured"}
    
    try:
        success = telegram_notifier.send_text("🧪 Test message from Security System")
        if success:
            return {"message": "Telegram test sent successfully!"}
        return {"error": "Failed to send Telegram message"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

def check_esp32_status(url: str) -> str:
    if not url:
        return "offline"
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return "online"
        else:
            return "error"
    except:
        return "offline"

def get_last_alert_time() -> Optional[str]:
    global security_system
    
    if not security_system:
        return None
    
    detections = security_system.get_detections(limit=1, type_filter="unknown")
    if detections:
        return detections[0].get('timestamp')
    
    return None

async def run_security_system():
    global security_system, system_active
    
    if not security_system:
        logger.error("Cannot start system: not initialized")
        return
    
    try:
        logger.info("Starting security monitoring...")
        await security_system.run()
    except Exception as e:
        logger.error(f"Security system error: {e}")
        system_active = False

def main():
    logger.info("="*70)
    logger.info("SMART SECURITY SYSTEM - FASTAPI SERVER")
    logger.info("="*70)
    logger.info(f"ESP32-CAM: {getattr(config, 'ESP32_CAM_IP', 'N/A')}")
    logger.info(f"Face Recognition: {'Enabled' if face_recognizer else 'Disabled'}")
    logger.info(f"Telegram: {'Enabled' if telegram_notifier else 'Disabled'}")
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