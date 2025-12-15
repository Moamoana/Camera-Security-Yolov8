"""
Telegram Notifier
Sends alerts and photos to Telegram
"""

import requests
import logging
import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict
import io

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, cooldown_seconds: int = 300):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.cooldown_seconds = cooldown_seconds
        
        # Track last alerts to prevent spam
        self.last_alert_time = {}  # {person_id: timestamp}
        
        # Telegram API URLs
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.send_message_url = f"{self.base_url}/sendMessage"
        self.send_photo_url = f"{self.base_url}/sendPhoto"
    
    def can_send_alert(self, person_id: str) -> bool:
        """Check if enough time has passed since last alert for this person"""
        if person_id not in self.last_alert_time:
            return True
        
        time_since_last = datetime.now() - self.last_alert_time[person_id]
        return time_since_last.total_seconds() >= self.cooldown_seconds
    
    def send_text(self, message: str) -> bool:
        """Send text message to Telegram"""
        try:
            response = requests.post(
                self.send_message_url,
                data={
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram send failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def send_photo_with_caption(self, image: np.ndarray, caption: str) -> bool:
        """Send photo with caption to Telegram"""
        try:
            # Encode image as JPEG
            success, encoded_image = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success:
                logger.error("Failed to encode image")
                return False
            
            # Convert to bytes
            photo_bytes = io.BytesIO(encoded_image.tobytes())
            photo_bytes.name = 'alert.jpg'
            
            # Send to Telegram
            response = requests.post(
                self.send_photo_url,
                data={
                    'chat_id': self.chat_id,
                    'caption': caption,
                    'parse_mode': 'HTML'
                },
                files={'photo': photo_bytes},
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info("Telegram photo sent successfully")
                return True
            else:
                logger.error(f"Telegram photo send failed: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Telegram photo send error: {e}")
            return False
    
    def send_unknown_person_alert(self, image: np.ndarray, camera_id: str = "Security Camera",
                                  confidence: float = 0.0, location: tuple = None) -> bool:
        """
        Send alert for unknown person detection
        """
        person_id = f"unknown_{datetime.now().strftime('%Y%m%d_%H')}"  # Hourly grouping
        
        # Check cooldown
        if not self.can_send_alert(person_id):
            logger.info(f"Alert cooldown active for {person_id}")
            return False
        
        # Create alert message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        caption = (
            f"🚨 <b>UNKNOWN PERSON DETECTED</b>\n\n"
            f"📷 Camera: {camera_id}\n"
            f"🕒 Time: {timestamp}\n"
            f"📊 Confidence: {confidence:.1%}\n"
        )
        
        if location:
            caption += f"📍 Location: {location}\n"
        
        # Send photo with caption
        success = self.send_photo_with_caption(image, caption)
        
        if success:
            self.last_alert_time[person_id] = datetime.now()
        
        return success
    
    def send_known_person_detected(self, person_name: str, camera_id: str = "Security Camera",
                                   confidence: float = 0.0, send_photo: bool = False, 
                                   image: Optional[np.ndarray] = None) -> bool:
        """
        Send notification for known person detection (optional)
        """
        person_id = f"known_{person_name}"
        
        # Check cooldown (longer for known persons)
        if not self.can_send_alert(person_id):
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if send_photo and image is not None:
            caption = (
                f"✅ <b>Known Person Detected</b>\n\n"
                f"👤 Name: {person_name}\n"
                f"📷 Camera: {camera_id}\n"
                f"🕒 Time: {timestamp}\n"
                f"📊 Confidence: {confidence:.1%}"
            )
            success = self.send_photo_with_caption(image, caption)
        else:
            message = (
                f"✅ <b>Known Person Detected</b>\n\n"
                f"👤 Name: {person_name}\n"
                f"📷 Camera: {camera_id}\n"
                f"🕒 Time: {timestamp}\n"
                f"📊 Confidence: {confidence:.1%}"
            )
            success = self.send_text(message)
        
        if success:
            self.last_alert_time[person_id] = datetime.now()
        
        return success
    
    def send_system_status(self, status: Dict) -> bool:
        """Send system status update"""
        message = (
            f"📊 <b>System Status</b>\n\n"
            f"Status: {status.get('status', 'Unknown')}\n"
            f"Uptime: {status.get('uptime', 'N/A')}\n"
            f"Detections Today: {status.get('detections_today', 0)}\n"
            f"Known Persons: {status.get('known_persons', 0)}\n"
            f"Camera: {status.get('camera_status', 'Unknown')}"
        )
        
        return self.send_text(message)
    
    def send_multiple_photos(self, images: list, caption: str) -> bool:
        """
        Send multiple photos (max 3) to Telegram
        """
        if not images or len(images) == 0:
            return False
        
        # Limit to 3 photos
        images = images[:3]
        
        try:
            # Send first photo with caption
            success = self.send_photo_with_caption(images[0], caption)
            
            # Send remaining photos without caption
            for image in images[1:]:
                self.send_photo_with_caption(image, "")
            
            return success
        
        except Exception as e:
            logger.error(f"Error sending multiple photos: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=5)
            
            if response.status_code == 200:
                bot_info = response.json()
                logger.info(f"Telegram bot connected: {bot_info.get('result', {}).get('username', 'Unknown')}")
                return True
            else:
                logger.error(f"Telegram connection failed: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return False