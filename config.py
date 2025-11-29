
# ============================================
# ESP32 CONFIGURATION
# ============================================

# ESP32-CAM (Camera)
ESP32_CAM_IP = "192.168.1.100"
ESP32_CAM_STREAM_URL = f"http://{ESP32_CAM_IP}/stream"
ESP32_CAM_STATUS_URL = f"http://{ESP32_CAM_IP}/status"

# ESP32 Buzzer (Alert System)
ESP32_BUZZER_IP = "192.168.1.101"
ESP32_BUZZER_ALERT_URL = f"http://{ESP32_BUZZER_IP}/alert"
ESP32_BUZZER_TEST_URL = f"http://{ESP32_BUZZER_IP}/test"
ESP32_BUZZER_STATUS_URL = f"http://{ESP32_BUZZER_IP}/status"

# ============================================
# YOLO MODEL CONFIGURATION
# ============================================

PERSON_DETECTOR_MODEL = "yolov8n.pt"
FACE_RECOGNITION_MODEL = r".\runs\face_detection\my_face_model5\weights\best.pt"

# ============================================
# DETECTION SETTINGS
# ============================================

PERSON_CONFIDENCE = 0.75
MIN_DETECTIONS = 5
KNOWN_CONFIDENCE = 0.92
ALERT_COOLDOWN = 30
BUZZER_PATTERN = 1
FRAME_SKIP = 5
IMAGE_SIZE = 640

# ============================================
# STORAGE SETTINGS
# ============================================

IMAGES_DIR = "security_images"
LOGS_FILE = "security_log.json"
SAVE_IMAGES = True
DUPLICATE_COOLDOWN_HOURS = 1
HASH_SIMILARITY_THRESHOLD = 5

# ============================================
# FASTAPI SETTINGS
# ============================================

HOST = "0.0.0.0"
PORT = 8000
DEBUG = False
CORS_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# ============================================
# SYSTEM SETTINGS
# ============================================

MAX_WORKERS = 2
STREAM_TIMEOUT = 10
RECONNECT_DELAY = 5
LOG_LEVEL = "INFO"
MAX_LOG_ENTRIES = 1000

# ============================================
# FEATURE FLAGS
# ============================================

ENABLE_WEB_INTERFACE = True
ENABLE_WEBSOCKET = True
ENABLE_IMAGE_SAVING = True
ENABLE_BUZZER_ALERTS = True
ENABLE_STATISTICS = True

# ============================================
# ADVANCED SETTINGS
# ============================================

TRACK_MAX_DISTANCE = 100
TRACK_TIMEOUT = 30
MIN_PERSON_AREA_PERCENT = 2
ESP32_STATUS_CHECK_INTERVAL = 60