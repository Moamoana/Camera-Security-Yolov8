"""
Security System Control Panel
Manage logs, data, and system settings
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

class SecurityControl:
    def __init__(self, log_file='security_log.json', images_dir='security_images'):
        self.log_file = log_file
        self.images_dir = images_dir
    
    def show_menu(self):
        """Display control menu"""
        print("\n" + "="*70)
        print("SECURITY SYSTEM CONTROL PANEL")
        print("="*70)
        print("1. View Statistics")
        print("2. Delete All Logs")
        print("3. Delete Old Logs (specify days)")
        print("4. Delete All Images")
        print("5. Delete Old Images (specify days)")
        print("6. View Recent Alerts")
        print("7. Export Report")
        print("8. Clear Everything (logs + images)")
        print("9. Show Storage Usage")
        print("0. Exit")
        print("="*70)
    
    def get_log_data(self):
        """Load log data"""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_log_data(self, data):
        """Save log data"""
        with open(self.log_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def view_statistics(self):
        """Show system statistics"""
        logs = self.get_log_data()
        
        if not logs:
            print("\n❌ No data found")
            return
        
        total = len(logs)
        known = sum(1 for l in logs if l['type'] == 'known')
        unknown = sum(1 for l in logs if l['type'] == 'unknown')
        
        # 24h stats
        now = datetime.now()
        cutoff_24h = now - timedelta(hours=24)
        unknown_24h = sum(1 for l in logs 
                         if l['type'] == 'unknown' 
                         and datetime.fromisoformat(l['timestamp']) > cutoff_24h)
        
        # Count images
        image_count = 0
        image_size = 0
        if os.path.exists(self.images_dir):
            for f in Path(self.images_dir).glob('**/*.jpg'):
                image_count += 1
                image_size += f.stat().st_size
        
        print("\n" + "="*70)
        print("SYSTEM STATISTICS")
        print("="*70)
        print(f"Total Detections: {total}")
        print(f"  ✅ Known: {known} ({known/total*100:.1f}%)")
        print(f"  🚨 Unknown: {unknown} ({unknown/total*100:.1f}%)")
        print(f"\n24-Hour Statistics:")
        print(f"  🚨 Unknown alerts: {unknown_24h}")
        print(f"\nStorage:")
        print(f"  Saved images: {image_count}")
        print(f"  Storage used: {image_size / (1024*1024):.2f} MB")
        
        if logs:
            print(f"\nFirst detection: {logs[0]['date']} {logs[0]['time']}")
            print(f"Last detection: {logs[-1]['date']} {logs[-1]['time']}")
        
        print("="*70)
    
    def delete_all_logs(self):
        """Delete all log data"""
        confirm = input("\n⚠️  Delete ALL logs? This cannot be undone! (yes/no): ")
        
        if confirm.lower() == 'yes':
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
                print("✅ All logs deleted")
            else:
                print("❌ No logs to delete")
        else:
            print("❌ Cancelled")
    
    def delete_old_logs(self, days):
        """Delete logs older than specified days"""
        logs = self.get_log_data()
        
        if not logs:
            print("❌ No logs to delete")
            return
        
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        filtered = []
        removed = 0
        
        for log in logs:
            try:
                log_time = datetime.fromisoformat(log['timestamp'])
                if log_time > cutoff:
                    filtered.append(log)
                else:
                    removed += 1
            except:
                filtered.append(log)
        
        if removed > 0:
            confirm = input(f"\n⚠️  Delete {removed} old logs (>{days} days)? (yes/no): ")
            if confirm.lower() == 'yes':
                self.save_log_data(filtered)
                print(f"✅ Deleted {removed} old logs")
            else:
                print("❌ Cancelled")
        else:
            print(f"✅ No logs older than {days} days")
    
    def delete_all_images(self):
        """Delete all saved images"""
        if not os.path.exists(self.images_dir):
            print("❌ No images directory found")
            return
        
        image_count = len(list(Path(self.images_dir).glob('**/*.jpg')))
        
        if image_count == 0:
            print("❌ No images to delete")
            return
        
        confirm = input(f"\n⚠️  Delete ALL {image_count} images? This cannot be undone! (yes/no): ")
        
        if confirm.lower() == 'yes':
            shutil.rmtree(self.images_dir)
            print(f"✅ Deleted {image_count} images")
        else:
            print("❌ Cancelled")
    
    def delete_old_images(self, days):
        """Delete images older than specified days"""
        if not os.path.exists(self.images_dir):
            print("❌ No images directory found")
            return
        
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        removed = 0
        total_size = 0
        
        for img_path in Path(self.images_dir).glob('**/*.jpg'):
            # Check file modification time
            mtime = datetime.fromtimestamp(img_path.stat().st_mtime)
            if mtime < cutoff:
                removed += 1
                total_size += img_path.stat().st_size
        
        if removed > 0:
            confirm = input(f"\n⚠️  Delete {removed} old images (>{days} days, {total_size/(1024*1024):.2f} MB)? (yes/no): ")
            if confirm.lower() == 'yes':
                deleted = 0
                for img_path in Path(self.images_dir).glob('**/*.jpg'):
                    mtime = datetime.fromtimestamp(img_path.stat().st_mtime)
                    if mtime < cutoff:
                        img_path.unlink()
                        deleted += 1
                print(f"✅ Deleted {deleted} old images")
            else:
                print("❌ Cancelled")
        else:
            print(f"✅ No images older than {days} days")
    
    def view_recent_alerts(self, count=10):
        """Show recent unknown person alerts"""
        logs = self.get_log_data()
        
        unknown_logs = [l for l in logs if l['type'] == 'unknown']
        
        if not unknown_logs:
            print("\n✅ No unknown person alerts")
            return
        
        recent = unknown_logs[-count:]
        
        print("\n" + "="*70)
        print(f"RECENT UNKNOWN PERSON ALERTS (Last {len(recent)})")
        print("="*70)
        
        for i, log in enumerate(reversed(recent), 1):
            print(f"{i}. {log['date']} {log['time']} - Confidence: {log['confidence']:.2f}")
        
        print("="*70)
    
    def export_report(self, output_file='security_report.txt'):
        """Export detailed report"""
        logs = self.get_log_data()
        
        if not logs:
            print("❌ No data to export")
            return
        
        now = datetime.now()
        
        with open(output_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("SECURITY SYSTEM REPORT\n")
            f.write("="*70 + "\n")
            f.write(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Detections: {len(logs)}\n")
            f.write("="*70 + "\n\n")
            
            # Unknown alerts
            unknown = [l for l in logs if l['type'] == 'unknown']
            f.write(f"UNKNOWN PERSON ALERTS: {len(unknown)}\n")
            f.write("-"*70 + "\n")
            for log in unknown:
                f.write(f"{log['date']} {log['time']} - Confidence: {log['confidence']:.2f}\n")
            
            f.write("\n" + "="*70 + "\n\n")
            
            # Known detections
            known = [l for l in logs if l['type'] == 'known']
            f.write(f"KNOWN PERSON DETECTIONS: {len(known)}\n")
            f.write("-"*70 + "\n")
            if known:
                f.write(f"First: {known[0]['date']} {known[0]['time']}\n")
                f.write(f"Last: {known[-1]['date']} {known[-1]['time']}\n")
        
        print(f"✅ Report exported to {output_file}")
    
    def clear_everything(self):
        """Delete all data"""
        confirm = input("\n⚠️  DELETE EVERYTHING (logs + images)? This cannot be undone! Type 'DELETE' to confirm: ")
        
        if confirm == 'DELETE':
            # Delete logs
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
                print("✅ Logs deleted")
            
            # Delete images
            if os.path.exists(self.images_dir):
                shutil.rmtree(self.images_dir)
                print("✅ Images deleted")
            
            print("✅ All data cleared")
        else:
            print("❌ Cancelled")
    
    def show_storage_usage(self):
        """Show detailed storage usage"""
        # Log file size
        log_size = 0
        log_count = 0
        if os.path.exists(self.log_file):
            log_size = os.path.getsize(self.log_file)
            with open(self.log_file, 'r') as f:
                log_count = len(json.load(f))
        
        # Images
        image_count = 0
        image_size = 0
        if os.path.exists(self.images_dir):
            for f in Path(self.images_dir).glob('**/*.jpg'):
                image_count += 1
                image_size += f.stat().st_size
        
        print("\n" + "="*70)
        print("STORAGE USAGE")
        print("="*70)
        print(f"Log File:")
        print(f"  Entries: {log_count}")
        print(f"  Size: {log_size / 1024:.2f} KB")
        print(f"\nImages:")
        print(f"  Count: {image_count}")
        print(f"  Total size: {image_size / (1024*1024):.2f} MB")
        print(f"  Average size: {(image_size/image_count)/(1024) if image_count > 0 else 0:.2f} KB")
        print(f"\nTotal Storage: {(log_size + image_size) / (1024*1024):.2f} MB")
        print("="*70)
    
    def run(self):
        """Run control panel"""
        while True:
            self.show_menu()
            choice = input("\nSelect option (0-9): ")
            
            if choice == '1':
                self.view_statistics()
            elif choice == '2':
                self.delete_all_logs()
            elif choice == '3':
                days = int(input("Delete logs older than how many days? "))
                self.delete_old_logs(days)
            elif choice == '4':
                self.delete_all_images()
            elif choice == '5':
                days = int(input("Delete images older than how many days? "))
                self.delete_old_images(days)
            elif choice == '6':
                count = int(input("How many recent alerts to show? (default 10): ") or "10")
                self.view_recent_alerts(count)
            elif choice == '7':
                filename = input("Export filename (default: security_report.txt): ") or "security_report.txt"
                self.export_report(filename)
            elif choice == '8':
                self.clear_everything()
            elif choice == '9':
                self.show_storage_usage()
            elif choice == '0':
                print("\n👋 Exiting control panel")
                break
            else:
                print("\n❌ Invalid option")
            
            input("\nPress Enter to continue...")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Security System Control Panel')
    parser.add_argument('--log', type=str, default='security_log.json',
                       help='Path to log file')
    parser.add_argument('--images', type=str, default='security_images',
                       help='Path to images directory')
    
    args = parser.parse_args()
    
    control = SecurityControl(args.log, args.images)
    control.run()


if __name__ == "__main__":
    main()