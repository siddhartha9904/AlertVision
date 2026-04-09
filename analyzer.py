"""
AlertVision — Gemini Flash Vision Analyzer
Sends frames to Gemini 2.0 Flash for aggression detection.
"""

import base64
import json
import io
import cv2
import numpy as np
from PIL import Image
from google import genai
from google.genai import types
import config


# Structured prompt for Gemini Vision
ANALYSIS_PROMPT = """You are a real-time video surveillance aggression detection system called AlertVision.

Analyze this frame for signs of physical aggression, fighting, threatening gestures, or hostile behavior.

Respond ONLY with valid JSON in this exact format:
{
    "status": "normal" | "suspicious" | "aggressive",
    "confidence": 0.0 to 1.0,
    "description": "brief description of what you see",
    "regions": [
        {
            "label": "description of person/action",
            "bbox": [x1, y1, x2, y2],
            "threat_level": "normal" | "suspicious" | "aggressive"
        }
    ]
}

Rules:
- bbox coordinates are relative (0.0 to 1.0) as fractions of image width/height
- "normal" = peaceful behavior, no threat
- "suspicious" = unusual body language, raised voices posture, tense interaction
- "aggressive" = active fighting, hitting, pushing, threatening gestures with clear hostile intent
- If no people are visible, return status "normal" with empty regions
- Be conservative — only flag "aggressive" when there is CLEAR physical violence
- Always return valid JSON, nothing else"""


class AggressionAnalyzer:
    """Analyzes frames for aggression using Gemini 2.0 Flash Vision."""

    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model = config.GEMINI_MODEL
        print(f"[Analyzer] Initialized with model: {self.model}")

    def analyze_frame(self, frame):
        """Send a frame to Gemini Flash for aggression analysis.

        Args:
            frame: BGR numpy array (OpenCV frame)

        Returns:
            dict with keys: status, confidence, description, regions
        """
        try:
            # Convert BGR (OpenCV) to RGB, then to PIL Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)

            # Call Gemini Vision
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_image(pil_image),
                            types.Part.from_text(ANALYSIS_PROMPT),
                        ],
                    )
                ],
            )

            # Parse the JSON response
            return self._parse_response(response.text)

        except Exception as e:
            print(f"[Analyzer] Error: {e}")
            return self._default_response(str(e))

    def _parse_response(self, text):
        """Parse Gemini's JSON response."""
        try:
            # Clean up response — sometimes Gemini wraps in markdown code blocks
            cleaned = text.strip()
            if cleaned.startswith("```"):
                # Remove markdown code fences
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])

            result = json.loads(cleaned)

            # Validate required fields
            result.setdefault("status", "normal")
            result.setdefault("confidence", 0.0)
            result.setdefault("description", "")
            result.setdefault("regions", [])

            return result

        except json.JSONDecodeError:
            print(f"[Analyzer] Failed to parse JSON: {text[:200]}")
            return self._default_response("JSON parse error")

    def _default_response(self, error_msg=""):
        """Return a safe default when analysis fails."""
        return {
            "status": "normal",
            "confidence": 0.0,
            "description": f"Analysis unavailable: {error_msg}",
            "regions": [],
        }
