"""
Training Manager
Handles data collection, model training, and model management
"""

import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime
import shutil
import cv2
import numpy as np
from ultralytics import YOLO
import logging

logger = logging.getLogger(__name__)

class TrainingManager:
    def __init__(self, base_dir="training_data", models_dir="models"):
        self.base_dir = Path(base_dir)
        self.models_dir = Path(models_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)
        
        # Capture state
        self.capturing = False
        self.capture_thread = None
        self.capture_person = None
        self.capture_camera = None
        self.captured_count = 0
        self.target_count = 300
        self.auto_capture = False
        
        # Training state
        self.training = False
        self.training_thread = None
        self.training_progress = {
            "status": "idle",
            "epoch": 0,
            "total_epochs": 0,
            "loss": 0,
            "map": 0,
            "eta": ""
        }
        
        # Metadata file
        self.metadata_file = self.base_dir / "metadata.json"
        self.load_metadata()
    
    def load_metadata(self):
        """Load datasets metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {"datasets": {}}
    
    def save_metadata(self):
        """Save datasets metadata"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    # ==================== DATA COLLECTION ====================
    
    def start_capture(self, person_name, camera_source, auto=True, target=300):
        """Start capturing images for a person"""
        if self.capturing:
            return {"error": "Already capturing"}
        
        # Create dataset directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = f"{person_name.lower().replace(' ', '_')}_{timestamp}"
        dataset_path = self.base_dir / dataset_name
        dataset_path.mkdir(exist_ok=True)
        
        self.capture_person = person_name
        self.capture_camera = camera_source
        self.captured_count = 0
        self.target_count = target
        self.auto_capture = auto
        self.capturing = True
        self.dataset_path = dataset_path
        
        # Add to metadata
        self.metadata["datasets"][dataset_name] = {
            "person": person_name,
            "camera": camera_source,
            "created": timestamp,
            "count": 0,
            "status": "collecting"
        }
        self.save_metadata()
        
        logger.info(f"Started capture: {person_name} on {camera_source}")
        return {
            "status": "started",
            "dataset": dataset_name,
            "target": target
        }
    
    def capture_frame(self, frame):
        """Capture a single frame"""
        if not self.capturing:
            return {"error": "Not capturing"}
        
        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"img_{self.captured_count:04d}_{timestamp}.jpg"
        filepath = self.dataset_path / filename
        
        cv2.imwrite(str(filepath), frame)
        self.captured_count += 1
        
        # Update metadata
        dataset_name = self.dataset_path.name
        self.metadata["datasets"][dataset_name]["count"] = self.captured_count
        
        # Check if target reached
        if self.captured_count >= self.target_count:
            self.stop_capture()
            return {
                "captured": self.captured_count,
                "complete": True,
                "message": f"Captured {self.captured_count} images!"
            }
        
        return {
            "captured": self.captured_count,
            "target": self.target_count,
            "complete": False
        }
    
    def stop_capture(self):
        """Stop capturing"""
        if not self.capturing:
            return {"error": "Not capturing"}
        
        self.capturing = False
        dataset_name = self.dataset_path.name
        
        # Update metadata
        self.metadata["datasets"][dataset_name]["status"] = "complete"
        self.save_metadata()
        
        logger.info(f"Stopped capture: {self.captured_count} images collected")
        
        return {
            "status": "stopped",
            "total_captured": self.captured_count
        }
    
    def get_datasets(self):
        """Get all datasets"""
        datasets = []
        
        for dataset_name, info in self.metadata["datasets"].items():
            dataset_path = self.base_dir / dataset_name
            
            # Count actual images
            if dataset_path.exists():
                image_count = len(list(dataset_path.glob("*.jpg")))
            else:
                image_count = 0
            
            datasets.append({
                "name": dataset_name,
                "person": info.get("person", "Unknown"),
                "camera": info.get("camera", "Unknown"),
                "created": info.get("created", ""),
                "count": image_count,
                "status": info.get("status", "unknown"),
                "path": str(dataset_path)
            })
        
        return datasets
    
    def delete_dataset(self, dataset_name):
        """Delete a dataset"""
        dataset_path = self.base_dir / dataset_name
        
        if dataset_path.exists():
            shutil.rmtree(dataset_path)
        
        if dataset_name in self.metadata["datasets"]:
            del self.metadata["datasets"][dataset_name]
            self.save_metadata()
        
        logger.info(f"Deleted dataset: {dataset_name}")
        return {"status": "deleted"}
    
    # ==================== MODEL TRAINING ====================
    
    def prepare_yolo_dataset(self, selected_datasets, output_dir="yolo_dataset"):
        """Prepare YOLO format dataset from collected images"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Create structure
        (output_path / "images" / "train").mkdir(parents=True, exist_ok=True)
        (output_path / "labels" / "train").mkdir(parents=True, exist_ok=True)
        
        # Map person names to class IDs
        persons = list(set([d["person"] for d in selected_datasets if d["person"] != "negatives"]))
        class_mapping = {person: idx for idx, person in enumerate(persons)}
        
        # Copy and annotate images
        for dataset in selected_datasets:
            dataset_path = Path(dataset["path"])
            person = dataset["person"]
            
            if not dataset_path.exists():
                continue
            
            for img_file in dataset_path.glob("*.jpg"):
                # Copy image
                dest_img = output_path / "images" / "train" / f"{dataset['name']}_{img_file.name}"
                shutil.copy(img_file, dest_img)
                
                # Create label file
                if person != "negatives":
                    # For positive samples, create bounding box annotation
                    # Using full image as bounding box (will be refined by auto-annotation)
                    label_file = output_path / "labels" / "train" / f"{dataset['name']}_{img_file.stem}.txt"
                    
                    class_id = class_mapping[person]
                    # Full image bbox: center_x, center_y, width, height (normalized)
                    with open(label_file, 'w') as f:
                        f.write(f"{class_id} 0.5 0.5 0.8 0.8\n")
                else:
                    # For negatives, create empty label file
                    label_file = output_path / "labels" / "train" / f"{dataset['name']}_{img_file.stem}.txt"
                    label_file.touch()
        
        # Create data.yaml
        yaml_content = f"""
path: {output_path.absolute()}
train: images/train
val: images/train

nc: {len(persons)}
names: {persons}
"""
        
        with open(output_path / "data.yaml", 'w') as f:
            f.write(yaml_content)
        
        return {
            "dataset_path": str(output_path),
            "classes": persons,
            "class_mapping": class_mapping
        }
    
    def start_training(self, model_name, selected_datasets, epochs=100, batch=16, imgsz=640):
        """Start model training in background"""
        if self.training:
            return {"error": "Already training"}
        
        self.training = True
        self.training_progress = {
            "status": "preparing",
            "epoch": 0,
            "total_epochs": epochs,
            "loss": 0,
            "map": 0,
            "eta": "Calculating..."
        }
        
        # Start training thread
        self.training_thread = threading.Thread(
            target=self._train_model,
            args=(model_name, selected_datasets, epochs, batch, imgsz),
            daemon=True
        )
        self.training_thread.start()
        
        return {"status": "started", "model_name": model_name}
    
    def _train_model(self, model_name, selected_datasets, epochs, batch, imgsz):
        """Training worker thread"""
        try:
            logger.info(f"Starting training: {model_name}")
            
            # Prepare dataset
            self.training_progress["status"] = "preparing_dataset"
            dataset_info = self.prepare_yolo_dataset(selected_datasets)
            
            # Initialize model
            self.training_progress["status"] = "training"
            model = YOLO('yolov8n.pt')  # Start from pretrained
            
            # Train
            results = model.train(
                data=str(Path(dataset_info["dataset_path"]) / "data.yaml"),
                epochs=epochs,
                batch=batch,
                imgsz=imgsz,
                project=str(self.models_dir),
                name=model_name,
                exist_ok=True,
                verbose=True
            )
            
            # Save metadata
            model_path = self.models_dir / model_name
            metadata = {
                "name": model_name,
                "created": datetime.now().isoformat(),
                "classes": dataset_info["classes"],
                "class_mapping": dataset_info["class_mapping"],
                "epochs": epochs,
                "batch": batch,
                "imgsz": imgsz,
                "datasets": [d["name"] for d in selected_datasets],
                "cameras": list(set([d["camera"] for d in selected_datasets])),
                "metrics": {
                    "map": float(results.results_dict.get('metrics/mAP50(B)', 0)),
                    "precision": float(results.results_dict.get('metrics/precision(B)', 0)),
                    "recall": float(results.results_dict.get('metrics/recall(B)', 0))
                }
            }
            
            with open(model_path / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.training_progress["status"] = "complete"
            self.training_progress["epoch"] = epochs
            
            logger.info(f"Training complete: {model_name}")
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            self.training_progress["status"] = "failed"
            self.training_progress["error"] = str(e)
        finally:
            self.training = False
    
    def get_training_progress(self):
        """Get current training progress"""
        return self.training_progress
    
    def stop_training(self):
        """Stop training (not implemented - YOLO training is hard to interrupt)"""
        return {"error": "Cannot stop training once started"}
    
    # ==================== MODEL MANAGEMENT ====================
    
    def get_models(self):
        """Get all trained models"""
        models = []
        
        for model_dir in self.models_dir.iterdir():
            if not model_dir.is_dir():
                continue
            
            weights_file = model_dir / "weights" / "best.pt"
            metadata_file = model_dir / "metadata.json"
            
            if not weights_file.exists():
                continue
            
            # Load metadata
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    "name": model_dir.name,
                    "created": "Unknown",
                    "classes": [],
                    "cameras": []
                }
            
            models.append({
                "name": model_dir.name,
                "path": str(weights_file),
                "created": metadata.get("created", "Unknown"),
                "classes": metadata.get("classes", []),
                "cameras": metadata.get("cameras", []),
                "epochs": metadata.get("epochs", 0),
                "metrics": metadata.get("metrics", {}),
                "size_mb": weights_file.stat().st_size / (1024 * 1024)
            })
        
        return models
    
    def delete_model(self, model_name):
        """Delete a trained model"""
        model_path = self.models_dir / model_name
        
        if model_path.exists():
            shutil.rmtree(model_path)
            logger.info(f"Deleted model: {model_name}")
            return {"status": "deleted"}
        
        return {"error": "Model not found"}
    
    def get_model_info(self, model_name):
        """Get detailed model information"""
        model_path = self.models_dir / model_name
        metadata_file = model_path / "metadata.json"
        
        if not metadata_file.exists():
            return {"error": "Model not found"}
        
        with open(metadata_file, 'r') as f:
            return json.load(f)