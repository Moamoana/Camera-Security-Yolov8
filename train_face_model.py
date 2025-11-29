"""
YOLOv8 Face Recognition Training Script
Train a custom YOLOv8 model to recognize your specific face
"""

from ultralytics import YOLO
import torch

def train_face_model(
    data_yaml='face_dataset.yaml',
    model='yolov8n.pt',
    epochs=100,
    imgsz=640,
    batch=16,
    patience=20,
    save_dir='runs/face_detection'
):
    """
    Train YOLOv8 model on custom face dataset
    
    Args:
        data_yaml: Path to dataset configuration file
        model: Base model to start from (yolov8n.pt, yolov8s.pt, etc.)
        epochs: Number of training epochs
        imgsz: Input image size
        batch: Batch size
        patience: Early stopping patience
        save_dir: Directory to save training results
    """
    print(f"\n{'='*60}")
    print("YOLOV8 FACE RECOGNITION TRAINING")
    print(f"{'='*60}")
    print(f"Data config: {data_yaml}")
    print(f"Base model: {model}")
    print(f"Epochs: {epochs}")
    print(f"Image size: {imgsz}")
    print(f"Batch size: {batch}")
    print(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    print(f"{'='*60}\n")
    
    # Load a pretrained model
    model = YOLO(model)
    
    # Train the model
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=patience,
        save=True,
        project=save_dir,
        name='my_face_model',
        
        hsv_h=0.015,  # Image HSV-Hue augmentation
        hsv_s=0.7,    # Image HSV-Saturation augmentation
        hsv_v=0.4,    # Image HSV-Value augmentation
        degrees=0.0,  # Image rotation (+/- deg)
        translate=0.1,  # Image translation (+/- fraction)
        scale=0.5,    # Image scale (+/- gain)
        shear=0.0,    # Image shear (+/- deg)
        perspective=0.0,  # Image perspective (+/- fraction)
        flipud=0.0,   # Image flip up-down (probability)
        fliplr=0.5,   # Image flip left-right (probability)
        mosaic=1.0,   # Image mosaic (probability)
        mixup=0.0,    # Image mixup (probability)
        
        workers=8,
        verbose=True,
        save_period=10,
    )
    
    print(f"\n{'='*60}")
    print("Training complete!")
    print(f"{'='*60}")
    print(f"Best model saved to: {save_dir}/my_face_model/weights/best.pt")
    print(f"Last model saved to: {save_dir}/my_face_model/weights/last.pt")
    print(f"\nTo use your trained model:")
    print(f"python yolo_face_detection.py --model {save_dir}/my_face_model/weights/best.pt")
    print(f"{'='*60}\n")
    
    return results

def validate_model(model_path, data_yaml='face_dataset.yaml'):
    """
    Validate trained model
    
    Args:
        model_path: Path to trained model weights
        data_yaml: Path to dataset configuration file
    """
    print(f"\nValidating model: {model_path}")
    model = YOLO(model_path)
    results = model.val(data=data_yaml)
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Train YOLOv8 face recognition model')
    parser.add_argument('--data', type=str, default='face_dataset.yaml',
                        help='Path to dataset YAML file')
    parser.add_argument('--model', type=str, default='yolov8n.pt',
                        help='Base model (yolov8n.pt, yolov8s.pt, yolov8m.pt, etc.)')
    parser.add_argument('--epochs', type=int, default=100,
                        help='Number of training epochs')
    parser.add_argument('--imgsz', type=int, default=640,
                        help='Input image size')
    parser.add_argument('--batch', type=int, default=16,
                        help='Batch size')
    parser.add_argument('--patience', type=int, default=20,
                        help='Early stopping patience')
    parser.add_argument('--validate', action='store_true',
                        help='Validate model after training')
    
    args = parser.parse_args()
    
    results = train_face_model(
        data_yaml=args.data,
        model=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience
    )
    
    if args.validate:
        validate_model('runs/face_detection/my_face_model/weights/best.pt', args.data)