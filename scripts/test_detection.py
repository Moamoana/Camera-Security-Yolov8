"""
Quick Detection Test Script
Tests if face detection is working properly
"""

import cv2
from ultralytics import YOLO
import os

print("="*70)
print("DETECTION TEST SCRIPT")
print("="*70)

# Test 1: Check model file exists
print("\n[Test 1] Checking face model file...")
model_path = r".\runs\face_detection\my_face_model5\weights\best.pt"
if os.path.exists(model_path):
    print(f"✅ Model file found: {model_path}")
else:
    print(f"❌ Model NOT found: {model_path}")
    print("\nPlease check the path!")
    exit(1)

# Test 2: Load models
print("\n[Test 2] Loading YOLO models...")
try:
    person_detector = YOLO('yolov8n.pt')
    print("✅ Person detector loaded (yolov8n.pt)")
except Exception as e:
    print(f"❌ Failed to load person detector: {e}")
    exit(1)

try:
    face_recognizer = YOLO(model_path)
    print(f"✅ Face model loaded: {model_path}")
except Exception as e:
    print(f"❌ Failed to load face model: {e}")
    exit(1)

# Test 3: Connect to ESP32-CAM
print("\n[Test 3] Connecting to ESP32-CAM...")
esp32_cam_url = "http://192.168.1.100/stream"
print(f"Connecting to: {esp32_cam_url}")

cap = cv2.VideoCapture(esp32_cam_url)
if cap.isOpened():
    print("✅ Connected to ESP32-CAM")
else:
    print("❌ Failed to connect to ESP32-CAM")
    print("\nTrying webcam instead (index 0)...")
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("✅ Using webcam")
    else:
        print("❌ No camera available")
        exit(1)

# Test 4: Read and test detection
print("\n[Test 4] Testing detection...")
print("Press 'q' to quit")
print("\nLook at the camera and watch for:")
print("  - Yellow box = Person detected, verifying...")
print("  - Green box = KNOWN person (you!)")
print("  - Red box = UNKNOWN person")
print("-"*70)

frame_count = 0
detections = 0

PERSON_CONF = 0.75
KNOWN_CONF = 0.92

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame")
        break
    
    frame_count += 1
    
    # Detect person
    person_results = person_detector(frame, classes=[0], conf=PERSON_CONF, verbose=False)
    
    for person_box in person_results[0].boxes:
        detections += 1
        x1, y1, x2, y2 = map(int, person_box.xyxy[0])
        person_conf = float(person_box.conf[0])
        
        # Draw person box (yellow)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(frame, f"PERSON: {person_conf:.2f}", (x1, y1-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Test face recognition
        person_crop = frame[y1:y2, x1:x2]
        if person_crop.size > 0:
            face_results = face_recognizer(person_crop, conf=KNOWN_CONF, verbose=False)
            
            if len(face_results[0].boxes) > 0:
                # KNOWN!
                face_conf = float(face_results[0].boxes[0].conf[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.putText(frame, f"KNOWN: {face_conf:.2f}", (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                print(f"✅ Frame {frame_count}: KNOWN person detected (conf: {face_conf:.2f})")
            else:
                # UNKNOWN
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                cv2.putText(frame, f"UNKNOWN: {person_conf:.2f}", (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                print(f"❌ Frame {frame_count}: UNKNOWN person (conf: {person_conf:.2f})")
    
    # Show info
    info_text = f"Frame: {frame_count} | Detections: {detections} | Person Conf: {PERSON_CONF} | Known Conf: {KNOWN_CONF}"
    cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Display
    cv2.imshow('Detection Test', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print(f"Total frames: {frame_count}")
print(f"Total person detections: {detections}")
print("\nDid you see yourself as GREEN (KNOWN)?")
print("  - YES → Face model works! Issue might be in FastAPI")
print("  - NO → Face model needs retraining or confidence adjustment")
print("="*70)