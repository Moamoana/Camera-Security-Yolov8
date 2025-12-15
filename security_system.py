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
import asyncio
from collections import defaultdict

try:
    import config_new as config
except:
    import config

logger = logging.getLogger(__name__)

class SecuritySystem:
    def __init__(
        self,
        face_recognizer=None,
        telegram_notifier=None,
        image_manager=None,
        ws_handler=None,
        camera_manager=None
    ):
        logger.info("Initializing Security System...")
        
        self.face_recognizer = face_recognizer
        self.telegram_notifier = telegram_notifier
        self.image_manager = image_manager
        self.ws_handler = ws_handler
        self.camera_manager = camera_manager
        
        logger.info("Loading YOLO person detector...")
        self.person_detector = YOLO(getattr(config, 'PERSON_DETECTOR_MODEL', 'yolov8n.pt'))
        
        self.person_conf = getattr(config, 'PERSON_CONFIDENCE', 0.75)
        self.min_detections = getattr(config, 'MIN_DETECTIONS', 5)
        self.save_images = getattr(config, 'SAVE_IMAGES', True)
        self.alert_cooldown = getattr(config, 'ALERT_COOLDOWN', 30)
        
        camera_mode = getattr(config, 'CAMERA_MODE', 'http_stream')
        camera_id = getattr(config, 'DEFAULT_CAMERA_ID', 'esp32_cam_01')
        
        from websocket_handler import FrameReader
        self.frame_reader = FrameReader(
            mode=camera_mode,
            websocket_handler=ws_handler,
            http_url=getattr(config, 'ESP32_CAM_STREAM_URL', '') if camera_mode == "http_stream" else None
        )
        self.camera_id = camera_id
        
        self.tracked_persons = {}
        self.next_track_id = 0
        self.max_track_distance = getattr(config, 'TRACK_MAX_DISTANCE', 100)
        self.face_cache = {}
        self.saved_hashes = {}
        self.hash_similarity_threshold = getattr(config, 'HASH_SIMILARITY_THRESHOLD', 5)
        self.save_cooldown_hours = getattr(config, 'DUPLICATE_COOLDOWN_HOURS', 1)
        
        self.stats = {
            'total_detections': 0,
            'known_detections': 0,
            'unknown_detections': 0,
            'false_positives_blocked': 0,
            'images_saved': 0,
            'alerts_sent': 0,
            'uptime': 0,
            'frames_processed': 0
        }
        
        self.log_file = getattr(config, 'LOGS_FILE', 'security_log.json')
        self.detections = self.load_log()
        self.last_alert_time = {}
        self.running = False
        self.stop_event = Event()
        self.current_frame = None
        self.start_time = time.time()
        self.frame_count = 0
        self.detection_counts = defaultdict(int)
        
        logger.info("Security System initialized successfully")
    
    def load_log(self):
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_log(self):
        max_entries = getattr(config, 'MAX_LOG_ENTRIES', 1000)
        if len(self.detections) > max_entries:
            self.detections = self.detections[-max_entries:]
        
        with open(self.log_file, 'w') as f:
            json.dump(self.detections, f, indent=2)
    
    def log_detection(self, detection_type, confidence, timestamp, image_path=None):
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
        
        if len(self.detections) % 10 == 0:
            self.save_log()
        
        self.stats['total_detections'] += 1
        if detection_type == 'known':
            self.stats['known_detections'] += 1
        else:
            self.stats['unknown_detections'] += 1
    
    def send_alert_to_buzzer(self, pattern=1):
        if not getattr(config, 'ENABLE_BUZZER_ALERTS', True):
            return False
        
        try:
            buzzer_url = getattr(config, 'ESP32_BUZZER_ALERT_URL', '')
            if not buzzer_url:
                return False
            
            url = f"{buzzer_url}?pattern={pattern}"
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
        try:
            face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(face_rgb)
            face_hash = imagehash.phash(pil_image)
            return face_hash
        except:
            return None
    
    def is_duplicate_face(self, face_hash):
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
        if face_hash is not None:
            hash_str = str(face_hash)
            self.saved_hashes[hash_str] = {
                'timestamp': datetime.now(),
                'track_id': track_id,
                'type': person_type
            }
    
    def save_detection_image(self, frame, person_info, person_type):
        if not self.save_images:
            return None
        
        x1, y1, x2, y2 = person_info['bbox']
        person_crop = frame[y1:y2, x1:x2]
        
        face_hash = self.compute_face_hash(person_crop)
        is_duplicate, time_since = self.is_duplicate_face(face_hash)
        
        if is_duplicate:
            logger.info(f"Skipping duplicate {person_type} face (seen {time_since} ago)")
            self.stats['false_positives_blocked'] += 1
            return None
        
        if self.image_manager:
            saved_path = self.image_manager.save_image(
                frame,
                person_type=person_type,
                metadata={
                    'confidence': person_info.get('confidence', 0.0),
                    'track_id': person_info.get('track_id', 0),
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            if saved_path:
                self.add_face_hash(face_hash, person_info.get('track_id', 0), person_type)
                self.stats['images_saved'] += 1
                return saved_path
        
        return None
    
    def calculate_bbox_center(self, bbox):
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def calculate_distance(self, bbox1, bbox2):
        center1 = self.calculate_bbox_center(bbox1)
        center2 = self.calculate_bbox_center(bbox2)
        return np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
    
    def match_detection_to_track(self, bbox, frame_number):
        best_match_id = None
        best_distance = float('inf')
        
        for track_id, track_info in list(self.tracked_persons.items()):
            if frame_number - track_info['last_seen'] > getattr(config, 'TRACK_TIMEOUT', 30):
                del self.tracked_persons[track_id]
                if track_id in self.face_cache:
                    del self.face_cache[track_id]
                continue
            
            distance = self.calculate_distance(bbox, track_info['bbox'])
            
            if distance < self.max_track_distance and distance < best_distance:
                best_distance = distance
                best_match_id = track_id
        
        if best_match_id is None:
            best_match_id = self.next_track_id
            self.next_track_id += 1
            self.tracked_persons[best_match_id] = {
                'bbox': bbox,
                'count': 1,
                'last_seen': frame_number,
                'alerted': False,
                'is_known': False
            }
        else:
            self.tracked_persons[best_match_id]['bbox'] = bbox
            self.tracked_persons[best_match_id]['count'] += 1
            self.tracked_persons[best_match_id]['last_seen'] = frame_number
        
        return best_match_id
    
    def detect_and_classify(self, frame, frame_number):
        detected_persons = []
        confirmed_persons = []
        
        person_results = self.person_detector(
            frame, 
            classes=[0],
            conf=self.person_conf,
            verbose=False
        )
        
        if len(person_results[0].boxes) == 0:
            return detected_persons, confirmed_persons
        
        height, width = frame.shape[:2]
        min_area_percent = getattr(config, 'MIN_PERSON_AREA_PERCENT', 2)
        min_person_area = (width * height) * (min_area_percent / 100)
        
        persons_to_check = []
        
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
            
            if track_info['count'] >= self.min_detections:
                if track_id not in self.face_cache or not self.face_cache[track_id].get('checked', False):
                    person_crop = frame[y1:y2, x1:x2]
                    persons_to_check.append((track_id, person_crop, bbox, person_conf))
        
        if self.face_recognizer and persons_to_check:
            face_distance_threshold = getattr(config, 'FACE_DISTANCE_THRESHOLD', 0.6)
            enhance_frames = getattr(config, 'ENHANCE_FRAMES', True)
            
            for track_id, person_crop, bbox, person_conf in persons_to_check:
                if person_crop.size == 0:
                    continue
                
                face_results = self.face_recognizer.recognize_faces(
                    person_crop,
                    enhance=enhance_frames,
                    distance_threshold=face_distance_threshold
                )
                
                is_known = False
                known_conf = 0.0
                person_name = "Unknown"
                
                if face_results and len(face_results) > 0:
                    for face_result in face_results:
                        if face_result['is_known']:
                            is_known = True
                            known_conf = face_result['confidence']
                            person_name = face_result['name']
                            break
                
                self.face_cache[track_id] = {
                    'is_known': is_known,
                    'confidence': known_conf if is_known else person_conf,
                    'checked': True,
                    'name': person_name
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
            face_info = self.face_cache.get(track_id, {'is_known': False, 'confidence': 0.0, 'checked': False, 'name': 'Unknown'})
            
            if track_info['count'] >= self.min_detections:
                person_info = {
                    'bbox': bbox,
                    'is_known': face_info['is_known'],
                    'confidence': face_info['confidence'],
                    'type': 'known' if face_info['is_known'] else 'unknown',
                    'track_id': track_id,
                    'detection_count': track_info['count'],
                    'name': face_info.get('name', 'Unknown')
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
        self.stats['frames_processed'] += 1
        
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
                
                if person['is_known']:
                    label = f"{person.get('name', 'KNOWN')}: {person['confidence']:.2f}"
                else:
                    label = f"UNKNOWN: {person['confidence']:.2f}"
                
                cv2.putText(annotated, label, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        current_time = datetime.now()
        
        for person in confirmed_persons:
            track_id = person['track_id']
            
            alert_key = f"{person['type']}_{track_id}"
            
            if alert_key in self.last_alert_time:
                time_since_alert = (current_time - self.last_alert_time[alert_key]).total_seconds()
                if time_since_alert < self.alert_cooldown:
                    continue
            
            image_path = None
            if self.save_images:
                image_path = self.save_detection_image(annotated, person, person['type'])
            
            self.log_detection(person['type'], person['confidence'], current_time, image_path)
            
            if not person['is_known']:
                logger.warning(f"UNKNOWN PERSON DETECTED! Confidence: {person['confidence']:.2f}")
                
                if self.telegram_notifier:
                    self.telegram_notifier.send_unknown_person_alert(
                        image=annotated,
                        camera_id=self.camera_id,
                        confidence=person['confidence']
                    )
                
                self.send_alert_to_buzzer(pattern=getattr(config, 'BUZZER_PATTERN', 1))
                self.last_alert_time[alert_key] = current_time
            else:
                if getattr(config, 'ALERT_ON_KNOWN', False) and self.telegram_notifier:
                    send_photo = getattr(config, 'TELEGRAM_SEND_KNOWN_PERSON_ALERTS', False)
                    self.telegram_notifier.send_known_person_detected(
                        person_name=person.get('name', 'Known Person'),
                        camera_id=self.camera_id,
                        confidence=person['confidence'],
                        send_photo=send_photo,
                        image=annotated if send_photo else None
                    )
        
        self.current_frame = annotated
        return annotated
    
    def start(self):
        self.running = True
        self.stop_event.clear()
        
        frame_number = 0
        consecutive_failures = 0
        max_failures = 30
        
        logger.info("Security monitoring started")
        
        while self.running and not self.stop_event.is_set():
            if self.camera_manager and self.camera_manager.current_camera:
                ret, frame = self.camera_manager.read_frame()
            else:
                ret, frame, _ = self.frame_reader.read_frame(self.camera_id)
            
            if not ret or frame is None:
                consecutive_failures += 1
                
                if consecutive_failures > max_failures:
                    logger.error("Too many consecutive failures, stopping...")
                    break
                
                logger.warning(f"Failed to read frame ({consecutive_failures}/{max_failures})")
                time.sleep(2)
                continue
            
            consecutive_failures = 0
            frame_number += 1
            self.frame_count = frame_number
            
            frame_skip = getattr(config, 'FRAME_SKIP', 5)
            
            if frame_number % frame_skip == 0:
                processed_frame = self.process_frame(frame, frame_number)
                self.current_frame = processed_frame
            else:
                self.current_frame = frame
            
            self.stats['uptime'] = int(time.time() - self.start_time)
            
            time.sleep(0.01)
        
        logger.info("Security monitoring stopped")
        self.save_log()
        
        self.frame_reader.release()
    
    async def run(self):
        self.running = True
        self.stop_event.clear()
        
        frame_number = 0
        consecutive_failures = 0
        max_failures = 30
        
        logger.info("Security monitoring started (async)")
        
        while self.running and not self.stop_event.is_set():
            if self.camera_manager and self.camera_manager.current_camera:
                ret, frame = self.camera_manager.read_frame()
            else:
                ret, frame, _ = self.frame_reader.read_frame(self.camera_id)
            
            if not ret or frame is None:
                consecutive_failures += 1
                
                if consecutive_failures > max_failures:
                    logger.error("Too many consecutive failures, stopping...")
                    break
                
                logger.warning(f"Failed to read frame ({consecutive_failures}/{max_failures})")
                await asyncio.sleep(2)
                continue
            
            consecutive_failures = 0
            frame_number += 1
            self.frame_count = frame_number
            
            frame_skip = getattr(config, 'FRAME_SKIP', 5)
            
            if frame_number % frame_skip == 0:
                processed_frame = self.process_frame(frame, frame_number)
                self.current_frame = processed_frame
            else:
                self.current_frame = frame
            
            self.stats['uptime'] = int(time.time() - self.start_time)
            
            await asyncio.sleep(0.01)
        
        logger.info("Security monitoring stopped")
        self.save_log()
        
        self.frame_reader.release()
    
    def stop(self):
        self.running = False
        self.stop_event.set()
        self.save_log()
    
    def get_frame_stream(self):
        while self.running:
            if self.current_frame is not None:
                yield self.current_frame.copy()
            else:
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                yield blank
            time.sleep(0.033)
    
    def get_stats(self):
        return self.stats.copy()
    
    def get_24h_stats(self):
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
        detections = self.detections
        
        if type_filter:
            detections = [d for d in detections if d['type'] == type_filter]
        
        return list(reversed(detections[-limit:]))
    
    def get_detection_by_id(self, detection_id):
        for detection in self.detections:
            if detection['id'] == detection_id:
                return detection
        return None
    
    def get_detailed_stats(self):
        stats_24h = self.get_24h_stats()
        
        return {
            **self.stats,
            'unknown_24h': stats_24h['unknown'],
            'known_24h': stats_24h['known'],
            'total_24h': stats_24h['total'],
            'total_logged': len(self.detections)
        }