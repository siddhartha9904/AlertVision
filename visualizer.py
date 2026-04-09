"""
AlertVision — Frame Visualizer
Draws bounding boxes, labels, and status overlays on frames.
"""

import cv2
import config


class Visualizer:
    """Draws detection results onto video frames."""

    def draw(self, frame, analysis_result, fsm_state):
        """Draw bounding boxes and status overlay on a frame.

        Args:
            frame: BGR numpy array (will be modified in place)
            analysis_result: dict from AggressionAnalyzer
            fsm_state: str from StateMachine

        Returns:
            frame with overlays drawn
        """
        h, w = frame.shape[:2]
        regions = analysis_result.get("regions", [])

        # Draw bounding boxes for each detected region
        for region in regions:
            threat = region.get("threat_level", "normal")
            label = region.get("label", "Person")
            bbox = region.get("bbox", [])

            if len(bbox) != 4:
                continue

            # Convert relative coords (0-1) to pixel coords
            x1 = int(bbox[0] * w)
            y1 = int(bbox[1] * h)
            x2 = int(bbox[2] * w)
            y2 = int(bbox[3] * h)

            # Clamp to frame bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            color = config.COLORS.get(threat, config.COLORS["normal"])

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, config.BOX_THICKNESS)

            # Draw label background
            label_text = f"{label} [{threat.upper()}]"
            (tw, th), _ = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE, 1
            )
            cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 4, y1), color, -1)
            cv2.putText(
                frame, label_text, (x1 + 2, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, config.FONT_SCALE,
                (255, 255, 255), 1, cv2.LINE_AA,
            )

        # ── Status bar overlay at top ──────────────────────
        self._draw_status_bar(frame, analysis_result, fsm_state)

        return frame

    def _draw_status_bar(self, frame, analysis_result, fsm_state):
        """Draw a status bar at the top of the frame."""
        h, w = frame.shape[:2]
        status = analysis_result.get("status", "normal")
        confidence = analysis_result.get("confidence", 0.0)
        description = analysis_result.get("description", "")

        bar_color = config.COLORS.get(status, config.COLORS["normal"])

        # Semi-transparent dark bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 60), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # State indicator dot
        cv2.circle(frame, (20, 20), 8, bar_color, -1)

        # State text
        state_text = f"State: {fsm_state}"
        cv2.putText(
            frame, state_text, (35, 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA,
        )

        # Confidence bar
        conf_text = f"Confidence: {confidence:.0%}"
        cv2.putText(
            frame, conf_text, (35, 48),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA,
        )

        # Confidence meter
        bar_x = 220
        bar_w = 150
        cv2.rectangle(frame, (bar_x, 38), (bar_x + bar_w, 52), (60, 60, 60), -1)
        filled = int(bar_w * confidence)
        cv2.rectangle(frame, (bar_x, 38), (bar_x + filled, 52), bar_color, -1)

        # Description (truncated)
        if description:
            desc = description[:60] + ("..." if len(description) > 60 else "")
            cv2.putText(
                frame, desc, (400, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1, cv2.LINE_AA,
            )

    def draw_waiting(self, frame):
        """Draw a 'waiting for analysis' overlay."""
        h, w = frame.shape[:2]
        cv2.putText(
            frame, "Analyzing...", (w // 2 - 60, h // 2),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2, cv2.LINE_AA,
        )
        return frame
