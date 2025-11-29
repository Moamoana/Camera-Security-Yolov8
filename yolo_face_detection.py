"""
YOLOv8 Face Detection for Video/Webcam
"""

from ultralytics import YOLO
import cv2
import argparse

def main(source=0, model_path='yolov8n-face.pt', conf_threshold=0.5):
    """
    Run YOLOv8 face detection on video source
    
    Args:
        source: Video source (0 for webcam, or path to video file)
        model_path: Path to YOLO model weights
        conf_threshold: Confidence threshold for detections
    """
    print(f"Loading model: {model_path}")
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Trying to download YOLOv8n model instead...")
        model = YOLO('yolov8n.pt') 
    
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print(f"Error: Cannot open video source {source}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    print(f"Video source: {source}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps}")
    print("\nPress 'q' to quit, 's' to save screenshot")
    
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        
        if not ret:
            print("End of video or cannot read frame")
            break
        
        results = model(frame, conf=conf_threshold, verbose=False)
        annotated_frame = results[0].plot()
        frame_count += 1
        info_text = f"Frame: {frame_count} | Detections: {len(results[0].boxes)}"
        cv2.putText(annotated_frame, info_text, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow('YOLOv8 Face Detection', annotated_frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Quitting...")
            break
        elif key == ord('s'):
            screenshot_name = f"face_detection_{frame_count}.jpg"
            cv2.imwrite(screenshot_name, annotated_frame)
            print(f"Screenshot saved: {screenshot_name}")
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"\nTotal frames processed: {frame_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='YOLOv8 Face Detection')
    parser.add_argument('--source', type=str, default='0', 
                        help='Video source (0 for webcam, or path to video file)')
    parser.add_argument('--model', type=str, default='yolov8n-face.pt',
                        help='Path to YOLO model weights')
    parser.add_argument('--conf', type=float, default=0.5,
                        help='Confidence threshold (0-1)')
    args = parser.parse_args()
    source = int(args.source) if args.source.isdigit() else args.source
    
    main(source=source, model_path=args.model, conf_threshold=args.conf)