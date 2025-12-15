"""
Image Manager
Handles image storage, cleanup, and compression
Automatically archives/deletes images after 6 hours
"""

import os
import cv2
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import threading
import time

logger = logging.getLogger(__name__)

class ImageManager:
    def __init__(self, base_dir="security_images", archive_hours=6, 
                 cleanup_interval_minutes=30):
        self.base_dir = Path(base_dir)
        self.archive_hours = archive_hours
        self.cleanup_interval = cleanup_interval_minutes * 60
        
        # Create directory structure
        self.recent_dir = self.base_dir / "recent"
        self.archived_dir = self.base_dir / "archived"
        
        self.recent_unknown = self.recent_dir / "unknown"
        self.recent_known = self.recent_dir / "known"
        self.archived_unknown = self.archived_dir / "unknown"
        self.archived_known = self.archived_dir / "known"
        
        for directory in [self.recent_unknown, self.recent_known, 
                         self.archived_unknown, self.archived_known]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Start cleanup thread
        self.cleanup_thread = None
        self.stop_cleanup = False
        self.start_cleanup_thread()
    
    def save_image(self, image, person_type: str = "unknown", 
                   metadata: dict = None) -> str:
        """
        Save image to recent directory
        Returns: filepath
        """
        try:
            # Determine directory
            if person_type == "unknown":
                save_dir = self.recent_unknown
            else:
                save_dir = self.recent_known
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{person_type}_{timestamp}.jpg"
            filepath = save_dir / filename
            
            # Save image
            cv2.imwrite(str(filepath), image, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Save metadata if provided
            if metadata:
                metadata_file = filepath.with_suffix('.json')
                import json
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            logger.info(f"Image saved: {filepath.name}")
            return str(filepath)
        
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return None
    
    def get_images(self, person_type: str = "all", limit: int = 50, 
                   include_archived: bool = False) -> List[Dict]:
        """
        Get list of images
        """
        images = []
        
        # Determine directories to scan
        directories = []
        if person_type == "unknown" or person_type == "all":
            directories.append(('recent', 'unknown', self.recent_unknown))
            if include_archived:
                directories.append(('archived', 'unknown', self.archived_unknown))
        
        if person_type == "known" or person_type == "all":
            directories.append(('recent', 'known', self.recent_known))
            if include_archived:
                directories.append(('archived', 'known', self.archived_known))
        
        # Scan directories
        for location, ptype, directory in directories:
            if not directory.exists():
                continue
            
            for img_file in sorted(directory.glob("*.jpg"), reverse=True):
                if len(images) >= limit:
                    break
                
                # Get file info
                stat = img_file.stat()
                timestamp = datetime.fromtimestamp(stat.st_mtime)
                
                # Load metadata if exists
                metadata_file = img_file.with_suffix('.json')
                metadata = {}
                if metadata_file.exists():
                    import json
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                images.append({
                    'filename': img_file.name,
                    'filepath': str(img_file),
                    'type': ptype,
                    'location': location,
                    'timestamp': timestamp.isoformat(),
                    'size': stat.st_size,
                    'metadata': metadata
                })
        
        return images[:limit]
    
    def delete_image(self, filename: str) -> bool:
        """Delete an image file"""
        try:
            # Search in all directories
            for directory in [self.recent_unknown, self.recent_known, 
                            self.archived_unknown, self.archived_known]:
                filepath = directory / filename
                if filepath.exists():
                    filepath.unlink()
                    
                    # Delete metadata if exists
                    metadata_file = filepath.with_suffix('.json')
                    if metadata_file.exists():
                        metadata_file.unlink()
                    
                    logger.info(f"Deleted image: {filename}")
                    return True
            
            logger.warning(f"Image not found: {filename}")
            return False
        
        except Exception as e:
            logger.error(f"Failed to delete image {filename}: {e}")
            return False
    
    def compress_image(self, filepath: Path, quality: int = 60, resize_factor: float = 0.5) -> bool:
        """
        Compress image (reduce quality and size)
        """
        try:
            # Read image
            image = cv2.imread(str(filepath))
            if image is None:
                return False
            
            # Resize
            if resize_factor < 1.0:
                height, width = image.shape[:2]
                new_size = (int(width * resize_factor), int(height * resize_factor))
                image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
            
            # Save with lower quality
            cv2.imwrite(str(filepath), image, [cv2.IMWRITE_JPEG_QUALITY, quality])
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to compress {filepath}: {e}")
            return False
    
    def archive_old_images(self):
        """
        Move images older than archive_hours to archived directory
        - Unknown: Compress and keep
        - Known: Delete
        """
        cutoff_time = datetime.now() - timedelta(hours=self.archive_hours)
        
        archived_count = 0
        deleted_count = 0
        compressed_count = 0
        
        # Process unknown images (compress and archive)
        for img_file in self.recent_unknown.glob("*.jpg"):
            try:
                mtime = datetime.fromtimestamp(img_file.stat().st_mtime)
                
                if mtime < cutoff_time:
                    # Move to archived
                    dest_file = self.archived_unknown / img_file.name
                    shutil.move(str(img_file), str(dest_file))
                    
                    # Compress
                    if self.compress_image(dest_file, quality=60, resize_factor=0.5):
                        compressed_count += 1
                    
                    # Move metadata if exists
                    metadata_file = img_file.with_suffix('.json')
                    if metadata_file.exists():
                        dest_metadata = self.archived_unknown / metadata_file.name
                        shutil.move(str(metadata_file), str(dest_metadata))
                    
                    archived_count += 1
            
            except Exception as e:
                logger.error(f"Failed to archive {img_file}: {e}")
        
        # Process known images (delete)
        for img_file in self.recent_known.glob("*.jpg"):
            try:
                mtime = datetime.fromtimestamp(img_file.stat().st_mtime)
                
                if mtime < cutoff_time:
                    # Delete
                    img_file.unlink()
                    
                    # Delete metadata if exists
                    metadata_file = img_file.with_suffix('.json')
                    if metadata_file.exists():
                        metadata_file.unlink()
                    
                    deleted_count += 1
            
            except Exception as e:
                logger.error(f"Failed to delete {img_file}: {e}")
        
        if archived_count > 0 or deleted_count > 0:
            logger.info(f"Cleanup: {archived_count} archived (compressed), {deleted_count} deleted")
        
        return {
            'archived': archived_count,
            'deleted': deleted_count,
            'compressed': compressed_count
        }
    
    def start_cleanup_thread(self):
        """Start background cleanup thread"""
        if self.cleanup_thread is not None and self.cleanup_thread.is_alive():
            return
        
        self.stop_cleanup = False
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        logger.info(f"Image cleanup thread started (interval: {self.cleanup_interval/60:.0f} minutes)")
    
    def _cleanup_worker(self):
        """Background worker for automatic cleanup"""
        while not self.stop_cleanup:
            try:
                time.sleep(self.cleanup_interval)
                logger.info("Running automatic image cleanup...")
                self.archive_old_images()
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
    
    def stop_cleanup_thread(self):
        """Stop cleanup thread"""
        self.stop_cleanup = True
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("Image cleanup thread stopped")
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        stats = {
            'recent': {'unknown': 0, 'known': 0},
            'archived': {'unknown': 0, 'known': 0},
            'total_size': 0,
            'total_files': 0
        }
        
        for location, ptype, directory in [
            ('recent', 'unknown', self.recent_unknown),
            ('recent', 'known', self.recent_known),
            ('archived', 'unknown', self.archived_unknown),
            ('archived', 'known', self.archived_known)
        ]:
            if directory.exists():
                files = list(directory.glob("*.jpg"))
                count = len(files)
                size = sum(f.stat().st_size for f in files)
                
                stats[location][ptype] = count
                stats['total_files'] += count
                stats['total_size'] += size
        
        stats['total_size_mb'] = stats['total_size'] / (1024 * 1024)
        
        return stats
    
    def cleanup_all(self, delete_archived: bool = False):
        """
        Emergency cleanup - delete all images
        """
        count = 0
        
        for directory in [self.recent_unknown, self.recent_known]:
            if directory.exists():
                for file in directory.glob("*"):
                    file.unlink()
                    count += 1
        
        if delete_archived:
            for directory in [self.archived_unknown, self.archived_known]:
                if directory.exists():
                    for file in directory.glob("*"):
                        file.unlink()
                        count += 1
        
        logger.info(f"Cleanup all: {count} files deleted")
        return count