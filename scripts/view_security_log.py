"""
Security Log Viewer
View and analyze security system logs
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

class SecurityLogViewer:
    def __init__(self, log_file='security_log.json'):
        self.log_file = log_file
        self.detections = self.load_log()
    
    def load_log(self):
        """Load detection log"""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        return []
    
    def show_24h_report(self):
        """Show 24-hour detection report"""
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        
        unknown_detections = []
        known_detections = []
        
        for detection in self.detections:
            try:
                detection_time = datetime.fromisoformat(detection['timestamp'])
                if detection_time > cutoff:
                    if detection['type'] == 'unknown':
                        unknown_detections.append(detection)
                    else:
                        known_detections.append(detection)
            except:
                continue
        
        print("\n" + "="*70)
        print("24-HOUR SECURITY REPORT")
        print("="*70)
        print(f"Report Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Period: Last 24 hours")
        print("="*70)
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total Detections: {len(unknown_detections) + len(known_detections)}")
        print(f"  ✅ Known Persons: {len(known_detections)}")
        print(f"  🚨 Unknown Persons: {len(unknown_detections)}")
        
        if unknown_detections:
            print(f"\n⚠️  ALERTS: {len(unknown_detections)} unknown person detections")
            print("\n🚨 UNKNOWN PERSON DETECTIONS:")
            print("-" * 70)
            
            for i, detection in enumerate(unknown_detections, 1):
                print(f"{i}. {detection['date']} {detection['time']} - "
                      f"Confidence: {detection['confidence']:.2f}")
        else:
            print("\n✅ NO UNKNOWN PERSONS DETECTED (All Clear)")
        
        if known_detections:
            print(f"\n✅ KNOWN PERSON DETECTIONS:")
            print("-" * 70)
            print(f"First seen: {known_detections[0]['date']} {known_detections[0]['time']}")
            print(f"Last seen: {known_detections[-1]['date']} {known_detections[-1]['time']}")
            print(f"Total appearances: {len(known_detections)}")
        
        print("="*70 + "\n")
    
    def show_hourly_breakdown(self):
        """Show hourly breakdown of detections"""
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        
        hourly_unknown = defaultdict(int)
        hourly_known = defaultdict(int)
        
        for detection in self.detections:
            try:
                detection_time = datetime.fromisoformat(detection['timestamp'])
                if detection_time > cutoff:
                    hour = detection_time.strftime('%H:00')
                    if detection['type'] == 'unknown':
                        hourly_unknown[hour] += 1
                    else:
                        hourly_known[hour] += 1
            except:
                continue
        
        print("\n" + "="*70)
        print("HOURLY BREAKDOWN (Last 24 Hours)")
        print("="*70)
        
        all_hours = sorted(set(list(hourly_unknown.keys()) + list(hourly_known.keys())))
        
        if not all_hours:
            print("No detections in the last 24 hours")
            return
        
        print(f"{'Hour':<10} {'Known':<10} {'Unknown':<10} {'Total':<10}")
        print("-" * 70)
        
        for hour in all_hours:
            known = hourly_known[hour]
            unknown = hourly_unknown[hour]
            total = known + unknown
            
            unknown_marker = " 🚨" if unknown > 0 else ""
            print(f"{hour:<10} {known:<10} {unknown:<10} {total:<10}{unknown_marker}")
        
        print("="*70 + "\n")
    
    def show_all_time_stats(self):
        """Show all-time statistics"""
        if not self.detections:
            print("No detections logged yet")
            return
        
        total = len(self.detections)
        unknown = sum(1 for d in self.detections if d['type'] == 'unknown')
        known = total - unknown
        
        print("\n" + "="*70)
        print("ALL-TIME STATISTICS")
        print("="*70)
        print(f"Total Detections: {total}")
        print(f"Known Persons: {known} ({known/total*100:.1f}%)")
        print(f"Unknown Persons: {unknown} ({unknown/total*100:.1f}%)")
        
        if self.detections:
            first = self.detections[0]
            last = self.detections[-1]
            print(f"\nFirst Detection: {first['date']} {first['time']}")
            print(f"Last Detection: {last['date']} {last['time']}")
        
        print("="*70 + "\n")
    
    def export_unknown_alerts(self, output_file='unknown_alerts.txt'):
        """Export all unknown person alerts to file"""
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        
        unknown_detections = []
        for detection in self.detections:
            try:
                detection_time = datetime.fromisoformat(detection['timestamp'])
                if detection_time > cutoff and detection['type'] == 'unknown':
                    unknown_detections.append(detection)
            except:
                continue
        
        with open(output_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("UNKNOWN PERSON ALERTS - LAST 24 HOURS\n")
            f.write("="*70 + "\n")
            f.write(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Alerts: {len(unknown_detections)}\n")
            f.write("="*70 + "\n\n")
            
            for i, detection in enumerate(unknown_detections, 1):
                f.write(f"Alert #{i}\n")
                f.write(f"  Date: {detection['date']}\n")
                f.write(f"  Time: {detection['time']}\n")
                f.write(f"  Confidence: {detection['confidence']:.2f}\n")
                f.write("-"*70 + "\n")
        
        print(f"Exported {len(unknown_detections)} alerts to {output_file}")
    
    def clear_old_logs(self, days=7):
        """Clear logs older than specified days"""
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        filtered = []
        removed_count = 0
        
        for detection in self.detections:
            try:
                detection_time = datetime.fromisoformat(detection['timestamp'])
                if detection_time > cutoff:
                    filtered.append(detection)
                else:
                    removed_count += 1
            except:
                filtered.append(detection)
        
        if removed_count > 0:
            self.detections = filtered
            with open(self.log_file, 'w') as f:
                json.dump(self.detections, f, indent=2)
            print(f"Removed {removed_count} old log entries (older than {days} days)")
        else:
            print("No old logs to remove")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Security Log Viewer')
    parser.add_argument('--log', type=str, default='security_log.json',
                       help='Path to log file')
    parser.add_argument('--mode', type=str, 
                       choices=['report', 'hourly', 'alltime', 'export', 'clear'],
                       default='report',
                       help='Display mode')
    parser.add_argument('--output', type=str, default='unknown_alerts.txt',
                       help='Output file for export')
    parser.add_argument('--days', type=int, default=7,
                       help='Days to keep logs (for clear mode)')
    
    args = parser.parse_args()
    
    viewer = SecurityLogViewer(args.log)
    
    if args.mode == 'report':
        viewer.show_24h_report()
    elif args.mode == 'hourly':
        viewer.show_hourly_breakdown()
    elif args.mode == 'alltime':
        viewer.show_all_time_stats()
    elif args.mode == 'export':
        viewer.export_unknown_alerts(args.output)
    elif args.mode == 'clear':
        viewer.clear_old_logs(args.days)


if __name__ == "__main__":
    main()