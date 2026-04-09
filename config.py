"""
AlertVision Configuration
"""

# ── Gemini API ──────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyCfskTtARpzkoqtb4cuImHcwIYzSnUjQu0"
GEMINI_MODEL = "gemini-2.0-flash"

# ── Video Capture ───────────────────────────────────────────
WEBCAM_INDEX = 0                # Default webcam
FRAME_WIDTH = 640               # Resize width for processing
FRAME_HEIGHT = 480              # Resize height for processing
SAMPLE_INTERVAL_SEC = 2.5       # Analyze 1 frame every N seconds

# ── Detection Thresholds ────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.6      # Minimum confidence to flag as suspicious
AGGRESSION_THRESHOLD = 0.85     # Minimum confidence to flag as aggressive

# ── Visualization ───────────────────────────────────────────
COLORS = {
    "normal":     (0, 200, 0),    # Green  (BGR)
    "suspicious": (0, 220, 255),  # Yellow (BGR)
    "aggressive": (0, 0, 255),    # Red    (BGR)
}
BOX_THICKNESS = 2
FONT_SCALE = 0.6

# ── Alert Logging ───────────────────────────────────────────
LOG_DIR = "alerts"              # Directory to save alert snapshots
