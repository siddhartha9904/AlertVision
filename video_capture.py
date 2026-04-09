"""
AlertVision — Video Capture & Preprocessing
Handles webcam and video file input with CLAHE enhancement.
"""

import cv2
import numpy as np
import config


class VideoCapture:
    """Captures frames from webcam or video file with preprocessing."""

    def __init__(self, source=None):
        """
        Args:
            source: Webcam index (int) or video file path (str).
                    Defaults to config.WEBCAM_INDEX.
        """
        if source is None:
            source = config.WEBCAM_INDEX

        self.source = source
        self.cap = None
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def open(self):
        """Open the video source."""
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise IOError(f"Cannot open video source: {self.source}")

        # Set resolution for webcam
        if isinstance(self.source, int):
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        print(f"[VideoCapture] Opened source: {self.source}")
        return self

    def read_frame(self):
        """Read and preprocess a single frame.

        Returns:
            tuple: (success: bool, original_frame, preprocessed_frame)
        """
        if self.cap is None:
            raise RuntimeError("VideoCapture not opened. Call open() first.")

        ret, frame = self.cap.read()
        if not ret:
            return False, None, None

        # Resize to standard dimensions
        frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))

        # Preprocess: CLAHE on luminance channel for better visibility
        preprocessed = self._apply_clahe(frame)

        return True, frame, preprocessed

    def _apply_clahe(self, frame):
        """Apply CLAHE histogram equalization to improve contrast."""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        l_channel = self.clahe.apply(l_channel)
        enhanced = cv2.merge([l_channel, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    def get_fps(self):
        """Get source FPS (for video files)."""
        if self.cap:
            return self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        return 30.0

    def release(self):
        """Release the video source."""
        if self.cap:
            self.cap.release()
            print("[VideoCapture] Released.")

    def __enter__(self):
        return self.open()

    def __exit__(self, *args):
        self.release()
