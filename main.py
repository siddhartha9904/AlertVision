"""
AlertVision — Real-Time Aggression Detection
=============================================

Main entry point. Captures video from webcam or file,
sends sampled frames to Gemini Flash for analysis,
and displays annotated results with bounding boxes.

Usage:
    python main.py                     # Webcam mode
    python main.py --video path.mp4    # Video file mode

Controls:
    Q / ESC  — Quit
    SPACE    — Pause/Resume
    S        — Save current frame
"""

import argparse
import time
import cv2
import sys

from video_capture import VideoCapture
from analyzer import AggressionAnalyzer
from state_machine import StateMachine
from visualizer import Visualizer
from alert_logger import AlertLogger
import config


def parse_args():
    parser = argparse.ArgumentParser(
        description="AlertVision — Real-Time Aggression Detection"
    )
    parser.add_argument(
        "--video", type=str, default=None,
        help="Path to video file. If not set, uses webcam."
    )
    parser.add_argument(
        "--interval", type=float, default=config.SAMPLE_INTERVAL_SEC,
        help=f"Seconds between analysis frames (default: {config.SAMPLE_INTERVAL_SEC})"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Initialize components ─────────────────────────────
    source = args.video if args.video else config.WEBCAM_INDEX
    capture = VideoCapture(source)
    analyzer = AggressionAnalyzer()
    fsm = StateMachine()
    visualizer = Visualizer()
    logger = AlertLogger()

    print("=" * 55)
    print("  AlertVision — Real-Time Aggression Detection")
    print("=" * 55)
    print(f"  Source   : {'Webcam' if args.video is None else args.video}")
    print(f"  Interval : {args.interval}s between analyses")
    print(f"  Model    : {config.GEMINI_MODEL}")
    print("=" * 55)
    print("  Controls: Q/ESC=Quit | SPACE=Pause | S=Screenshot")
    print("=" * 55)

    # ── Main loop ─────────────────────────────────────────
    last_analysis_result = None
    last_analysis_time = 0
    paused = False
    frame_count = 0

    with capture:
        while True:
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # Q or ESC
                print("\n[AlertVision] Shutting down...")
                break
            elif key == ord(" "):  # Space to pause
                paused = not paused
                print(f"[AlertVision] {'Paused' if paused else 'Resumed'}")
                continue
            elif key == ord("s"):  # Screenshot
                if last_analysis_result:
                    logger.log_alert(frame, last_analysis_result)

            if paused:
                continue

            # Read frame
            success, frame, preprocessed = capture.read_frame()
            if not success:
                if args.video:
                    print("[AlertVision] Video ended.")
                    break
                continue

            frame_count += 1
            now = time.time()

            # ── Sample frame for analysis ─────────────────
            if now - last_analysis_time >= args.interval:
                last_analysis_time = now
                print(f"\n[AlertVision] Analyzing frame #{frame_count}...")

                # Send preprocessed frame to Gemini
                last_analysis_result = analyzer.analyze_frame(preprocessed)

                # Update FSM
                state = fsm.update(last_analysis_result)

                # Check if alert should be triggered
                if fsm.should_alert():
                    logger.log_alert(frame, last_analysis_result)

                status = last_analysis_result.get("status", "normal")
                conf = last_analysis_result.get("confidence", 0.0)
                desc = last_analysis_result.get("description", "")
                print(f"  → Status: {status} | Confidence: {conf:.0%}")
                print(f"  → {desc}")

            # ── Draw visualization ────────────────────────
            display_frame = frame.copy()
            if last_analysis_result:
                fsm_display = fsm.get_display_state()
                visualizer.draw(display_frame, last_analysis_result, fsm_display)
            else:
                visualizer.draw_waiting(display_frame)

            # Show frame
            cv2.imshow("AlertVision", display_frame)

    cv2.destroyAllWindows()
    print(f"\n[AlertVision] Total alerts: {logger.get_alert_count()}")
    print("[AlertVision] Done.")


if __name__ == "__main__":
    main()
