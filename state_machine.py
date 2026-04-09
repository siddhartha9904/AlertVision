"""
AlertVision — Behavioral State Machine
Tracks scene state: Neutral → Suspicious → Aggressive → Alert
"""

import time
import config


class BehavioralState:
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    AGGRESSIVE = "aggressive"
    ALERT = "alert"


class StateMachine:
    """Finite State Machine for temporal aggression modeling.

    Prevents flicker by requiring sustained signals before state transitions.
    """

    def __init__(self):
        self.current_state = BehavioralState.NORMAL
        self.state_since = time.time()
        self.aggressive_start = None
        self.alert_triggered = False
        self._history = []  # recent analysis results

    def update(self, analysis_result):
        """Update state based on a new analysis result.

        Args:
            analysis_result: dict from AggressionAnalyzer

        Returns:
            str: current behavioral state
        """
        status = analysis_result.get("status", "normal")
        confidence = analysis_result.get("confidence", 0.0)
        now = time.time()

        # Keep a short history for smoothing
        self._history.append({"status": status, "confidence": confidence, "time": now})
        # Only keep last 5 results
        self._history = self._history[-5:]

        previous_state = self.current_state

        # ── State transitions ──────────────────────────────
        if status == "aggressive" and confidence >= config.AGGRESSION_THRESHOLD:
            if self.aggressive_start is None:
                self.aggressive_start = now

            # Require sustained aggression (> 1 second / multiple frames)
            if now - self.aggressive_start >= 1.0:
                self.current_state = BehavioralState.ALERT
                self.alert_triggered = True
            else:
                self.current_state = BehavioralState.AGGRESSIVE

        elif status == "suspicious" and confidence >= config.CONFIDENCE_THRESHOLD:
            self.current_state = BehavioralState.SUSPICIOUS
            self.aggressive_start = None

        else:
            self.current_state = BehavioralState.NORMAL
            self.aggressive_start = None
            self.alert_triggered = False

        if self.current_state != previous_state:
            self.state_since = now
            print(f"[FSM] State: {previous_state} → {self.current_state}")

        return self.current_state

    def should_alert(self):
        """Check if an alert should be triggered (one-shot per aggressive episode)."""
        if self.alert_triggered:
            self.alert_triggered = False  # Reset after consuming
            return True
        return False

    def get_display_state(self):
        """Get a display-friendly state string."""
        duration = time.time() - self.state_since
        return f"{self.current_state.upper()} ({duration:.0f}s)"

    def reset(self):
        """Reset the state machine."""
        self.current_state = BehavioralState.NORMAL
        self.state_since = time.time()
        self.aggressive_start = None
        self.alert_triggered = False
        self._history.clear()
