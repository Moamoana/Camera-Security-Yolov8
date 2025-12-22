import cv2
import logging
import requests
import numpy as np
import threading
import time

logger = logging.getLogger(__name__)


class ESP32CameraCapture:
    """Handles ESP32-CAM via HTTP requests instead of OpenCV VideoCapture"""
    
    def __init__(self, base_url):
        self.base_url = base_url.replace('/stream', '').rstrip('/')
        self.capture_url = f"{self.base_url}/capture"
        self.status_url = f"{self.base_url}/status"
        
        self.last_frame = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.session = requests.Session()
    
    def start(self):
        """Start background frame capture thread"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"ESP32 capture started: {self.capture_url}")
    
    def stop(self):
        """Stop capture thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.session.close()
    
    def _capture_loop(self):
        """Continuously fetch frames via HTTP"""
        error_count = 0
        
        while self.running:
            try:
                response = self.session.get(self.capture_url, timeout=3)
                
                if response.status_code == 200:
                    img_array = np.frombuffer(response.content, dtype=np.uint8)
                    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        with self.lock:
                            self.last_frame = frame
                        error_count = 0
                else:
                    error_count += 1
                    
            except requests.exceptions.Timeout:
                error_count += 1
                time.sleep(0.3)
            except requests.exceptions.ConnectionError:
                error_count += 1
                time.sleep(1)
            except Exception as e:
                logger.error(f"ESP32 capture error: {e}")
                error_count += 1
                time.sleep(0.5)
            
            # Back off if too many errors
            if error_count > 10:
                time.sleep(2)
                error_count = 0
    
    def read(self):
        """Get latest frame (called by main code)"""
        with self.lock:
            if self.last_frame is not None:
                return True, self.last_frame.copy()
        return False, None
    
    def isOpened(self):
        """Check if ESP32 is reachable"""
        try:
            r = self.session.get(self.status_url, timeout=2)
            return r.status_code == 200
        except:
            return False
    
    def release(self):
        """Release resources"""
        self.stop()


class CameraManager:
    def __init__(self):
        self.cameras = {}
        self.current_camera = None
        self.current_source = None
        self.esp32_capture = None
    
    def detect_cameras(self, webcam_index=0, esp32_url=""):
        self.cameras = {}
        
        # Detect webcam
        cap = cv2.VideoCapture(webcam_index, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.cameras['webcam'] = {
                    'id': 'webcam',
                    'name': f'Webcam {webcam_index}',
                    'type': 'webcam',
                    'source': webcam_index,
                    'resolution': f'{w}x{h}'
                }
            cap.release()
        
        # Detect ESP32-CAM
        if esp32_url:
            base_url = esp32_url.replace('/stream', '').rstrip('/')
            try:
                r = requests.get(f"{base_url}/status", timeout=3)
                if r.status_code == 200:
                    self.cameras['esp32'] = {
                        'id': 'esp32',
                        'name': 'ESP32-CAM',
                        'type': 'esp32',
                        'source': esp32_url,
                        'base_url': base_url,
                        'resolution': '640x480'
                    }
                    logger.info(f"ESP32-CAM found at {base_url}")
            except:
                logger.warning("ESP32-CAM not available")
        
        logger.info(f"Detected {len(self.cameras)} cameras")
    
    def list_all(self):
        return list(self.cameras.values())
    
    def select_camera(self, camera_id):
        if camera_id not in self.cameras:
            return False
        
        # Release current camera first
        self.release()
        
        cam = self.cameras[camera_id]
        
        if cam['type'] == 'esp32':
            # Use HTTP-based capture for ESP32
            base_url = cam.get('base_url', cam['source'].replace('/stream', ''))
            self.esp32_capture = ESP32CameraCapture(base_url)
            
            if self.esp32_capture.isOpened():
                self.esp32_capture.start()
                self.current_camera = self.esp32_capture
                self.current_source = cam
                logger.info(f"Selected ESP32-CAM via HTTP: {base_url}")
                return True
            else:
                logger.error("ESP32-CAM not responding")
                self.esp32_capture = None
                return False
        else:
            # Use OpenCV for webcam
            cap = cv2.VideoCapture(cam['source'], cv2.CAP_DSHOW)
            if not cap.isOpened():
                logger.error(f"Failed to open: {camera_id}")
                return False
            
            self.current_camera = cap
            self.current_source = cam
            logger.info(f"Selected: {cam['name']}")
            return True
    
    def get_current(self):
        return self.current_source
    
    def read_frame(self):
        if not self.current_camera:
            return False, None
        
        if isinstance(self.current_camera, ESP32CameraCapture):
            return self.current_camera.read()
        else:
            ret, frame = self.current_camera.read()
            return (True, frame) if ret else (False, None)
    
    def release(self):
        if self.esp32_capture:
            self.esp32_capture.release()
            self.esp32_capture = None
        
        if self.current_camera and not isinstance(self.current_camera, ESP32CameraCapture):
            self.current_camera.release()
        
        self.current_camera = None
        self.current_source = None
    
    def add_ip_camera(self, name, url):
        camera_id = name.lower().replace(" ", "_").replace("-", "_")
        
        # Check if it's an ESP32
        base_url = url.replace('/stream', '').rstrip('/')
        try:
            r = requests.get(f"{base_url}/status", timeout=3)
            if r.status_code == 200:
                self.cameras[camera_id] = {
                    'id': camera_id,
                    'name': name,
                    'type': 'esp32',
                    'source': url,
                    'base_url': base_url,
                    'resolution': '640x480'
                }
                logger.info(f"Added ESP32-CAM: {name}")
                return {"status": "success"}
        except:
            pass
        
        # Regular IP camera
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.cameras[camera_id] = {
                    'id': camera_id,
                    'name': name,
                    'type': 'ip',
                    'source': url,
                    'resolution': f'{w}x{h}'
                }
                cap.release()
                logger.info(f"Added IP camera: {name}")
                return {"status": "success"}
            cap.release()
        return {"error": "Failed to connect"}
    
    def get_cameras(self):
        return list(self.cameras.values())