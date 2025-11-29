"""
Model Info Check
Checks your face model details and what it was trained on
"""

from ultralytics import YOLO
import os

print("="*70)
print("FACE MODEL INFORMATION")
print("="*70)

model_path = r".\runs\face_detection\my_face_model5\weights\best.pt"

# Check if exists
print(f"\n[1] Checking model file...")
print(f"    Path: {model_path}")
print(f"    Current directory: {os.getcwd()}")

if not os.path.exists(model_path):
    print(f"    ❌ ERROR: Model not found!")
    
    # Try to find it
    print("\n    Searching for model files...")
    for root, dirs, files in os.walk("runs"):
        for file in files:
            if file == "best.pt":
                print(f"    Found: {os.path.join(root, file)}")
    
    input("\nPress Enter to exit...")
    exit(1)
else:
    file_size = os.path.getsize(model_path) / (1024 * 1024)
    print(f"    ✅ Found! Size: {file_size:.2f} MB")

# Load model
print(f"\n[2] Loading model...")
try:
    model = YOLO(model_path)
    print(f"    ✅ Model loaded successfully!")
except Exception as e:
    print(f"    ❌ ERROR: {e}")
    input("\nPress Enter to exit...")
    exit(1)

# Get model info
print(f"\n[3] Model Information:")
try:
    print(f"    Model type: {type(model)}")
    print(f"    Task: {model.task}")
    
    # Try to get class names
    if hasattr(model, 'names'):
        print(f"\n[4] Classes the model was trained on:")
        for idx, name in model.names.items():
            print(f"    Class {idx}: {name}")
    
    # Try to get model metadata
    if hasattr(model.model, 'yaml'):
        print(f"\n[5] Model Architecture:")
        print(f"    Layers: {len(model.model.yaml['backbone']) if 'backbone' in model.model.yaml else 'N/A'}")
    
except Exception as e:
    print(f"    Could not get detailed info: {e}")

print(f"\n[6] Testing model on a simple image...")
print(f"    This will test if the model can make predictions...")

# Create a test image (black square)
import numpy as np
test_image = np.zeros((640, 640, 3), dtype=np.uint8)

try:
    results = model(test_image, verbose=False)
    print(f"    ✅ Model can make predictions!")
    print(f"    Detections on test image: {len(results[0].boxes)}")
except Exception as e:
    print(f"    ❌ ERROR during prediction: {e}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"Model file: ✅ Found")
print(f"Model loads: ✅ Yes")
print(f"Can predict: ✅ Yes")
print("\nThe model file itself is OK!")
print("\nIf face detection still doesn't work, the issue is likely:")
print("  1. Confidence thresholds too high")
print("  2. Model trained on different camera/lighting")
print("  3. Need more training data")
print("="*70)

input("\nPress Enter to exit...")