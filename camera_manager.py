"""
Camera Manager
Handles camera selection and switching
"""

import cv2
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class CameraManager:
    def __init__(self):
        self.current_camera = None
        self.current_source = None
        self.available_cameras = []
        self.detect_cameras()
    
    def detect_cameras(self):
        """Detect available cameras"""
        self.available_cameras = []
        
        for idx in range(3):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    
                    self.available_cameras.append({
                        "id": f"webcam_{idx}",
                        "name": f"Webcam ({idx})",
                        "type": "webcam",
                        "source": idx,
                        "resolution": f"{width}x{height}"
                    })
                cap.release()
        
        logger.info(f"Detected {len(self.available_cameras)} cameras")
    
    def add_ip_camera(self, name: str, url: str):
        camera_id = name.lower().replace(" ", "_")
        
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                camera_info = {
                    "id": camera_id,
                    "name": name,
                    "type": "ip",
                    "source": url,
                    "resolution": f"{width}x{height}"
                }
                
                existing = next((c for c in self.available_cameras if c["id"] == camera_id), None)
                if existing:
                    idx = self.available_cameras.index(existing)
                    self.available_cameras[idx] = camera_info
                else:
                    self.available_cameras.append(camera_info)
                
                cap.release()
                logger.info(f"Added IP camera: {name} ({url})")
                return {"status": "success", "camera": camera_info}
            cap.release()
        
        logger.error(f"Failed to connect to IP camera: {url}")
        return {"error": "Failed to connect to camera"}
    
    def get_cameras(self) -> List[Dict]:
        """Get list of available cameras"""
        return self.available_cameras
    
    def select_camera(self, camera_id: str):
        """Select a camera by ID"""
        camera = next((c for c in self.available_cameras if c["id"] == camera_id), None)
        
        if not camera:
            return {"error": "Camera not found"}
        
        if self.current_camera is not None:
            self.current_camera.release()
            self.current_camera = None
        
        source = camera["source"]
        cap = cv2.VideoCapture(source)
        
        if not cap.isOpened():
            logger.error(f"Failed to open camera: {camera_id}")
            return {"error": "Failed to open camera"}
        
        self.current_camera = cap
        self.current_source = camera
        
        logger.info(f"Selected camera: {camera['name']}")
        return {"status": "success", "camera": camera}
    
    def get_current_camera(self) -> Optional[Dict]:
        """Get currently selected camera"""
        return self.current_source
    
    def read_frame(self):
        """Read frame from current camera"""
        if self.current_camera is None:
            return None, None
        
        ret, frame = self.current_camera.read()
        if ret:
            return True, frame
        return False, None
    
    def release(self):
        """Release current camera"""
        if self.current_camera is not None:
            self.current_camera.release()
            self.current_camera = None
            self.current_source = None
    
    def test_camera(self, camera_id: str):
        """Test if a camera is accessible"""
        camera = next((c for c in self.available_cameras if c["id"] == camera_id), None)
        
        if not camera:
            return {"error": "Camera not found"}
        
        cap = cv2.VideoCapture(camera["source"])
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                return {"status": "ok", "message": "Camera is accessible"}
            return {"error": "Camera opened but cannot read frames"}
        
        return {"error": "Cannot open camera"}