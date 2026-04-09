"""
AlertVision — Alert Logger
Logs aggressive incidents with timestamps and frame snapshots.
"""

import os
import cv2
import time
from datetime import datetime
import config


class AlertLogger:
    """Logs aggression alerts with frame snapshots."""

    def __init__(self):
        self.log_dir = config.LOG_DIR
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "incidents.log")
        self.alert_count = 0
        print(f"[AlertLogger] Logging to: {os.path.abspath(self.log_dir)}")

    def log_alert(self, frame, analysis_result):
        """Log an aggressive incident.

        Args:
            frame: BGR numpy array — the suspicious frame
            analysis_result: dict from AggressionAnalyzer
        """
        self.alert_count += 1
        timestamp = datetime.now()
        ts_str = timestamp.strftime("%Y%m%d_%H%M%S")

        # Save frame snapshot
        snapshot_path = os.path.join(self.log_dir, f"alert_{ts_str}_{self.alert_count}.jpg")
        cv2.imwrite(snapshot_path, frame)

        # Write to log file
        status = analysis_result.get("status", "unknown")
        confidence = analysis_result.get("confidence", 0.0)
        description = analysis_result.get("description", "")

        log_entry = (
            f"[{timestamp.isoformat()}] "
            f"ALERT #{self.alert_count} | "
            f"Status: {status} | "
            f"Confidence: {confidence:.2%} | "
            f"Description: {description} | "
            f"Snapshot: {snapshot_path}\n"
        )

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

        print(f"[AlertLogger] 🚨 ALERT #{self.alert_count}: {description}")
        print(f"[AlertLogger] Snapshot saved: {snapshot_path}")

        return snapshot_path

    def get_alert_count(self):
        return self.alert_count
