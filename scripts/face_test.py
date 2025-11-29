"""
Simple Face Detection Test
Tests your face model with regular webcam first
"""

import cv2
from ultralytics import YOLO
import os
import sys

print("="*70)
print("SIMPLE FACE DETECTION TEST")
print("="*70)

# Settings (matching your command)
PERSON_CONF = 0.75
KNOWN_CONF = 0.92
MIN_DETECTIONS = 5

# Check model file
model_path = r".\runs\face_detection\my_face_model5\weights\best.pt"
print(f"\n[1] Checking face model...")
print(f"    Path: {model_path}")

if not os.path.exists(model_path):
    print(f"    ❌ ERROR: Model file not found!")
    print(f"\n    Please check the path. Current directory:")
    print(f"    {os.getcwd()}")
    input("\nPress Enter to exit...")
    sys.exit(1)
else:
    print(f"    ✅ Model file found!")

# Load models
print(f"\n[2] Loading YOLO models...")
try:
    print("    Loading person detector...")
    person_detector = YOLO('yolov8n.pt')
    print("    ✅ Person detector loaded")
except Exception as e:
    print(f"    ❌ ERROR: {e}")
    input("\nPress Enter to exit...")
    sys.exit(1)

try:
    print(f"    Loading face model...")
    face_recognizer = YOLO(model_path)
    print(f"    ✅ Face model loaded")
except Exception as e:
    print(f"    ❌ ERROR: {e}")
    input("\nPress Enter to exit...")
    sys.exit(1)

# Try webcam first (simpler)
print(f"\n[3] Opening camera...")
print(f"    Trying webcam (index 0)...")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print(f"    ❌ Webcam failed, trying index 1...")
    cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print(f"    ❌ Webcam failed, trying ESP32-CAM...")
    cap = cv2.VideoCapture("http://192.168.1.100/stream")

if not cap.isOpened():
    print(f"    ❌ ERROR: No camera available!")
    input("\nPress Enter to exit...")
    sys.exit(1)

print(f"    ✅ Camera opened successfully!")

# Get camera info
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"    Resolution: {width}x{height}")

print(f"\n[4] Starting detection...")
print(f"    Person confidence: {PERSON_CONF}")
print(f"    Known confidence: {KNOWN_CONF}")
print(f"    Min detections: {MIN_DETECTIONS}")
print(f"\n{'='*70}")
print("INSTRUCTIONS:")
print("  - Stand in front of camera")
print("  - Wait for detection")
print("  - Green box = KNOWN (you!)")
print("  - Red box = UNKNOWN")
print("  - Yellow box = Verifying...")
print("  - Press 'q' to quit")
print("="*70)

detection_count = {}
frame_number = 0
known_detections = 0
unknown_detections = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("\n❌ Failed to read frame!")
            break
        
        frame_number += 1
        
        # Detect persons
        person_results = person_detector(frame, classes=[0], conf=PERSON_CONF, verbose=False)
        
        detected_this_frame = []
        
        for idx, person_box in enumerate(person_results[0].boxes):
            x1, y1, x2, y2 = map(int, person_box.xyxy[0])
            person_conf = float(person_box.conf[0])
            
            # Track detections
            track_id = f"person_{idx}"
            if track_id not in detection_count:
                detection_count[track_id] = 0
            detection_count[track_id] += 1
            
            current_count = detection_count[track_id]
            detected_this_frame.append(track_id)
            
            # Crop person
            person_crop = frame[y1:y2, x1:x2]
            
            if current_count < MIN_DETECTIONS:
                # Still verifying - Yellow box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                label = f"VERIFYING {current_count}/{MIN_DETECTIONS}"
                cv2.putText(frame, label, (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                # Check face
                is_known = False
                face_conf = 0.0
                
                if person_crop.size > 0:
                    face_results = face_recognizer(person_crop, conf=KNOWN_CONF, verbose=False)
                    
                    if len(face_results[0].boxes) > 0:
                        is_known = True
                        face_conf = float(face_results[0].boxes[0].conf[0])
                
                if is_known:
                    # KNOWN - Green box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    label = f"KNOWN: {face_conf:.2f}"
                    cv2.putText(frame, label, (x1, y1-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    known_detections += 1
                    print(f"✅ Frame {frame_number}: KNOWN person! (confidence: {face_conf:.2f})")
                else:
                    # UNKNOWN - Red box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    label = f"UNKNOWN: {person_conf:.2f}"
                    cv2.putText(frame, label, (x1, y1-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                    unknown_detections += 1
                    print(f"❌ Frame {frame_number}: UNKNOWN person (person conf: {person_conf:.2f})")
        
        # Clean up old tracks
        for track_id in list(detection_count.keys()):
            if track_id not in detected_this_frame:
                del detection_count[track_id]
        
        # Show stats
        stats = f"Frame: {frame_number} | Known: {known_detections} | Unknown: {unknown_detections}"
        cv2.putText(frame, stats, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Display
        cv2.imshow('Face Detection Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\n\nStopped by user")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print(f"Total frames: {frame_number}")
    print(f"Known detections: {known_detections}")
    print(f"Unknown detections: {unknown_detections}")
    print("="*70)
    
    if known_detections > 0:
        print("\n✅ SUCCESS! Face model is working!")
        print("   Your face was detected as KNOWN")
    elif unknown_detections > 0:
        print("\n⚠️  Face model loaded but not recognizing you")
        print("   Possible fixes:")
        print("   1. Lower KNOWN_CONF from 0.92 to 0.85")
        print("   2. Retrain model with more images")
        print("   3. Check lighting conditions")
    else:
        print("\n❌ No person detected at all")
        print("   Possible fixes:")
        print("   1. Lower PERSON_CONF from 0.75 to 0.65")
        print("   2. Move closer to camera")
        print("   3. Check camera is working")
    
    input("\nPress Enter to exit...")