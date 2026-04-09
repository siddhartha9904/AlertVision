# AlertVision 🔴

**Real-Time Aggression Detection using Video Analytics**

A lightweight system that captures video (webcam or file), analyzes frames using Google Gemini 2.0 Flash Vision, and draws bounding boxes around detected aggression.

---

## Quick Start

```bash
# Install dependencies
npm install

# Start the server
npm start

# Open in browser
# → http://localhost:8000
```

## Features

| Feature | Description |
|---|---|
| **Live Webcam** | Real-time analysis with bounding boxes via browser webcam |
| **Video Upload** | Upload MP4/AVI/MOV files for frame-by-frame AI analysis |
| **Dashboard** | Stats, charts, and incident timeline |
| **Alerts** | Automatic incident logging with threat levels |

## How It Works

```
Webcam/File → Browser captures frame → Node.js server → Gemini 2.0 Flash Vision → JSON → Bounding Boxes
```

### Behavioral States
- 🟢 **Normal** — No threat detected
- 🟡 **Suspicious** — Unusual body language or tense interaction
- 🔴 **Aggressive** — Active fighting, pushing, threatening gestures

## Files

| File | Purpose |
|---|---|
| `server.js` | Node.js Express backend — serves dashboard + Gemini API |
| `.env` | API key configuration |
| `frontend/index.html` | Dashboard UI + webcam/upload logic |
| `frontend/style.css` | Dashboard styling |

## Configuration

Edit `.env` to change settings:
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
PORT=8000
```

## Authors

B. Karthik Sai, A. Siddhartha, V. Siddhartha
