"""
Dataset Organization Script
Organizes images and labels into train/val splits for YOLOv8 training
"""

import os
import shutil
from pathlib import Path
import random

def organize_dataset(images_dir, labels_dir, output_dir='dataset', train_split=0.8):
    """
    Organize images and labels into train/val structure
    
    Args:
        images_dir: Directory containing images
        labels_dir: Directory containing label files
        output_dir: Output directory for organized dataset
        train_split: Proportion of data for training (0-1)
    """
    
    train_images_dir = os.path.join(output_dir, 'images', 'train')
    val_images_dir = os.path.join(output_dir, 'images', 'val')
    train_labels_dir = os.path.join(output_dir, 'labels', 'train')
    val_labels_dir = os.path.join(output_dir, 'labels', 'val')
    
    for dir_path in [train_images_dir, val_images_dir, train_labels_dir, val_labels_dir]:
        os.makedirs(dir_path, exist_ok=True)
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    image_files = []
    for ext in image_extensions:
        image_files.extend(Path(images_dir).glob(f'*{ext}'))
    
    valid_pairs = []
    for img_path in image_files:
        label_path = Path(labels_dir) / (img_path.stem + '.txt')
        if label_path.exists():
            valid_pairs.append((img_path, label_path))
    
    print(f"\n{'='*60}")
    print("DATASET ORGANIZATION")
    print(f"{'='*60}")
    print(f"Total images found: {len(image_files)}")
    print(f"Valid image-label pairs: {len(valid_pairs)}")
    print(f"Train split: {train_split * 100}%")
    print(f"Val split: {(1 - train_split) * 100}%")
    
    if len(valid_pairs) == 0:
        print("\nERROR: No valid image-label pairs found!")
        print("Make sure your labels directory has .txt files matching your images.")
        return
    
    random.shuffle(valid_pairs)
    split_idx = int(len(valid_pairs) * train_split)
    train_pairs = valid_pairs[:split_idx]
    val_pairs = valid_pairs[split_idx:]
    
    print(f"\nTrain samples: {len(train_pairs)}")
    print(f"Val samples: {len(val_pairs)}")
    print(f"\nCopying files...")
    
    for img_path, label_path in train_pairs:
        shutil.copy2(img_path, os.path.join(train_images_dir, img_path.name))
        shutil.copy2(label_path, os.path.join(train_labels_dir, label_path.name))
    
    for img_path, label_path in val_pairs:
        shutil.copy2(img_path, os.path.join(val_images_dir, img_path.name))
        shutil.copy2(label_path, os.path.join(val_labels_dir, label_path.name))
    
    print(f"\n{'='*60}")
    print("Dataset organization complete!")
    print(f"{'='*60}")
    print(f"\nDataset structure:")
    print(f"{output_dir}/")
    print(f"  ├── images/")
    print(f"  │   ├── train/  ({len(train_pairs)} images)")
    print(f"  │   └── val/    ({len(val_pairs)} images)")
    print(f"  └── labels/")
    print(f"      ├── train/  ({len(train_pairs)} labels)")
    print(f"      └── val/    ({len(val_pairs)} labels)")
    print(f"\nYou can now train with: python train_face_model.py")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Organize dataset for YOLO training')
    parser.add_argument('--images', type=str, default='dataset/my_face',
                        help='Directory containing images')
    parser.add_argument('--labels', type=str, default='dataset/labels',
                        help='Directory containing labels')
    parser.add_argument('--output', type=str, default='dataset',
                        help='Output directory')
    parser.add_argument('--split', type=float, default=0.8,
                        help='Train split ratio (0-1)')
    
    args = parser.parse_args()
    
    organize_dataset(args.images, args.labels, args.output, args.split)