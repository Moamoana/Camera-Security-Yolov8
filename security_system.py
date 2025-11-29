"""
Security System with FastAPI Integration
Reads from ESP32-CAM, sends alerts to ESP32 Buzzer
"""

from ultralytics import YOLO
import cv2
from datetime import datetime, timedelta
import json
import os
import numpy as np
import imagehash
from PIL import Image
import requests
from threading import Thread, Event
import time
import logging

logger = logging.getLogger(__name__)

class SecuritySystem:
    def __init__(
        self,
        esp32_cam_url,
        esp32_buzzer_url,
        face_model_path,
        person_conf=0.75,
        known_conf=0.92,
        min_detections=5,
        save_images=True,
        images_dir='security_images',
        alert_cooldown=30,
        camera_manager=None
    ):
        """
        Initialize security system with ESP32 integration
        
        Args:
            esp32_cam_url: URL to ESP32-CAM stream
            esp32_buzzer_url: URL to ESP32 buzzer alert endpoint
            face_model_path: Path to trained face recognition model
            person_conf: Person detection confidence threshold
            known_conf: Known person confidence threshold
            min_detections: Minimum detections before confirming
            save_images: Whether to save detection images
            images_dir: Directory to save images
            alert_cooldown: Seconds between alerts
            camera_manager: CameraManager instance for camera access
        """
        
        logger.info("Initializing Security System...")
        
        self.esp32_cam_url = esp32_cam_url
        self.esp32_buzzer_url = esp32_buzzer_url
        self.camera_manager = camera_manager
        
        logger.info("Loading YOLO models...")
        self.person_detector = YOLO('yolov8n.pt')
        self.face_recognizer = None
        
        if face_model_path and os.path.exists(face_model_path):
            self.face_recognizer = YOLO(face_model_path)
            logger.info(f"Face model loaded: {face_model_path}")
        else:
            logger.warning(f"Face model not found: {face_model_path}")
        
        # Settings
        self.person_conf = person_conf
        self.known_conf = known_conf
        self.min_detections = min_detections
        self.save_images = save_images
        self.images_dir = images_dir
        self.alert_cooldown = alert_cooldown
        
        os.makedirs(f"{images_dir}/unknown", exist_ok=True)
        os.makedirs(f"{images_dir}/known", exist_ok=True)
        
        self.tracked_persons = {}
        self.next_track_id = 0
        self.max_track_distance = 100
        self.face_cache = {}
        self.saved_hashes = {}
        self.hash_similarity_threshold = 5
        self.save_cooldown_hours = 1
        self.stats = {
            'total_detections': 0,
            'known_detections': 0,
            'unknown_detections': 0,
            'false_positives_blocked': 0,
            'images_saved': 0,
            'alerts_sent': 0,
            'uptime': 0
        }
        self.log_file = 'security_log.json'
        self.detections = self.load_log()
        self.last_alert_time = {}
        self.stream = None
        self.running = False
        self.stop_event = Event()
        self.current_frame = None
        self.start_time = time.time()
        
        logger.info("Security System initialized successfully")
    
    def load_log(self):
        """Load detection log"""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_log(self):
        """Save detection log"""
        with open(self.log_file, 'w') as f:
            json.dump(self.detections, f, indent=2)
    
    def log_detection(self, detection_type, confidence, timestamp, image_path=None):
        """Log a detection"""
        detection = {
            'id': len(self.detections),
            'type': detection_type,
            'confidence': float(confidence),
            'timestamp': timestamp.isoformat(),
            'date': timestamp.strftime('%Y-%m-%d'),
            'time': timestamp.strftime('%H:%M:%S'),
            'image_path': image_path
        }
        
        self.detections.append(detection)
        self.save_log()
        self.stats['total_detections'] += 1
        if detection_type == 'known':
            self.stats['known_detections'] += 1
        else:
            self.stats['unknown_detections'] += 1
    
    def connect_to_stream(self):
        """Connect to camera stream via camera manager"""
        if self.camera_manager and self.camera_manager.current_camera:
            logger.info("Using camera manager for stream")
            return True
        logger.info(f"Connecting to ESP32-CAM: {self.esp32_cam_url}")
        
        try:
            self.stream = cv2.VideoCapture(self.esp32_cam_url)
            
            if self.stream.isOpened():
                logger.info("Successfully connected to ESP32-CAM")
                return True
            else:
                logger.error("Failed to connect to ESP32-CAM")
                return False
        except Exception as e:
            logger.error(f"Error connecting to ESP32-CAM: {e}")
            return False
    
    def send_alert_to_buzzer(self, pattern=1):
        """Send alert to ESP32 buzzer"""
        try:
            url = f"{self.esp32_buzzer_url}?pattern={pattern}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"Alert sent to buzzer (pattern {pattern})")
                self.stats['alerts_sent'] += 1
                return True
            else:
                logger.error(f"Buzzer alert failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending alert to buzzer: {e}")
            return False
    
    def compute_face_hash(self, face_crop):
        """Compute perceptual hash of face"""
        try:
            face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(face_rgb)
            face_hash = imagehash.phash(pil_image)
            return face_hash
        except:
            return None
    
    def is_duplicate_face(self, face_hash):
        """Check if face was already saved recently"""
        if face_hash is None:
            return False, None
        
        now = datetime.now()
        hash_str = str(face_hash)
        
        for saved_hash_str, info in list(self.saved_hashes.items()):
            saved_hash = imagehash.hex_to_hash(saved_hash_str)
            distance = face_hash - saved_hash
            
            if distance <= self.hash_similarity_threshold:
                time_since = now - info['timestamp']
                hours_since = time_since.total_seconds() / 3600
                
                if hours_since < self.save_cooldown_hours:
                    return True, time_since
                else:
                    del self.saved_hashes[saved_hash_str]
                    return False, time_since
        
        return False, None
    
    def add_face_hash(self, face_hash, track_id, person_type):
        """Add face hash to saved hashes"""
        if face_hash is not None:
            hash_str = str(face_hash)
            self.saved_hashes[hash_str] = {
                'timestamp': datetime.now(),
                'track_id': track_id,
                'person_type': person_type
            }
    
    def save_detection_image(self, frame, person_info, person_type):
        """Save detection image"""
        if not self.save_images:
            return None
        
        x1, y1, x2, y2 = person_info['bbox']
        face_crop = frame[y1:y2, x1:x2]
        
        if face_crop.size == 0:
            return None
        face_hash = self.compute_face_hash(face_crop)
        is_duplicate, time_since = self.is_duplicate_face(face_hash)
        
        if is_duplicate:
            minutes_ago = time_since.total_seconds() / 60
            logger.info(f"Skipping save: Same person detected {minutes_ago:.1f} min ago")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        subfolder = 'unknown' if person_type == 'unknown' else 'known'
        full_frame_path = os.path.join(self.images_dir, subfolder, f'full_{timestamp}.jpg')
        annotated = frame.copy()
        color = (0, 0, 255) if person_type == 'unknown' else (0, 255, 0)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
        
        label = f"{person_type.upper()}: {person_info['confidence']:.2f}"
        cv2.putText(annotated, label, (x1, y1 - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        timestamp_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(annotated, timestamp_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imwrite(full_frame_path, annotated)
        
        crop_path = os.path.join(self.images_dir, subfolder, f'crop_{timestamp}.jpg')
        if face_crop.size > 0:
            cv2.imwrite(crop_path, face_crop)
        
        self.add_face_hash(face_hash, person_info['track_id'], person_type)
        
        self.stats['images_saved'] += 1
        logger.info(f"Image saved: {full_frame_path}")
        
        return full_frame_path
    
    def calculate_iou(self, box1, box2):
        """Calculate IoU between two boxes"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
            return 0.0
        
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    def match_detection_to_track(self, bbox, frame_number):
        """Match detection to existing track"""
        best_match_id = None
        best_iou = 0.4
        
        for track_id, track_info in self.tracked_persons.items():
            if frame_number - track_info['last_seen'] > 30:
                continue
            
            iou = self.calculate_iou(bbox, track_info['bbox'])
            if iou > best_iou:
                best_iou = iou
                best_match_id = track_id
        
        return best_match_id
    
    def detect_and_classify(self, frame, frame_number):
        """Detect and classify persons"""
        detected_persons = []
        confirmed_persons = []
        person_results = self.person_detector(frame, classes=[0], conf=self.person_conf, verbose=False)
        frame_height, frame_width = frame.shape[:2]
        min_person_area = (frame_width * frame_height) * 0.02
        persons_to_check = []
        
        for person_box in person_results[0].boxes:
            x1, y1, x2, y2 = map(int, person_box.xyxy[0])
            person_conf = float(person_box.conf[0])
            
            bbox_area = (x2 - x1) * (y2 - y1)
            if bbox_area < min_person_area:
                self.stats['false_positives_blocked'] += 1
                continue
            
            person_crop = frame[y1:y2, x1:x2]
            if person_crop.size == 0:
                continue
            
            bbox = (x1, y1, x2, y2)
            track_id = self.match_detection_to_track(bbox, frame_number)
            
            if track_id is None:
                track_id = self.next_track_id
                self.next_track_id += 1
                self.tracked_persons[track_id] = {
                    'count': 1,
                    'is_known': False,
                    'bbox': bbox,
                    'last_seen': frame_number,
                    'alerted': False
                }
                self.face_cache[track_id] = {
                    'is_known': False,
                    'confidence': 0.0,
                    'checked': False
                }
            else:
                self.tracked_persons[track_id]['count'] += 1
                self.tracked_persons[track_id]['bbox'] = bbox
                self.tracked_persons[track_id]['last_seen'] = frame_number
            
            track_info = self.tracked_persons[track_id]
            
            if track_info['count'] >= self.min_detections:
                if not self.face_cache[track_id]['checked']:
                    persons_to_check.append((track_id, person_crop, bbox, person_conf))
        
        if persons_to_check and self.face_recognizer is not None:
            for track_id, person_crop, bbox, person_conf in persons_to_check:
                face_results = self.face_recognizer(person_crop, conf=self.known_conf, verbose=False)
                
                is_known = False
                known_conf = 0.0
                
                if len(face_results[0].boxes) > 0:
                    is_known = True
                    known_conf = float(face_results[0].boxes[0].conf[0])
                
                self.face_cache[track_id] = {
                    'is_known': is_known,
                    'confidence': known_conf if is_known else person_conf,
                    'checked': True
                }
                
                self.tracked_persons[track_id]['is_known'] = is_known
        
        for person_box in person_results[0].boxes:
            x1, y1, x2, y2 = map(int, person_box.xyxy[0])
            person_conf = float(person_box.conf[0])
            
            bbox_area = (x2 - x1) * (y2 - y1)
            if bbox_area < min_person_area:
                continue
            
            bbox = (x1, y1, x2, y2)
            track_id = self.match_detection_to_track(bbox, frame_number)
            
            if track_id is None:
                continue
            
            track_info = self.tracked_persons[track_id]
            face_info = self.face_cache.get(track_id, {'is_known': False, 'confidence': 0.0, 'checked': False})
            
            if track_info['count'] >= self.min_detections:
                person_info = {
                    'bbox': bbox,
                    'is_known': face_info['is_known'],
                    'confidence': face_info['confidence'],
                    'type': 'known' if face_info['is_known'] else 'unknown',
                    'track_id': track_id,
                    'detection_count': track_info['count']
                }
                detected_persons.append(person_info)
                
                if not track_info['alerted']:
                    confirmed_persons.append(person_info)
                    track_info['alerted'] = True
            else:
                person_info = {
                    'bbox': bbox,
                    'is_pending': True,
                    'detection_count': track_info['count'],
                    'required': self.min_detections
                }
                detected_persons.append(person_info)
        
        return detected_persons, confirmed_persons
    
    def process_frame(self, frame, frame_number):
        """Process single frame"""
        detected_persons, confirmed_persons = self.detect_and_classify(frame, frame_number)
        annotated = frame.copy()
        
        for person in detected_persons:
            if person.get('is_pending'):
                x1, y1, x2, y2 = person['bbox']
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 255), 2)
                label = f"VERIFYING {person['detection_count']}/{person['required']}"
                cv2.putText(annotated, label, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            else:
                x1, y1, x2, y2 = person['bbox']
                color = (0, 255, 0) if person['is_known'] else (0, 0, 255)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
                
                label = f"{'KNOWN' if person['is_known'] else 'UNKNOWN'}: {person['confidence']:.2f}"
                cv2.putText(annotated, label, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        current_time = datetime.now()
        for person in confirmed_persons:
            track_id = person['track_id']
            
            if track_id in self.last_alert_time:
                time_since_alert = (current_time - self.last_alert_time[track_id]).total_seconds()
                if time_since_alert < self.alert_cooldown:
                    continue
                
            image_path = None
            if self.save_images:
                image_path = self.save_detection_image(annotated, person, person['type'])
                
            self.log_detection(person['type'], person['confidence'], current_time, image_path)
            
            if not person['is_known']:
                logger.warning(f"UNKNOWN PERSON DETECTED! Confidence: {person['confidence']:.2f}")
                self.send_alert_to_buzzer(pattern=1)
                self.last_alert_time[track_id] = current_time
        
        self.current_frame = annotated
        return annotated
    
    def start(self):
        """Start security monitoring"""
        if not self.connect_to_stream():
            logger.error("Failed to connect to stream")
            return
        
        self.running = True
        self.stop_event.clear()
        
        frame_number = 0
        
        logger.info("Security monitoring started")
        
        while self.running and not self.stop_event.is_set():
            if self.camera_manager and self.camera_manager.current_camera:
                ret, frame = self.camera_manager.read_frame()
            elif self.stream:
                ret, frame = self.stream.read()
            else:
                ret = False
                frame = None
            
            if not ret or frame is None:
                logger.warning("Failed to read frame, attempting reconnect...")
                time.sleep(5)
                self.connect_to_stream()
                continue
            
            frame_number += 1
            if frame_number % 5 == 0:
                processed_frame = self.process_frame(frame, frame_number)
                self.current_frame = processed_frame
            else:
                self.current_frame = frame
            
            self.stats['uptime'] = int(time.time() - self.start_time)
        
        logger.info("Security monitoring stopped")
        
        if self.stream:
            self.stream.release()
    
    def stop(self):
        """Stop security monitoring"""
        self.running = False
        self.stop_event.set()
    
    def get_frame_stream(self):
        """Generator for frame streaming"""
        while self.running:
            if self.current_frame is not None:
                yield self.current_frame.copy()
            else:
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                yield blank
            time.sleep(0.033)
    
    def get_stats(self):
        """Get statistics"""
        return self.stats.copy()
    
    def get_24h_stats(self):
        """Get 24-hour statistics"""
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        
        unknown = 0
        known = 0
        
        for detection in self.detections:
            try:
                det_time = datetime.fromisoformat(detection['timestamp'])
                if det_time > cutoff:
                    if detection['type'] == 'unknown':
                        unknown += 1
                    else:
                        known += 1
            except:
                continue
        
        return {'unknown': unknown, 'known': known, 'total': unknown + known}
    
    def get_detections(self, limit=100, type_filter=None):
        """Get detection history"""
        detections = self.detections
        
        if type_filter:
            detections = [d for d in detections if d['type'] == type_filter]
        
        return list(reversed(detections[-limit:]))
    
    def get_detection_by_id(self, detection_id):
        """Get specific detection"""
        for detection in self.detections:
            if detection['id'] == detection_id:
                return detection
        return None
    
    def get_detailed_stats(self):
        """Get detailed statistics"""
        stats_24h = self.get_24h_stats()
        
        return {
            **self.stats,
            'unknown_24h': stats_24h['unknown'],
            'known_24h': stats_24h['known'],
            'total_24h': stats_24h['total'],
            'total_logged': len(self.detections)
        }