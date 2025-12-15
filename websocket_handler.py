"""
WebSocket Handler for ESP32 Camera
Receives frames from ESP32-CAM via WebSocket
"""

import asyncio
import logging
import cv2
import numpy as np
import base64
import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Optional
from datetime import datetime
import threading
from collections import deque

logger = logging.getLogger(__name__)

class CameraWebSocketHandler:
    def __init__(self, buffer_size: int = 2):   
        self.connections: Dict[str, WebSocket] = {}
        self.frame_buffers: Dict[str, deque] = {}
        self.camera_metadata: Dict[str, dict] = {}
        self.buffer_size = buffer_size
        
        # Statistics
        self.stats = {
            'frames_received': 0,
            'frames_dropped': 0,
            'bytes_received': 0,
            'connections': 0
        }
    
    async def handle_camera_connection(self, websocket: WebSocket, camera_id: str):
        """
        Handle WebSocket connection from ESP32 camera
        """
        await websocket.accept()
        
        self.connections[camera_id] = websocket
        self.frame_buffers[camera_id] = deque(maxlen=self.buffer_size)
        self.camera_metadata[camera_id] = {
            'connected_at': datetime.now().isoformat(),
            'last_frame': None,
            'frame_count': 0,
            'status': 'connected'
        }
        self.stats['connections'] += 1
        
        logger.info(f"Camera {camera_id} connected")
        
        try:
            while True:
                # Receive data from ESP32
                data = await websocket.receive_text()
                
                # Parse JSON message
                try:
                    message = json.loads(data)
                    
                    if message.get('type') == 'frame':
                        await self._process_frame(camera_id, message)
                    elif message.get('type') == 'heartbeat':
                        await self._process_heartbeat(camera_id, message)
                    else:
                        logger.warning(f"Unknown message type from {camera_id}: {message.get('type')}")
                
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from {camera_id}")
                    continue
        
        except WebSocketDisconnect:
            logger.info(f"Camera {camera_id} disconnected")
            self._cleanup_camera(camera_id)
        
        except Exception as e:
            logger.error(f"Error handling camera {camera_id}: {e}")
            self._cleanup_camera(camera_id)
    
    async def _process_frame(self, camera_id: str, message: dict):
        """Process received frame"""
        try:
            # Decode base64 frame
            frame_b64 = message.get('frame', '')
            if not frame_b64:
                return
            
            frame_bytes = base64.b64decode(frame_b64)
            self.stats['bytes_received'] += len(frame_bytes)
            
            # Decode JPEG to numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.warning(f"Failed to decode frame from {camera_id}")
                return
            
            # Store frame with metadata
            frame_data = {
                'frame': frame,
                'timestamp': message.get('timestamp', datetime.now().timestamp()),
                'width': frame.shape[1],
                'height': frame.shape[0],
                'camera_id': camera_id
            }
            
            # Add to buffer (automatically removes oldest if full)
            self.frame_buffers[camera_id].append(frame_data)
            
            # Update metadata
            self.camera_metadata[camera_id]['last_frame'] = datetime.now().isoformat()
            self.camera_metadata[camera_id]['frame_count'] += 1
            self.stats['frames_received'] += 1
            
            # Send acknowledgment
            await self.connections[camera_id].send_json({
                'status': 'received',
                'frame_count': self.camera_metadata[camera_id]['frame_count']
            })
        
        except Exception as e:
            logger.error(f"Error processing frame from {camera_id}: {e}")
    
    async def _process_heartbeat(self, camera_id: str, message: dict):
        """Process heartbeat message"""
        self.camera_metadata[camera_id]['last_heartbeat'] = datetime.now().isoformat()
        
        # Send response
        await self.connections[camera_id].send_json({
            'status': 'alive',
            'server_time': datetime.now().isoformat()
        })
    
    def _cleanup_camera(self, camera_id: str):
        """Cleanup camera connection"""
        if camera_id in self.connections:
            del self.connections[camera_id]
        
        if camera_id in self.frame_buffers:
            del self.frame_buffers[camera_id]
        
        if camera_id in self.camera_metadata:
            self.camera_metadata[camera_id]['status'] = 'disconnected'
    
    def get_latest_frame(self, camera_id: str) -> Optional[dict]:
        """Get latest frame from camera buffer"""
        if camera_id not in self.frame_buffers or len(self.frame_buffers[camera_id]) == 0:
            return None
        
        return self.frame_buffers[camera_id][-1]
    
    def get_camera_status(self, camera_id: str) -> dict:
        """Get camera status"""
        if camera_id not in self.camera_metadata:
            return {'status': 'not_connected'}
        
        return self.camera_metadata[camera_id]
    
    def get_all_cameras(self) -> list:
        """Get list of all connected cameras"""
        cameras = []
        for camera_id, metadata in self.camera_metadata.items():
            cameras.append({
                'id': camera_id,
                **metadata
            })
        return cameras
    
    def is_camera_connected(self, camera_id: str) -> bool:
        """Check if camera is connected"""
        return camera_id in self.connections
    
    def get_stats(self) -> dict:
        """Get handler statistics"""
        return {
            **self.stats,
            'active_cameras': len(self.connections),
            'buffered_frames': sum(len(buf) for buf in self.frame_buffers.values())
        }


class FrameReader:
    """
    Unified frame reader that works with both WebSocket and HTTP stream
    """
    def __init__(self, mode: str = "websocket", websocket_handler: CameraWebSocketHandler = None,
                 http_url: str = None):
        self.mode = mode
        self.websocket_handler = websocket_handler
        self.http_url = http_url
        self.http_capture = None
        
        if mode == "http_stream" and http_url:
            self._init_http_stream()
    
    def _init_http_stream(self):
        """Initialize HTTP stream capture"""
        try:
            self.http_capture = cv2.VideoCapture(self.http_url)
            if self.http_capture.isOpened():
                logger.info(f"HTTP stream opened: {self.http_url}")
            else:
                logger.error(f"Failed to open HTTP stream: {self.http_url}")
        except Exception as e:
            logger.error(f"Error opening HTTP stream: {e}")
    
    def read_frame(self, camera_id: str = None):
        """
        Read frame from camera
        Returns: (success, frame, metadata)
        """
        if self.mode == "websocket":
            if not self.websocket_handler:
                return False, None, None
            
            frame_data = self.websocket_handler.get_latest_frame(camera_id)
            if frame_data:
                return True, frame_data['frame'], {
                    'timestamp': frame_data['timestamp'],
                    'camera_id': camera_id,
                    'source': 'websocket'
                }
            return False, None, None
        
        elif self.mode == "http_stream":
            if not self.http_capture or not self.http_capture.isOpened():
                return False, None, None
            
            ret, frame = self.http_capture.read()
            if ret:
                return True, frame, {
                    'timestamp': datetime.now().timestamp(),
                    'camera_id': camera_id or 'http_stream',
                    'source': 'http_stream'
                }
            return False, None, None
        
        return False, None, None
    
    def is_available(self, camera_id: str = None) -> bool:
        """Check if camera is available"""
        if self.mode == "websocket":
            return self.websocket_handler and self.websocket_handler.is_camera_connected(camera_id)
        elif self.mode == "http_stream":
            return self.http_capture and self.http_capture.isOpened()
        return False
    
    def release(self):
        """Release resources"""
        if self.http_capture:
            self.http_capture.release()
            logger.info("HTTP stream released")