from ultralytics import YOLO
import cv2
import os
from pathlib import Path

def auto_annotate_faces(image_dir, output_label_dir, model_path='yolov8n-face.pt', conf_threshold=0.5):
    """
    Automatically annotate faces in images using YOLOv8
    
    Args:
        image_dir: Directory containing images
        output_label_dir: Directory to save YOLO format labels
        model_path: Path to YOLO model for detection
        conf_threshold: Confidence threshold for detections
    """
    os.makedirs(output_label_dir, exist_ok=True)
    
    print(f"Loading model: {model_path}")
    try:
        model = YOLO(model_path)
    except:
        print(f"Could not load {model_path}, using yolov8n.pt instead")
        model = YOLO('yolov8n.pt')
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    image_files = []
    for ext in image_extensions:
        image_files.extend(Path(image_dir).glob(f'*{ext}'))
    
    print(f"\nFound {len(image_files)} images in {image_dir}")
    print(f"Annotating with confidence threshold: {conf_threshold}")
    print(f"Saving labels to: {output_label_dir}\n")
    
    annotated_count = 0
    no_detection_count = 0
    
    for img_path in image_files:
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"Could not read: {img_path}")
            continue
        
        height, width = img.shape[:2]
        results = model(img, conf=conf_threshold, verbose=False)
        boxes = results[0].boxes
        
        if len(boxes) == 0:
            no_detection_count += 1
            print(f"No face detected: {img_path.name}")
            continue
        
        label_file = os.path.join(output_label_dir, img_path.stem + '.txt')
        
        with open(label_file, 'w') as f:
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                x_center = ((x1 + x2) / 2) / width
                y_center = ((y1 + y2) / 2) / height
                w = (x2 - x1) / width
                h = (y2 - y1) / height
                
                f.write(f"0 {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")
        
        annotated_count += 1
        if annotated_count % 10 == 0:
            print(f"Annotated: {annotated_count}/{len(image_files)}")
    
    print(f"\n{'='*60}")
    print(f"Auto-annotation complete!")
    print(f"Total images: {len(image_files)}")
    print(f"Successfully annotated: {annotated_count}")
    print(f"No face detected: {no_detection_count}")
    print(f"Labels saved to: {output_label_dir}")
    print(f"{'='*60}\n")
    
    if no_detection_count > 0:
        print(f"WARNING: {no_detection_count} images had no face detected.")
        print("You may want to review these images or lower the confidence threshold.\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto-annotate faces in dataset')
    parser.add_argument('--images', type=str, default='dataset/my_face',
                        help='Directory containing images')
    parser.add_argument('--labels', type=str, default='dataset/labels',
                        help='Output directory for labels')
    parser.add_argument('--model', type=str, default='yolov8n.pt',
                        help='YOLO model to use for detection')
    parser.add_argument('--conf', type=float, default=0.3,
                        help='Confidence threshold')
    
    args = parser.parse_args()
    
    auto_annotate_faces(args.images, args.labels, args.model, args.conf)