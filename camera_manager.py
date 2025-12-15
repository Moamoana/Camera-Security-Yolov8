import cv2
import logging
import requests

logger = logging.getLogger(__name__)

class CameraManager:
    def __init__(self):
        self.cameras = {}
        self.current_camera = None
        self.current_source = None
    
    def detect_cameras(self, webcam_index=0, esp32_url=""):
        self.cameras = {}
        
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
        
        if esp32_url:
            try:
                status_url = esp32_url.replace('/stream', '/status')
                r = requests.get(status_url, timeout=2)
                if r.status_code == 200:
                    self.cameras['esp32'] = {
                        'id': 'esp32',
                        'name': 'ESP32-CAM',
                        'type': 'esp32',
                        'source': esp32_url,
                        'resolution': '640x480'
                    }
            except:
                pass
        
        logger.info(f"Detected {len(self.cameras)} cameras")
    
    def list_all(self):
        return list(self.cameras.values())
    
    def select_camera(self, camera_id):
        if camera_id not in self.cameras:
            return False
        
        if self.current_camera:
            self.current_camera.release()
            self.current_camera = None
        
        cam = self.cameras[camera_id]
        cap = cv2.VideoCapture(cam['source'])
        
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
            return None, None
        ret, frame = self.current_camera.read()
        return (True, frame) if ret else (False, None)
    
    def release(self):
        if self.current_camera:
            self.current_camera.release()
            self.current_camera = None
            self.current_source = None
    
    def add_ip_camera(self, name, url):
        camera_id = name.lower().replace(" ", "_").replace("-", "_")
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