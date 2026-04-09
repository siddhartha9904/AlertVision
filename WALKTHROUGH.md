# AlertVision — Project Walkthrough 🔴

> **Real-Time Aggression Detection using AI Video Analytics**
>
> Authors: B. Karthik Sai, A. Siddhartha, V. Siddhartha

---

## Table of Contents

1. [What Is AlertVision?](#what-is-alertvision)
2. [High-Level Architecture](#high-level-architecture)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Setup & Installation](#setup--installation)
6. [How It Works — End to End](#how-it-works--end-to-end)
7. [Module-by-Module Breakdown](#module-by-module-breakdown)
   - [server.js — Node.js Backend](#serverjs--nodejs-backend)
   - [Frontend (index.html + style.css)](#frontend-indexhtml--stylecss)
   - [Python Modules (Legacy / Desktop Mode)](#python-modules-legacy--desktop-mode)
8. [API Reference](#api-reference)
9. [AI Analysis Pipeline](#ai-analysis-pipeline)
10. [Behavioral State Machine](#behavioral-state-machine)
11. [Email Alert System](#email-alert-system)
12. [Configuration](#configuration)
13. [Key Design Decisions](#key-design-decisions)

---

## What Is AlertVision?

AlertVision is a **real-time aggression detection system** that uses AI-powered video analytics to monitor live webcam feeds or uploaded video files. It analyzes each frame using vision LLMs (Groq Llama 4 Scout / Google Gemini 2.0 Flash) and:

- Classifies scenes as **Normal** 🟢, **Suspicious** 🟡, or **Aggressive** 🔴
- Draws **bounding boxes** around detected people with their threat levels
- Tracks incidents on a **real-time dashboard** with charts and stats
- Sends **email alerts** with captured frames when aggression is detected
- Uses a **finite state machine** to prevent false alarms (requires sustained aggression signals)

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        BROWSER (Client)                      │
│                                                              │
│   ┌─────────────┐   ┌──────────────┐   ┌────────────────┐   │
│   │  Webcam Feed │   │ Video Upload │   │   Dashboard    │   │
│   │  (getUserMe  │   │  (MP4/AVI/   │   │  (Stats,       │   │
│   │   dia API)   │   │   MOV)       │   │   Charts,      │   │
│   └──────┬───────┘   └──────┬───────┘   │   Timeline)    │   │
│          │                  │           └────────────────┘   │
│          │ WebSocket        │ REST API                       │
│          │ (base64 frames)  │ (base64 frames)               │
└──────────┼──────────────────┼────────────────────────────────┘
           │                  │
           ▼                  ▼
┌──────────────────────────────────────────────────────────────┐
│                   NODE.JS SERVER (server.js)                 │
│                                                              │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────────┐    │
│  │  Express    │  │  WebSocket   │  │  State Machine    │    │
│  │  REST API   │  │  Server      │  │  (FSM)            │    │
│  └─────┬──────┘  └──────┬───────┘  └───────────────────┘    │
│        │                │                                    │
│        └───────┬────────┘                                    │
│                ▼                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              AI Analysis Pipeline                     │   │
│  │                                                       │   │
│  │   1. Groq (Llama 4 Scout) ── primary                 │   │
│  │   2. Gemini 2.0 Flash     ── fallback                │   │
│  │                                                       │   │
│  │   Frame → Vision LLM → JSON → Bounding Boxes         │   │
│  └──────────────────────────────────────────────────────┘   │
│                │                                             │
│                ▼                                             │
│  ┌──────────────────────────┐                               │
│  │  Email Alerts (Nodemailer)│                              │
│  │  Gmail SMTP → recipient   │                              │
│  └──────────────────────────┘                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer         | Technology                                               |
|---------------|----------------------------------------------------------|
| **Frontend**  | Vanilla HTML/CSS/JS, Canvas API for bounding boxes       |
| **Backend**   | Node.js + Express + WebSocket (`ws`)                     |
| **AI (Primary)**   | Groq API — `meta-llama/llama-4-scout-17b-16e-instruct` |
| **AI (Fallback)**  | Google Gemini 2.0 Flash (`@google/generative-ai`)      |
| **Email**     | Nodemailer (Gmail SMTP)                                  |
| **Desktop Mode** | Python + OpenCV + FastAPI (legacy, alternative entry point) |

---

## Project Structure

```
alertv/
├── server.js              # Main Node.js backend (Express + WebSocket + AI)
├── package.json           # Node dependencies & scripts
├── .env                   # API keys & config (Gemini, Groq, Gmail)
│
├── frontend/
│   ├── index.html         # Full dashboard UI (webcam, upload, stats, charts)
│   └── style.css          # Dashboard styling (dark theme)
│
├── main.py                # Python CLI entry point (webcam desktop mode)
├── app.py                 # Python FastAPI web server (alternative backend)
├── analyzer.py            # Python Gemini Vision analyzer
├── state_machine.py       # Python behavioral FSM
├── video_capture.py       # Python OpenCV video capture + CLAHE preprocessing
├── visualizer.py          # Python OpenCV frame annotation (bboxes, overlays)
├── alert_logger.py        # Python alert logging (snapshots + log file)
├── config.py              # Python configuration constants
├── requirements.txt       # Python dependencies
│
└── alerts/                # Directory for saved alert snapshots (auto-created)
```

> **Note:** The project has two modes — the **primary mode** is the Node.js web dashboard (`server.js`), and the **legacy mode** is the Python desktop application (`main.py`). Both use the same AI pipeline concepts but the Node.js version is the main one.

---

## Setup & Installation

### Prerequisites

- **Node.js** v18+ installed
- A **Groq API key** and/or **Google Gemini API key**
- (Optional) Gmail account with an App Password for email alerts

### Steps

```bash
# 1. Clone or download the project
cd alertv

# 2. Install Node.js dependencies
npm install

# 3. Configure your API keys
#    Edit the .env file with your keys:
#
#    GEMINI_API_KEY=your_gemini_key
#    GROQ_API_KEY=your_groq_key
#    PORT=8000
#
#    (Optional) For email alerts:
#    ALERT_EMAIL_FROM=your_email@gmail.com
#    ALERT_EMAIL_TO=recipient@gmail.com
#    GMAIL_APP_PASSWORD=your_app_password

# 4. Start the server
npm start

# 5. Open in browser
#    → http://localhost:8000
```

### Python Desktop Mode (Optional)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run desktop mode (opens an OpenCV window with live webcam analysis)
python main.py

# Or with a video file
python main.py --video path/to/video.mp4
```

---

## How It Works — End to End

### Live Webcam Flow

1. User opens the dashboard at `http://localhost:8000` and clicks **"Start Analysis"**
2. The browser requests webcam access via `navigator.mediaDevices.getUserMedia()`
3. A **WebSocket** connection is opened to `ws://localhost:8000/ws/feed`
4. The browser captures frames from the webcam at a regular interval, encodes each frame as a **base64 JPEG**, and sends it over the WebSocket
5. The server receives the frame and sends it to the **AI analysis pipeline** (Groq first, Gemini as fallback)
6. The AI returns a JSON response with: `status`, `confidence`, `description`, and `regions` (bounding boxes)
7. The server updates the **state machine**, records the incident, and sends the result back via WebSocket
8. The browser receives the result, draws **bounding boxes** on a canvas overlay, and updates the dashboard stats/charts
9. If aggression is detected, an **email alert** is sent with the captured frame attached

### Video Upload Flow

1. User uploads a video file (MP4/AVI/MOV) through the dashboard
2. The browser extracts frames from the video at ~2-second intervals using a `<video>` element and `<canvas>`
3. The extracted frames (as base64 JPEG) are sent to `POST /api/analyze-batch`
4. The server analyzes each frame sequentially through the AI pipeline
5. Results are sent back as a batch and displayed on the dashboard with a timeline

---

## Module-by-Module Breakdown

### `server.js` — Node.js Backend

This is the **main backend** file that does everything:

| Section | What It Does |
|---------|-------------|
| **Configuration** (lines 27–34) | Reads API keys, model names, and thresholds from `.env` |
| **AI Clients** (lines 47–59) | Initializes Gemini (`@google/generative-ai`) and Groq SDK clients |
| **Email Transporter** (lines 62–74) | Sets up Gmail SMTP via Nodemailer for alert emails |
| **`sendAlertEmail()`** (lines 80–143) | Sends a styled HTML email with the captured frame embedded as an attachment. Includes a 30-second cooldown to prevent spam |
| **`ANALYSIS_PROMPT`** (lines 146–232) | A detailed, structured prompt that tells the AI exactly how to classify scenes. Includes behavioral indicators for each threat level and strict JSON output format |
| **`StateMachine` class** (lines 241–292) | Finite state machine that tracks Normal → Suspicious → Aggressive → Alert. Requires sustained aggression (>1 second) before triggering an alert |
| **`analyzeFrame()`** (lines 340–365) | Orchestrates the AI call — tries Groq first, falls back to Gemini |
| **`parseGeminiResponse()`** (lines 367–397) | Cleans up AI output (strips markdown fences, extracts JSON) and validates the response |
| **Express Routes** (lines 444–553) | REST API endpoints for frame analysis, batch analysis, stats, incidents, analytics, and system info |
| **WebSocket Server** (lines 560–620) | Real-time bidirectional communication for live webcam feed. Each client gets its own `StateMachine` instance |

### Frontend (`index.html` + `style.css`)

The frontend is a **single-page dashboard** with:

- **Live webcam feed** with canvas-based bounding box overlay
- **Video upload** with frame extraction and batch analysis
- **Stats cards** (total incidents, critical alerts, warnings, safe events)
- **Charts** (incident distribution, hourly activity)
- **Incident timeline** with real-time updates
- **Dark theme** with a professional security-dashboard aesthetic

All logic (webcam capture, WebSocket communication, canvas drawing, chart rendering) is handled in inline JavaScript within `index.html`.

### Python Modules (Legacy / Desktop Mode)

These modules form the **Python-based desktop application** that runs with OpenCV windows:

#### `main.py` — CLI Entry Point
- Parses command-line arguments (`--video`, `--interval`)
- Initializes all components (capture, analyzer, FSM, visualizer, logger)
- Runs the main loop: read frame → analyze → draw → display
- Keyboard controls: Q/ESC to quit, Space to pause, S to save screenshot

#### `analyzer.py` — Gemini Vision Analyzer
- `AggressionAnalyzer` class wraps the Google GenAI SDK
- Converts OpenCV BGR frames to PIL images
- Sends images to Gemini with the analysis prompt
- Parses JSON responses with error handling

#### `video_capture.py` — Video Capture & Preprocessing
- `VideoCapture` class wraps OpenCV's `cv2.VideoCapture`
- Supports both webcam (by index) and video files (by path)
- Applies **CLAHE** (Contrast Limited Adaptive Histogram Equalization) preprocessing for better visibility in poor lighting
- Context manager support (`with` statement)

#### `state_machine.py` — Behavioral State Machine
- `StateMachine` class implements a 4-state FSM: Normal → Suspicious → Aggressive → Alert
- Uses configurable thresholds (`CONFIDENCE_THRESHOLD = 0.6`, `AGGRESSION_THRESHOLD = 0.85`)
- Keeps a rolling history of the last 5 analysis results for smoothing
- Requires sustained aggression (≥1 second) before escalating to Alert state
- One-shot alert system: `should_alert()` returns `True` only once per aggressive episode

#### `visualizer.py` — Frame Annotation
- `Visualizer` class draws bounding boxes, labels, and a status bar overlay on OpenCV frames
- Color-coded: Green (normal), Yellow (suspicious), Red (aggressive)
- Converts relative bbox coordinates (0.0–1.0) to pixel coordinates
- Status bar shows: current FSM state, confidence meter, and scene description

#### `alert_logger.py` — Alert Logging
- `AlertLogger` class saves alert snapshots as JPEG images to the `alerts/` directory
- Writes structured log entries to `alerts/incidents.log`
- Tracks total alert count

#### `config.py` — Configuration Constants
- API keys, model names
- Video capture settings (resolution, sample interval)
- Detection thresholds
- Visualization colors (BGR format for OpenCV)

---

## API Reference

All endpoints are served by `server.js` on `http://localhost:8000`.

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Serves the dashboard (`frontend/index.html`) |
| `POST` | `/api/analyze` | Analyze a single base64 frame. Body: `{ "frame": "<base64>", "camera": "UPLOAD" }` |
| `POST` | `/api/analyze-batch` | Analyze multiple frames. Body: `{ "frames": [{ "data": "<base64>", "timestamp": "1s" }], "filename": "video.mp4" }` |
| `GET`  | `/api/stats` | Returns `{ total_incidents, critical_alerts, warnings, safe_events }` |
| `GET`  | `/api/incidents` | Returns the last 50 recorded incidents |
| `GET`  | `/api/analytics` | Returns hourly activity breakdown and status distribution |
| `GET`  | `/api/system` | Returns version, AI model, API status, active cameras, email config |
| `POST` | `/api/test-alert` | Sends a test alert email to verify email configuration |

### WebSocket

| Endpoint | Protocol |
|----------|----------|
| `ws://localhost:8000/ws/feed` | WebSocket |

**Client → Server message:**
```json
{
  "type": "frame",
  "data": "<base64 JPEG string>",
  "camera": "WEBCAM"
}
```

**Server → Client message (analysis result):**
```json
{
  "type": "analysis",
  "result": {
    "status": "normal | suspicious | aggressive",
    "confidence": 0.85,
    "description": "Two people talking calmly",
    "regions": [
      {
        "label": "Person standing",
        "bbox": [0.1, 0.2, 0.4, 0.9],
        "threat_level": "normal"
      }
    ]
  },
  "state": "normal",
  "incident": { ... }
}
```

**Server → Client message (alert notification):**
```json
{
  "type": "alert_sent",
  "emailSent": true,
  "status": "aggressive",
  "message": "🚨 Alert email sent to recipient@gmail.com — AGGRESSIVE detected"
}
```

---

## AI Analysis Pipeline

The AI pipeline uses a **dual-provider strategy** with automatic failover:

```
Frame (base64 JPEG)
       │
       ▼
  ┌─────────────┐     success     ┌──────────────┐
  │  Groq API   │ ──────────────► │  Parse JSON  │ ──► Result
  │  (Llama 4   │                 │  Response    │
  │   Scout)    │                 └──────────────┘
  └──────┬──────┘
         │ error
         ▼
  ┌─────────────┐     success     ┌──────────────┐
  │  Gemini API │ ──────────────► │  Parse JSON  │ ──► Result
  │  (2.0 Flash)│                 │  Response    │
  └──────┬──────┘                 └──────────────┘
         │ error
         ▼
  ┌─────────────┐
  │  Default    │ ──► { status: "normal", confidence: 0 }
  │  Response   │
  └─────────────┘
```

### The Analysis Prompt

The prompt is carefully structured with:

1. **Classification definitions** — Detailed behavioral indicators for each threat level (Normal, Suspicious, Aggressive) with specific examples
2. **Important rules** — Conservative classification guidelines (e.g., sports/gym/dance ≠ aggression, default to lower threat level when uncertain)
3. **Response format** — Strict JSON schema with relative bounding box coordinates (0.0–1.0)
4. **Confidence guides** — Suggested confidence ranges for each classification level

---

## Behavioral State Machine

The FSM prevents false alarms by requiring **temporal consistency**:

```
                ┌─────────┐
                │ NORMAL  │◄──────────────────────┐
                │  🟢     │                       │
                └────┬────┘                       │
                     │ suspicious detected        │ confidence drops /
                     │ (conf ≥ 0.6)              │ status returns to normal
                     ▼                            │
                ┌─────────────┐                   │
                │ SUSPICIOUS  │───────────────────┘
                │  🟡         │
                └────┬────────┘
                     │ aggressive detected
                     │ (conf ≥ 0.85)
                     ▼
                ┌─────────────┐
                │ AGGRESSIVE  │
                │  🔴         │
                └────┬────────┘
                     │ sustained > 1 second
                     ▼
                ┌─────────────┐
                │   ALERT     │ ──► Trigger email + log
                │  🚨         │
                └─────────────┘
```

Key behaviors:
- **Smoothing**: Keeps a rolling window of the last 5 analysis results
- **Sustained detection**: Aggression must persist for >1 second before escalating to Alert
- **One-shot alerts**: `shouldAlert()` fires only once per aggressive episode, then resets
- **Automatic de-escalation**: State returns to Normal when confidence drops below thresholds

---

## Email Alert System

When aggression or suspicious activity is detected, an **HTML email** is sent via Gmail SMTP:

- **Styled HTML body** with a dark-themed security alert design
- **Attached frame** — the captured video frame is embedded as an inline image (`cid:alertframe`)
- **30-second cooldown** between emails to prevent spam
- **Content includes**: status, confidence %, description, number of detected regions, and timestamp

### Gmail Setup

To enable email alerts, you need a [Gmail App Password](https://myaccount.google.com/apppasswords):

1. Enable 2-Factor Authentication on your Google account
2. Go to App Passwords → Generate a new one for "Mail"
3. Add the credentials to `.env`:
   ```
   ALERT_EMAIL_FROM=your_email@gmail.com
   ALERT_EMAIL_TO=recipient@gmail.com
   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

---

## Configuration

All configuration is done via the `.env` file:

```env
# AI Provider API Keys (at least one required)
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# AI Model
GEMINI_MODEL=gemini-2.0-flash

# Server Port
PORT=8000

# Email Alerts (optional)
ALERT_EMAIL_FROM=sender@gmail.com
ALERT_EMAIL_TO=recipient@gmail.com
GMAIL_APP_PASSWORD=your_app_password
```

### Detection Thresholds (in `server.js`)

| Constant | Value | Meaning |
|----------|-------|---------|
| `CONFIDENCE_THRESHOLD` | `0.6` | Minimum confidence to flag as suspicious |
| `AGGRESSION_THRESHOLD` | `0.85` | Minimum confidence to flag as aggressive |
| `EMAIL_COOLDOWN_MS` | `30000` | Minimum 30 seconds between alert emails |

---

## Key Design Decisions

1. **Dual AI Provider (Groq + Gemini)** — Groq is used as the primary provider because Llama 4 Scout has strong multimodal capabilities and fast inference. Gemini serves as a reliable fallback if Groq is unavailable or errors out.

2. **Base64 Frame Transport** — Frames are sent as base64-encoded JPEGs over WebSocket/REST rather than streaming raw video. This simplifies the architecture (no media server needed) and works through any proxy/firewall.

3. **Client-Side Frame Extraction** — Video frame extraction happens in the browser using `<video>` + `<canvas>`, avoiding the need for server-side FFmpeg or OpenCV for the web mode.

4. **State Machine for Temporal Smoothing** — Rather than alarming on every single frame classification, the FSM requires sustained aggressive signals (>1 second) before triggering alerts. This dramatically reduces false positives.

5. **Conservative AI Classification** — The analysis prompt explicitly instructs the AI to be conservative, defaulting to lower threat levels when uncertain. Sports, exercise, and playful interactions are explicitly excluded from aggression.

6. **In-Memory State** — Incident history is kept in-memory (last 200 events) for simplicity. There is no database — data resets on server restart. This keeps the project lightweight.

---

*Built with ❤️ by B. Karthik Sai, A. Siddhartha, V. Siddhartha*
