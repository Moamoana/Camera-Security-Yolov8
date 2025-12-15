# test_face_recognition.py
import face_recognition
import numpy as np

# Test 1: Basic dlib check
print("Testing face_recognition installation...")

# Test 2: Try loading an existing known_faces image (if any exist)
import os
known_faces_dir = "known_faces"
if os.path.exists(known_faces_dir):
    for person_dir in os.listdir(known_faces_dir):
        person_path = os.path.join(known_faces_dir, person_dir)
        if os.path.isdir(person_path):
            for img_file in os.listdir(person_path):
                if img_file.endswith('.jpg'):
                    img_path = os.path.join(person_path, img_file)
                    print(f"Testing with existing file: {img_path}")
                    try:
                        img = face_recognition.load_image_file(img_path)
                        print(f"  Loaded: dtype={img.dtype}, shape={img.shape}")
                        encodings = face_recognition.face_encodings(img)
                        print(f"  Encodings: {len(encodings)} faces found")
                    except Exception as e:
                        print(f"  ERROR: {e}")
                    break
            break

# Test 3: Create a simple test image
print("\nTesting with synthetic image...")
test_img = np.zeros((480, 640, 3), dtype=np.uint8)
test_img[:] = (128, 128, 128)  # Gray background
try:
    locations = face_recognition.face_locations(test_img)
    print(f"  face_locations worked: {locations}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\nDlib version check:")
import dlib
print(f"  dlib version: {dlib.__version__}")
print(f"  dlib CUDA: {dlib.DLIB_USE_CUDA}")