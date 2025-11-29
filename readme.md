# 🛡️ Smart Security System

**AI-Powered Face Recognition Security System with ESP32 Integration**

A complete, production-ready security monitoring system featuring real-time face detection, multi-camera support, web-based training interface, and ESP32 hardware integration.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [System Architecture](#system-architecture)
- [Complete Feature List](#complete-feature-list)
- [User Guide](#user-guide)
- [Training System](#training-system)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Configuration](#configuration)

---

## 🎯 Overview

This Smart Security System combines AI-powered face recognition with modern web technologies and IoT hardware to create a complete surveillance solution.

**What It Does:**
- Detects and recognizes faces in real-time
- Alerts you when unknown persons are detected
- Supports multiple cameras (webcams, ESP32-CAM, IP cameras)
- Web-based interface for training custom models
- Complete logging and image gallery
- ESP32 hardware integration for alerts

**Technology Stack:**
- **Backend:** Python, FastAPI, YOLOv8, OpenCV
- **Frontend:** HTML, CSS, JavaScript
- **Hardware:** ESP32-CAM, ESP32 Buzzer (optional)
- **AI:** Custom-trained YOLO models

---

## ✨ Key Features

### 🎥 **Real-Time Detection**
- Live face recognition with bounding boxes
- Multi-stage verification (prevents false positives)
- Color-coded detection (Yellow: Verifying, Green: Known, Red: Unknown)
- Confidence-based classification
- Smart tracking across frames

### 📹 **Multi-Camera Support**
- Auto-detect webcams
- ESP32-CAM integration
- Custom IP cameras
- Instant camera switching
- No conflicts or lag

### 🎓 **Web-Based Training**
- Collect training data via browser
- Auto-capture mode (hands-free)
- Train custom face recognition models
- Multi-person support
- Model management (load, switch, delete)

### 📊 **Complete Dashboard**
- Live video feed
- System status indicators
- Real-time statistics
- Recent alerts log
- Camera selector

### 📝 **Logs & Gallery**
- Complete detection history
- Searchable and filterable logs
- Export to CSV/JSON
- Image gallery with lightbox
- Date range filtering

### 🚨 **ESP32 Integration**
- ESP32-CAM for video streaming
- ESP32 Buzzer for alerts
- WiFi connectivity
- Status monitoring

---

## 🚀 Quick Start

### **5-Minute Setup**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start server
python main.py

# 3. Open browser
http://localhost:8000

# 4. Train your face
# - Go to /train
# - Auto-capture 300 images
# - Train model (30-60 min)
# - Load model

# 5. Start detection
# - Dashboard
# - Click "Start Detection"
# - You're recognized! ✅
```

### **With ESP32-CAM**

```bash
# 1. Update config.py
ESP32_CAM_IP = "192.168.1.100"  # Your ESP32-CAM IP

# 2. Start server
python main.py

# 3. Dashboard auto-selects ESP32-CAM
# 4. Train on ESP32-CAM
# 5. Perfect recognition! ✅
```

---

## 📦 Installation

### **Requirements**

- Python 3.8+
- 8GB RAM (16GB recommended)
- Webcam or ESP32-CAM
- Windows/Linux/Mac

### **Step 1: Clone Repository**

```bash
git clone https://github.com/yourusername/smart-security-system.git
cd smart-security-system
```

### **Step 2: Create Virtual Environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### **Step 3: Install Dependencies**

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```txt
fastapi==0.104.1
uvicorn==0.24.0
ultralytics==8.0.196
opencv-python==4.8.1.78
numpy==1.24.3
Pillow==10.1.0
imagehash==4.3.1
requests==2.31.0
jinja2==3.1.2
python-multipart==0.0.6
```

### **Step 4: Configure**

Edit `config.py`:

```python
# ESP32 IPs (if using)
ESP32_CAM_IP = "192.168.1.100"
ESP32_BUZZER_IP = "192.168.1.101"

# Detection thresholds
PERSON_CONFIDENCE = 0.75
KNOWN_CONFIDENCE = 0.92
MIN_DETECTIONS = 5
```

### **Step 5: Run**

```bash
python main.py
```

Open: `http://localhost:8000`

---

## 🏗️ System Architecture

### **Components**

```
┌─────────────────────────────────────────────┐
│           Web Browser (User)                │
│  Dashboard | Training | Logs | Gallery      │
└──────────────────┬──────────────────────────┘
                   │ HTTP/WebSocket
┌──────────────────▼──────────────────────────┐
│         FastAPI Server (main.py)            │
│  • Routes & API                             │
│  • WebSocket streaming                      │
│  • Static file serving                      │
└──┬────────────┬────────────┬────────────────┘
   │            │            │
┌──▼──────┐ ┌──▼──────┐ ┌──▼──────────┐
│Camera   │ │Security │ │Training     │
│Manager  │ │System   │ │Manager      │
│         │ │         │ │             │
│•Detect  │ │•Detect  │ │•Collect data│
│•Switch  │ │•Track   │ │•Train models│
│•Stream  │ │•Alert   │ │•Manage      │
└──┬──────┘ └──┬──────┘ └──┬──────────┘
   │           │            │
┌──▼──┐    ┌──▼──┐     ┌──▼──┐
│Cam  │    │YOLO │     │YOLO │
│Feed │    │Model│     │Train│
└─────┘    └──┬──┘     └─────┘
              │
         ┌────▼────┐
         │ESP32    │
         │Buzzer   │
         └─────────┘
```

### **Data Flow**

**Detection Pipeline:**
```
Camera → Frame → Person Detection → Face Recognition
                                          ↓
                  ← Annotated ← Tracking ← Classification
                       ↓
                  Browser Display
                       ↓
                 Save + Alert (if unknown)
```

**Training Pipeline:**
```
Camera → Capture Images → Save Dataset
                              ↓
                  Prepare YOLO Format
                              ↓
                      Train Model
                              ↓
                   Save Model + Metadata
                              ↓
                      Load into System
```

---

## 📋 Complete Feature List

### **1. Detection System**

#### **Person Detection**
✅ YOLOv8 person detection  
✅ Confidence threshold filtering  
✅ Bounding box visualization  
✅ Real-time processing  

#### **Face Recognition**
✅ Custom-trained YOLO models  
✅ Known vs Unknown classification  
✅ Multi-stage verification  
✅ Confidence-based decisions  

#### **Tracking**
✅ Cross-frame person tracking  
✅ Track ID assignment  
✅ Movement prediction  
✅ Duplicate prevention  

#### **Smart Verification**
✅ Pending phase (yellow boxes)  
✅ Minimum detection count (5 default)  
✅ Confidence averaging  
✅ False positive prevention  

### **2. Camera Management**

✅ Auto-detect webcams (0-2)  
✅ ESP32-CAM support  
✅ Custom IP camera support  
✅ Hot-swap camera switching  
✅ Resolution detection  
✅ Connection testing  
✅ Single shared stream  
✅ No conflicts or lag  

### **3. Web Interface**

#### **Dashboard (`/`)**
✅ Live video feed with annotations  
✅ System status indicators  
✅ Camera selector dropdown  
✅ Statistics cards  
✅ Recent alerts log  
✅ Control buttons  
✅ Quick navigation  

#### **Training Page (`/train`)**
✅ Camera selection interface  
✅ Data collection controls  
✅ Live preview  
✅ Auto-capture mode  
✅ Progress tracking  
✅ Dataset management  
✅ Training interface  
✅ Model management  

#### **Logs Page (`/logs`)**
✅ Complete detection history  
✅ Date range filtering  
✅ Type filtering (Known/Unknown)  
✅ Search functionality  
✅ Export to CSV  
✅ Export to JSON  
✅ Sortable columns  
✅ Pagination  

#### **Gallery Page (`/gallery`)**
✅ Grid view of images  
✅ Type filtering  
✅ Date filtering  
✅ Lightbox viewer  
✅ Zoom controls  
✅ Download images  
✅ Delete images  
✅ Auto-refresh  

### **4. Training System**

#### **Data Collection**
✅ Person name input  
✅ Auto-capture (0.5s interval)  
✅ Manual capture  
✅ Target image count  
✅ Progress bar  
✅ Live preview  
✅ Instructions panel  

#### **Dataset Management**
✅ List all datasets  
✅ Show metadata  
✅ Status indicators  
✅ Delete datasets  
✅ View image count  
✅ Creation timestamp  

#### **Model Training**
✅ Custom model naming  
✅ Dataset selection  
✅ Training parameters  
✅ Background training  
✅ Real-time progress  
✅ Training metrics  
✅ Auto-annotation  

#### **Model Management**
✅ List trained models  
✅ Model metadata  
✅ Load/switch models  
✅ Delete models  
✅ Active indicator  
✅ Performance metrics  

### **5. Data Management**

#### **Image Storage**
✅ Auto-save detections  
✅ Full frame + crop  
✅ Organized folders  
✅ Duplicate prevention  
✅ Image hashing  
✅ Cooldown period  

#### **Detection Logs**
✅ JSON format  
✅ All detection data  
✅ Timestamps  
✅ Confidence scores  
✅ Image paths  
✅ Searchable  

#### **Training Data**
✅ Organized folders  
✅ Timestamp-based naming  
✅ Metadata tracking  
✅ Dataset status  

### **6. ESP32 Integration**

#### **ESP32-CAM**
✅ MJPEG stream support  
✅ Direct URL access  
✅ Auto-reconnect  
✅ Status monitoring  

#### **ESP32 Buzzer**
✅ HTTP alert endpoint  
✅ Multiple patterns  
✅ Alert cooldown  
✅ Status checking  

### **7. API Features**

✅ RESTful API  
✅ WebSocket streaming  
✅ JSON responses  
✅ Error handling  
✅ CORS support  
✅ 30+ endpoints  

### **8. Configuration**

✅ config.py settings  
✅ Adjustable thresholds  
✅ Camera URLs  
✅ File paths  
✅ Server settings  
✅ Logging levels  

---

## 📖 User Guide

### **Dashboard Usage**

#### **Starting Detection**

1. **Open Dashboard**
   ```
   http://localhost:8000
   ```

2. **Check Status**
   - System: Should show "Inactive"
   - ESP32-CAM: Green (online) or Red (offline)
   - Buzzer: Green (online) or Red (offline)

3. **Select Camera** (if needed)
   - Click camera dropdown
   - Select your camera
   - Video preview appears

4. **Start Detection**
   - Click "Start Detection"
   - System status → "Active"
   - Video shows with detection boxes

5. **Observe Detections**
   - **Yellow boxes:** Verifying (counting to 5)
   - **Green boxes:** KNOWN person
   - **Red boxes:** UNKNOWN person

#### **Understanding Detection States**

**Pending (Yellow):**
```
Person detected
Counting detections (1/5, 2/5, etc.)
Waiting for MIN_DETECTIONS
Not yet confirmed
```

**Known (Green):**
```
Confidence ≥ KNOWN_CONFIDENCE (0.92)
Detected MIN_DETECTIONS times
Face recognized
No alert sent
```

**Unknown (Red):**
```
Person detected MIN_DETECTIONS times
Confidence < KNOWN_CONFIDENCE
Face not recognized
Alert sent to buzzer
Image saved
```

#### **Switching Cameras**

1. **Stop detection** (if running)
2. **Click camera dropdown**
3. **Select new camera**
4. **Wait for video to refresh**
5. **Start detection again**

#### **Viewing Statistics**

Dashboard shows real-time stats:

- **Known Today:** Green box detections
- **Unknown Today:** Red box detections  
- **False Positives Blocked:** Duplicates prevented
- **Images Saved:** Total saved images

Updates automatically every 2 seconds.

#### **Recent Alerts**

Bottom section shows last 10 detections:
- Time and date
- Detection type
- Confidence percentage
- Color-coded (green = known, red = unknown)

Refreshes every 5 seconds.

### **Training System Usage**

Complete guide in [Training System](#training-system) section below.

### **Logs Page Usage**

#### **Viewing All Logs**

1. Navigate to `/logs`
2. See table of all detections
3. Columns:
   - ID (unique number)
   - Type (Known/Unknown)
   - Confidence (percentage)
   - Date
   - Time

#### **Filtering**

**By Type:**
```
1. Click "Type" dropdown
2. Select: All / Known / Unknown
3. Click "Filter"
4. Table updates
```

**By Date:**
```
1. Select start date
2. Select end date
3. Click "Filter"
4. Shows only dates in range
```

**By Search:**
```
1. Type in search box
2. Auto-filters as you type
3. Searches: date, time, type
```

#### **Sorting**

```
1. Click column header
2. Toggles ascending/descending
3. Can sort by any column
```

#### **Exporting**

**CSV Export:**
```
1. Filter/sort as desired
2. Click "Export CSV"
3. Downloads CSV file
4. Open in Excel/Sheets
```

**JSON Export:**
```
1. Click "Export JSON"
2. Downloads JSON file
3. Use for data processing
```

#### **Pagination**

```
- 50 results per page
- Click page numbers to navigate
- Shows total count
```

### **Gallery Page Usage**

#### **Viewing Images**

1. Go to `/gallery`
2. See grid of thumbnails
3. Each shows:
   - Preview image
   - Type badge (Known/Unknown)
   - Confidence score
   - Timestamp

#### **Filtering**

**By Type:**
```
Buttons: All | Known | Unknown
Click to filter instantly
```

**By Date:**
```
Date picker at top
Select date → Shows only that day
```

#### **Lightbox**

**Open:**
```
Click any thumbnail
Opens full-size in lightbox
```

**Navigate:**
```
← → arrows: Previous/Next
Zoom: + / - buttons
Close: X or ESC key
```

#### **Actions**

**Download:**
```
Hover over image
Click download icon
Saves to your computer
```

**Delete:**
```
Click trash icon
Confirms deletion
Removes from gallery
```

**Auto-Refresh:**
```
Toggle switch at top
Refreshes every 30s
New images appear automatically
```

---

## 🎓 Training System

### **Quick Training Guide**

#### **Step 1: Collect Data**

```
1. Go to /train
2. Select camera (Webcam or ESP32-CAM)
3. Enter person name: "James"
4. Target: 300 images
5. Click "Start Auto-Capture"
6. Move head around:
   - Left, right
   - Up, down
   - Different expressions
   - Closer, farther
7. Wait for auto-stop at 300
8. ✅ Dataset saved!
```

#### **Step 2: Collect Negatives**

```
1. Enter name: "negatives"
2. Target: 400 images
3. Click "Start Auto-Capture"
4. Point at:
   - Walls
   - Furniture
   - Objects
   - Other people
5. Wait for 400
6. ✅ Negatives saved!
```

#### **Step 3: Train Model**

```
1. Model name: "my_face_model"
2. Select datasets:
   ☑️ james_... (300)
   ☑️ negatives_... (400)
3. Epochs: 100
4. Batch: 16
5. Click "Start Training"
6. Wait 30-60 minutes
7. Watch progress bar
8. ✅ Training complete!
```

#### **Step 4: Load Model**

```
1. See model in "Trained Models"
2. Shows metadata:
   - Classes: James
   - Accuracy: 96.5%
   - Size: 6.2 MB
3. Click "Load Model"
4. ✅ Model active!
```

#### **Step 5: Test**

```
1. Go to dashboard
2. Click "Start Detection"
3. Stand in front of camera
4. See green box: "KNOWN: James"
5. ✅ Success!
```

### **Advanced Training**

#### **Multi-Person Training**

```
Collect:
- James: 300 images
- Mom: 300 images
- Dad: 300 images
- Negatives: 400 images

Train:
- Model: "family_model"
- Select all 4 datasets
- Epochs: 100

Result:
- Recognizes all 3 people! ✅
```

#### **Multi-Camera Training**

```
Problem: 
- Model trained on webcam
- Doesn't work on ESP32-CAM

Solution:
1. Collect James on Webcam: 300
2. Collect James on ESP32-CAM: 300
3. Train with both datasets
4. Works on BOTH cameras! ✅
```

### **Training Parameters**

**Epochs:**
- What: Training iterations
- Range: 50-200
- Recommended: 100
- More = better accuracy (diminishing returns)

**Batch Size:**
- What: Images per batch
- Options: 8, 16, 32
- Recommended: 16
- Lower = less RAM, slower
- Higher = faster, more RAM

**Image Size:**
- What: Input resolution
- Options: 416, 640, 1280
- Recommended: 640
- Higher = better accuracy, slower

### **Training Time**

**CPU:**
- 300 images, 100 epochs
- Intel i5: ~2 hours
- Intel i7: ~1 hour

**GPU:**
- 300 images, 100 epochs
- RTX 3060: ~10 minutes
- RTX 4090: ~5 minutes

### **Best Practices**

✅ **DO:**
- Collect 300+ images per person
- Vary angles and expressions
- Good, even lighting
- Include 400+ negatives
- Train on target camera

❌ **DON'T:**
- Stay in one position
- Same expression throughout
- Poor lighting
- Skip negatives
- Train on different camera

---

## 📡 API Documentation

### **Core Endpoints**

#### **System Status**

**GET /api/status**
```json
Response:
{
  "active": true,
  "esp32_cam_status": "online",
  "esp32_buzzer_status": "online",
  "detections_today": 45,
  "unknown_today": 3,
  "known_today": 42,
  "false_positives_blocked": 12,
  "images_saved": 33,
  "uptime": 3600
}
```

**POST /api/start**
```json
Response:
{
  "status": "started",
  "message": "Security system started successfully"
}
```

**POST /api/stop**
```json
Response:
{
  "status": "stopped",
  "message": "Security system stopped"
}
```

#### **Detection Data**

**GET /api/detections?limit=100&type_filter=unknown**
```json
Response:
[
  {
    "id": 0,
    "type": "unknown",
    "confidence": 0.95,
    "timestamp": "2025-11-29T15:30:45.123456",
    "date": "2025-11-29",
    "time": "15:30:45",
    "image_path": "security_images/unknown/full_20251129_153045.jpg"
  }
]
```

**GET /api/stream**

Returns: MJPEG video stream with detection overlays

#### **Camera Management**

**GET /api/cameras**
```json
Response:
[
  {
    "id": "webcam_0",
    "name": "Webcam (0)",
    "type": "webcam",
    "source": 0,
    "resolution": "1280x720"
  },
  {
    "id": "esp32-cam",
    "name": "ESP32-CAM",
    "type": "ip",
    "source": "http://192.168.1.100/stream",
    "resolution": "640x480"
  }
]
```

**POST /api/camera/select**
```json
Request:
{
  "camera_id": "esp32-cam"
}

Response:
{
  "status": "success",
  "camera": {...}
}
```

**GET /api/camera/current**

Returns currently selected camera

**POST /api/camera/add**
```json
Request:
{
  "name": "ESP32-CAM-2",
  "url": "http://192.168.1.102/stream"
}
```

### **Training Endpoints**

**POST /api/training/start-capture**
```json
Request:
{
  "person_name": "James",
  "camera_source": "esp32-cam",
  "auto": true,
  "target": 300
}

Response:
{
  "status": "started",
  "dataset": "james_20251129_143022",
  "target": 300
}
```

**POST /api/training/capture-frame**
```json
Response:
{
  "captured": 156,
  "target": 300,
  "complete": false
}
```

**GET /api/training/datasets**

Returns list of all collected datasets

**POST /api/training/start**
```json
Request:
{
  "model_name": "family_model",
  "datasets": [...],
  "epochs": 100,
  "batch": 16,
  "imgsz": 640
}
```

**GET /api/training/status**

Returns current training progress

**GET /api/training/models**

Returns list of all trained models

**POST /api/training/load-model**
```json
Request:
{
  "model_name": "family_model_v2"
}

Response:
{
  "status": "loaded",
  "model": "family_model_v2",
  "path": "models/family_model_v2/weights/best.pt"
}
```

---

## 🔍 Troubleshooting

### **Common Issues**

#### **1. No Video Feed**

**Symptoms:** Blank/black screen

**Solutions:**
```
✅ Check camera selection dropdown
✅ Verify camera permissions (browser + system)
✅ Test camera in other apps
✅ Restart server
✅ Refresh browser (F5)
```

#### **2. Not Recognized as KNOWN**

**Symptoms:** Red box instead of green

**Solutions:**
```
✅ Check model loaded (/train page)
✅ Lower KNOWN_CONFIDENCE to 0.85
✅ Check lighting (similar to training)
✅ Verify camera (same as training)
✅ Retrain with more images
✅ Add more variety to training data
```

#### **3. ESP32-CAM Offline**

**Symptoms:** Red status indicator

**Solutions:**
```
✅ Check power to ESP32-CAM
✅ Verify WiFi connection
✅ Ping IP: ping 192.168.1.100
✅ Test in browser: http://192.168.1.100/stream
✅ Restart ESP32-CAM
✅ Update IP in config.py
```

#### **4. Training Fails**

**Symptoms:** Error or crash during training

**Solutions:**
```
✅ Close other programs (free RAM)
✅ Reduce batch size to 8
✅ Reduce image size to 416
✅ Check disk space (need 5GB+)
✅ Verify datasets (50+ images each)
✅ Reduce epochs to 50
```

#### **5. High CPU Usage**

**Symptoms:** Computer slow, fan loud

**Solutions:**
```
✅ Stop detection when not needed
✅ Process fewer frames (edit code)
✅ Use GPU if available
✅ Close other programs
✅ Upgrade hardware
```

#### **6. Images Not Saving**

**Symptoms:** Gallery empty, saved count = 0

**Solutions:**
```
✅ Check SAVE_IMAGES = True in config.py
✅ Verify security_images/ folder exists
✅ Check folder permissions
✅ Verify detection is running
✅ Check confidence thresholds
✅ Wait 1+ hour between duplicate saves
```

### **Error Messages**

**"Failed to connect to stream"**
- Cause: Camera unreachable
- Fix: Check IP, network, restart camera

**"Model not found"**
- Cause: Wrong path in config.py
- Fix: Verify path, use absolute path

**"Camera already in use"**
- Cause: Another app using camera
- Fix: Close Zoom/Skype, restart computer

**"Out of memory"**
- Cause: Not enough RAM
- Fix: Reduce batch size, close programs

---

## ⚙️ Configuration

### **config.py Settings**

```python
# ===== ESP32 Configuration =====
ESP32_CAM_IP = "192.168.1.100"
ESP32_BUZZER_IP = "192.168.1.101"

# Auto-generated URLs (don't change)
ESP32_CAM_STREAM_URL = f"http://{ESP32_CAM_IP}/stream"
ESP32_BUZZER_ALERT_URL = f"http://{ESP32_BUZZER_IP}/alert"

# ===== Detection Thresholds =====
# Person detection confidence (0.0 - 1.0)
PERSON_CONFIDENCE = 0.75  # Recommended: 0.70-0.80

# Known face confidence (0.0 - 1.0)
KNOWN_CONFIDENCE = 0.92   # Recommended: 0.85-0.95

# Minimum detections before confirming
MIN_DETECTIONS = 5        # Recommended: 3-7

# ===== Face Recognition =====
# Path to trained model
FACE_RECOGNITION_MODEL = "./runs/face_detection/my_face_model5/weights/best.pt"

# ===== Image Storage =====
SAVE_IMAGES = True
IMAGES_DIR = "security_images"

# ===== Server Settings =====
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 8000
CORS_ORIGINS = ["*"]

# ===== Logging =====
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
```

### **Tuning Detection**

**For More Detections:**
```python
PERSON_CONFIDENCE = 0.70  # Lower threshold
MIN_DETECTIONS = 3        # Fewer verifications
```

**For Fewer False Positives:**
```python
PERSON_CONFIDENCE = 0.85  # Higher threshold
KNOWN_CONFIDENCE = 0.95   # Stricter matching
MIN_DETECTIONS = 7        # More verifications
```

**For Faster Response:**
```python
MIN_DETECTIONS = 3  # Quick confirmation
```

**For More Accuracy:**
```python
MIN_DETECTIONS = 10  # Thorough verification
```

### **Advanced Settings**

In `security_system_fastapi.py`:

```python
# Alert cooldown (seconds between alerts)
alert_cooldown = 30  # Default

# Duplicate detection
self.hash_similarity_threshold = 5  # Lower = stricter
self.save_cooldown_hours = 1        # Hours between saves

# Tracking
self.max_track_distance = 100  # Max pixels for same person
```

---

## 📁 File Structure

```
smart-security-system/
│
├── main.py                      # FastAPI server
├── security_system_fastapi.py   # Detection engine
├── camera_manager.py            # Camera handling
├── training_manager.py          # Training system
├── config.py                    # Configuration
├── requirements.txt             # Dependencies
├── README.md                    # This file
│
├── templates/                   # HTML pages
│   ├── index.html              # Dashboard
│   ├── training.html           # Training page
│   ├── logs.html               # Logs page
│   └── gallery.html            # Gallery page
│
├── static/                      # JavaScript
│   └── training.js             # Training page JS
│
├── security_images/             # Saved detections
│   ├── known/
│   │   ├── full_*.jpg          # Full frame images
│   │   └── crop_*.jpg          # Face crops
│   └── unknown/
│       ├── full_*.jpg
│       └── crop_*.jpg
│
├── training_data/               # Training datasets
│   ├── james_webcam_20251129/
│   │   └── img_*.jpg
│   ├── mom_esp32cam_20251129/
│   └── metadata.json
│
├── models/                      # Trained models
│   ├── family_model_v2/
│   │   ├── weights/
│   │   │   └── best.pt
│   │   ├── metadata.json
│   │   └── results.csv
│   └── my_face_model6/
│
├── security_log.json            # Detection history
│
└── runs/                        # YOLO training runs
    └── detect/
```

---

## 🎯 Use Cases

### **Home Security**

```
Setup:
- ESP32-CAM at front door
- Train family members
- Enable alerts

Result:
- Family = Green boxes (no alert)
- Strangers = Red boxes + buzzer alert
- All activity logged
- Images saved
```

### **Office Access Control**

```
Setup:
- Webcam at entrance
- Train all employees
- Monitor dashboard

Result:
- Employees recognized
- Visitors flagged
- Complete attendance log
- Security images saved
```

### **Retail Analytics**

```
Setup:
- Multiple cameras
- Train regular customers
- Track visits

Result:
- Identify VIP customers
- Track visit frequency
- Unknown customer alerts
- Analytics data
```

### **Smart Home**

```
Setup:
- ESP32-CAM network
- Family training
- IoT integration

Result:
- Person-specific automation
- Security monitoring
- Activity logging
- Smart alerts
```

---

## 🔒 Security Considerations

### **Privacy**

- **Local Processing:** All data stays on your network
- **No Cloud:** No external servers
- **User Control:** You own all images and data
- **Deletion:** Easy to delete logs and images

### **Access Control**

- **Network Isolation:** Keep on private network
- **Port Security:** Close port 8000 to internet
- **Authentication:** Add login system if exposing
- **HTTPS:** Use reverse proxy with SSL

### **Data Protection**

- **Encryption:** Encrypt stored images
- **Backups:** Regular backup of models/data
- **Retention:** Auto-delete old images
- **Compliance:** Follow local privacy laws

---

## 🚀 Performance Optimization

### **Speed Up Detection**

```python
# Process fewer frames
# In security_system_fastapi.py:
if frame_number % 10 == 0:  # Instead of % 5
    processed_frame = self.process_frame(frame, frame_number)
```

### **Reduce RAM Usage**

```python
# Lower batch size during training
batch = 8  # Instead of 16

# Smaller image size
imgsz = 416  # Instead of 640
```

### **GPU Acceleration**

```bash
# Install CUDA version
pip install ultralytics[gpu]

# Automatically uses GPU if available
```

### **Optimize Storage**

```python
# Reduce image quality
cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

# Auto-cleanup old images
# Add to config.py:
AUTO_DELETE_DAYS = 30  # Delete images older than 30 days
```

---

## 🔄 Updating

### **Update Dependencies**

```bash
pip install --upgrade -r requirements.txt
```

### **Update Code**

```bash
git pull origin main
```

### **Migrate Data**

```bash
# Backup before updating
cp -r security_images/ backup/
cp -r models/ backup/
cp security_log.json backup/

# Update
git pull

# Restore if needed
```

---

## 🤝 Contributing

We welcome contributions!

### **How to Contribute**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### **Development Setup**

```bash
# Clone your fork
git clone https://github.com/yourusername/smart-security-system.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start development server
python main.py
```

### **Code Style**

- Follow PEP 8
- Add docstrings
- Comment complex logic
- Write tests for new features

---

## 📄 License

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 🙏 Acknowledgments

- **Ultralytics** - YOLOv8 framework
- **FastAPI** - Modern web framework
- **OpenCV** - Computer vision library
- **ESP32 Community** - Hardware support

---

## 📞 Support

### **Documentation**

- **README:** This file
- **API Docs:** See API Documentation section
- **Training Guide:** See Training System section

### **Getting Help**

- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Email:** support@example.com

### **FAQ**

**Q: Can I use multiple ESP32-CAMs?**  
A: Yes! Add each via training page camera management.

**Q: Does it work offline?**  
A: Yes, no internet required after installation.

**Q: Can I train on mobile?**  
A: No, training requires desktop/server.

**Q: Is GPU required?**  
A: No, but recommended for faster training.

**Q: How many people can it recognize?**  
A: Unlimited, but performance decreases beyond 50+ people.

**Q: Can I use Raspberry Pi?**  
A: Possible but very slow. Desktop PC recommended.

**Q: What cameras are supported?**  
A: Webcams, ESP32-CAM, any IP camera with MJPEG stream.

**Q: How accurate is it?**  
A: 90-98% with proper training (300+ images).

**Q: Can it work in the dark?**  
A: No, requires visible light. Use IR camera for night vision.

**Q: Is it secure?**  
A: Yes, all processing is local. No cloud connection.

---
### **Next Steps**

1. **Train your model** - Collect 300+ images
2. **Test detection** - Verify accuracy
3. **Deploy** - Set up cameras
4. **Monitor** - Watch dashboard
5. **Enjoy** - Secure and automated! 🛡️

### **Quick Links**

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Training Guide](#training-system)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)

---

**Version:** 1.0.0  
**Last Updated:** November 29, 2025  
