"""
Face Data Collection Script
Captures images from webcam to create a training dataset
"""

import cv2
import os
from datetime import datetime
import time

def collect_face_data(output_dir='dataset/my_face', num_images=200, capture_interval=0.5):
    """
    Collect face images from webcam for training
    
    Args:
        output_dir: Directory to save images
        num_images: Number of images to capture
        capture_interval: Seconds between captures
    """
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Cannot open webcam")
        return
    
    print(f"\n{'='*60}")
    print("FACE DATA COLLECTION")
    print(f"{'='*60}")
    print(f"Output directory: {output_dir}")
    print(f"Target images: {num_images}")
    print(f"Capture interval: {capture_interval}s")
    print(f"\nINSTRUCTIONS:")
    print("- Move your head slowly (left, right, up, down)")
    print("- Try different expressions")
    print("- Vary lighting if possible")
    print("- Get different angles and distances")
    print("\nPress 'SPACE' to start capturing")
    print("Press 'q' to quit early")
    print(f"{'='*60}\n")
    
    captured = 0
    capturing = False
    last_capture_time = 0
    
    while captured < num_images:
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Cannot read frame")
            break
        
        display_frame = frame.copy()
        status = "CAPTURING" if capturing else "PAUSED - Press SPACE to start"
        color = (0, 255, 0) if capturing else (0, 165, 255)
        
        cv2.putText(display_frame, status, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(display_frame, f"Captured: {captured}/{num_images}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        height, width = frame.shape[:2]
        rect_size = 300
        x1 = (width - rect_size) // 2
        y1 = (height - rect_size) // 2
        x2 = x1 + rect_size
        y2 = y1 + rect_size
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(display_frame, "Position face here", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        cv2.imshow('Face Data Collection', display_frame)
        
        current_time = time.time()
        if capturing and (current_time - last_capture_time) >= capture_interval:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"face_{captured:04d}_{timestamp}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            cv2.imwrite(filepath, frame)
            captured += 1
            last_capture_time = current_time
            print(f"Captured: {captured}/{num_images} - {filename}")
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\nCapture stopped by user")
            break
        elif key == ord(' '):
            capturing = not capturing
            status_msg = "STARTED" if capturing else "PAUSED"
            print(f"\nCapture {status_msg}")
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n{'='*60}")
    print(f"Data collection complete!")
    print(f"Total images captured: {captured}")
    print(f"Saved to: {output_dir}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect face images for training')
    parser.add_argument('--output', type=str, default='dataset/my_face',
                        help='Output directory for images')
    parser.add_argument('--num', type=int, default=200,
                        help='Number of images to capture')
    parser.add_argument('--interval', type=float, default=0.5,
                        help='Seconds between captures')
    
    args = parser.parse_args()
    
    collect_face_data(args.output, args.num, args.interval)