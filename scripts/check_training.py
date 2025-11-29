"""
Check Training Status and Provide Next Steps
"""

import os
from pathlib import Path

def check_training_status():
    """Check if model training is complete and provide guidance"""
    
    print("\n" + "="*60)
    print("TRAINING STATUS CHECK")
    print("="*60)
    
    # Check dataset
    dataset_images = Path("dataset/images/train")
    dataset_labels = Path("dataset/labels/train")
    
    if dataset_images.exists() and dataset_labels.exists():
        train_images = len(list(dataset_images.glob("*.jpg"))) + len(list(dataset_images.glob("*.png")))
        train_labels = len(list(dataset_labels.glob("*.txt")))
        print(f"✓ Dataset ready: {train_images} images, {train_labels} labels")
    else:
        print("✗ Dataset not organized yet")
        print("  Run: python organize_dataset.py")
        return
    
    # Check for trained models
    best_model = Path("runs/face_detection/my_face_model/weights/best.pt")
    last_model = Path("runs/face_detection/my_face_model/weights/last.pt")
    
    if best_model.exists():
        model_size = best_model.stat().st_size / (1024 * 1024)  # MB
        print(f"✓ Training COMPLETE!")
        print(f"  Best model: {best_model} ({model_size:.1f} MB)")
        print("\n" + "="*60)
        print("NEXT STEP: Test your model")
        print("="*60)
        print(f"python yolo_face_detection.py --model {best_model}")
        print("="*60)
    elif last_model.exists():
        print("⚠ Training IN PROGRESS or INTERRUPTED")
        print(f"  Last checkpoint: {last_model}")
        print("\nOptions:")
        print("1. Resume training:")
        print("   python train_face_model.py --epochs 50 --batch 8")
        print("\n2. Use last checkpoint (not recommended):")
        print(f"   python yolo_face_detection.py --model {last_model}")
    else:
        print("✗ Training NOT started or FAILED")
        print("\n" + "="*60)
        print("NEXT STEP: Start training")
        print("="*60)
        print("For CPU (faster training):")
        print("  python train_face_model.py --epochs 50 --batch 8 --imgsz 416")
        print("\nFor GPU (better quality):")
        print("  python train_face_model.py --epochs 100 --batch 16")
        print("="*60)
        
        # Check for any training logs
        runs_dir = Path("runs/face_detection")
        if runs_dir.exists():
            subdirs = [d for d in runs_dir.iterdir() if d.is_dir()]
            if subdirs:
                print(f"\nFound {len(subdirs)} previous training attempt(s)")
                print("Training logs in:", runs_dir)
    
    print()

if __name__ == "__main__":
    check_training_status()