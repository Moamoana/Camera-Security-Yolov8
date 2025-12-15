import os
import cv2
import numpy as np
from pathlib import Path
import logging
import pickle
import json
from datetime import datetime
from io import BytesIO

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    face_recognition = None

logger = logging.getLogger(__name__)

class FaceRecognitionManager:
    def __init__(self, known_faces_dir="known_faces", encodings_cache="face_encodings.pkl"):
        if not FACE_RECOGNITION_AVAILABLE:
            logger.warning("face_recognition library not installed")
            self.available = False
            return
        
        self.available = True
        self.known_faces_dir = Path(known_faces_dir)
        self.encodings_cache = Path(encodings_cache)
        self.known_faces_dir.mkdir(exist_ok=True)
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_known_faces()
        logger.info(f"Face recognition initialized with {len(self.known_face_names)} known persons")
    
    def load_known_faces(self):
        if self.encodings_cache.exists():
            try:
                with open(self.encodings_cache, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data['encodings']
                    self.known_face_names = data['names']
                logger.info(f"Loaded cached encodings for {len(self.known_face_names)} persons")
                return
            except Exception as e:
                logger.error(f"Failed to load cached encodings: {e}")
        
        self.known_face_encodings = []
        self.known_face_names = []
        
        if not self.known_faces_dir.exists():
            return
        
        for person_dir in self.known_faces_dir.iterdir():
            if not person_dir.is_dir():
                continue
            
            person_name = person_dir.name
            logger.info(f"Loading faces for: {person_name}")
            
            for img_path in person_dir.glob("*.jpg"):
                try:
                    image = face_recognition.load_image_file(str(img_path))
                    encodings = face_recognition.face_encodings(image)
                    
                    if encodings:
                        self.known_face_encodings.append(encodings[0])
                        self.known_face_names.append(person_name)
                except Exception as e:
                    logger.error(f"Error loading {img_path}: {e}")
        
        self.save_encodings()
    
    def save_encodings(self):
        try:
            data = {
                'encodings': self.known_face_encodings,
                'names': self.known_face_names
            }
            with open(self.encodings_cache, 'wb') as f:
                pickle.dump(data, f)
            logger.info("Encodings cached successfully")
        except Exception as e:
            logger.error(f"Failed to cache encodings: {e}")
    
    def enhance_image(self, image):
        try:
            # Ensure input is uint8
            if image.dtype != np.uint8:
                image = np.clip(image, 0, 255).astype(np.uint8)
            
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            enhanced = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
            enhanced = cv2.filter2D(enhanced, -1, kernel)
            
            # Ensure output is uint8
            if enhanced.dtype != np.uint8:
                enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
            
            return enhanced
        except Exception as e:
            logger.error(f"Error enhancing image: {e}")
            return image
    
    def recognize_faces(self, image, enhance=False, distance_threshold=0.6):
        if not self.available:
            return []
        
        try:
            # Save to temp file and use face_recognition's loader
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                temp_path = tmp.name
            
            cv2.imwrite(temp_path, image)
            rgb_image = face_recognition.load_image_file(temp_path)
            
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
            
            face_locations = face_recognition.face_locations(rgb_image, model="hog")
            
            if not face_locations:
                return []
            
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            results = []
            for face_encoding, face_location in zip(face_encodings, face_locations):
                if not self.known_face_encodings:
                    results.append({
                        'is_known': False,
                        'name': 'Unknown',
                        'confidence': 0.0,
                        'location': face_location
                    })
                    continue
                
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                best_distance = face_distances[best_match_index]
                
                if best_distance < distance_threshold:
                    name = self.known_face_names[best_match_index]
                    confidence = 1.0 - best_distance
                    is_known = True
                else:
                    name = 'Unknown'
                    confidence = best_distance
                    is_known = False
                
                results.append({
                    'is_known': is_known,
                    'name': name,
                    'confidence': float(confidence),
                    'location': face_location
                })
            
            return results
        except Exception as e:
            logger.error(f"Error recognizing faces: {e}")
            return []
    
    def capture_and_add_person(self, person_name, frames, camera_name="Unknown"):
        if not self.available:
            return {"error": "Face recognition not available"}
        
        person_dir = self.known_faces_dir / person_name
        person_dir.mkdir(exist_ok=True)
        
        metadata = {
            'camera': camera_name,
            'date': datetime.now().isoformat(),
            'frames_count': len(frames)
        }
        with open(person_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f)
        
        added = 0
        for i, frame in enumerate(frames):
            try:
                # Debug logging
                logger.info(f"Frame {i}: dtype={frame.dtype}, shape={frame.shape}")
                
                # Save frame to temp file first
                temp_path = person_dir / f"temp_{i}.jpg"
                cv2.imwrite(str(temp_path), frame)
                
                # Use face_recognition's own loader - this is guaranteed to work
                rgb_frame = face_recognition.load_image_file(str(temp_path))
                
                logger.info(f"Frame {i} via load_image_file: dtype={rgb_frame.dtype}, shape={rgb_frame.shape}")
                
                # Get face encodings
                encodings = face_recognition.face_encodings(rgb_frame)
                
                if encodings:
                    # Rename temp to final
                    final_path = person_dir / f"photo_{i+1}.jpg"
                    temp_path.rename(final_path)
                    
                    self.known_face_encodings.append(encodings[0])
                    self.known_face_names.append(person_name)
                    added += 1
                    logger.info(f"Successfully processed frame {i} for {person_name}")
                else:
                    # Remove temp file if no face found
                    temp_path.unlink(missing_ok=True)
                    logger.warning(f"No face found in frame {i}")
            except Exception as e:
                logger.error(f"Error processing frame {i}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Clean up temp file on error
                temp_path = person_dir / f"temp_{i}.jpg"
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
        
        self.save_encodings()
        
        return {
            "success": True,
            "person": person_name,
            "encodings_added": added,
            "camera": camera_name,
            "total_encodings": len([n for n in self.known_face_names if n == person_name])
        }
    
    def get_known_persons(self):
        return list(set(self.known_face_names))
    
    def get_person_metadata(self, person_name):
        person_dir = self.known_faces_dir / person_name
        metadata_file = person_dir / 'metadata.json'
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                return json.load(f)
        return None