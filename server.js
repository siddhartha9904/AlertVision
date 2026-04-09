/**
 * AlertVision — Node.js Backend Server
 * =====================================
 * Replaces the Python/FastAPI backend entirely.
 * 
 * Features:
 *   - Serves the frontend dashboard
 *   - REST API for frame analysis via Gemini 2.0 Flash
 *   - WebSocket for live webcam feed analysis
 *   - In-memory incident tracking & statistics
 * 
 * Usage:
 *   npm install
 *   npm start
 *   → Open http://localhost:8000
 */

require('dotenv').config();
const express = require('express');
const http = require('http');
const path = require('path');
const { WebSocketServer } = require('ws');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const Groq = require('groq-sdk');
const nodemailer = require('nodemailer');

// ── Configuration ──────────────────────────────────────
const PORT = process.env.PORT || 8000;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-2.0-flash';
const GROQ_API_KEY = process.env.GROQ_API_KEY;
const GROQ_MODEL = 'meta-llama/llama-4-scout-17b-16e-instruct';

const CONFIDENCE_THRESHOLD = 0.6;
const AGGRESSION_THRESHOLD = 0.85;

// ── Email Alert Configuration ─────────────────────────
const ALERT_EMAIL_FROM = process.env.ALERT_EMAIL_FROM;
const ALERT_EMAIL_TO = process.env.ALERT_EMAIL_TO;
const GMAIL_APP_PASSWORD = process.env.GMAIL_APP_PASSWORD;

if (!GEMINI_API_KEY && !GROQ_API_KEY) {
  console.error('ERROR: At least one of GEMINI_API_KEY or GROQ_API_KEY must be set in .env');
  process.exit(1);
}

// ── Gemini AI Client ───────────────────────────────────
let genAI, geminiModel;
if (GEMINI_API_KEY) {
  genAI = new GoogleGenerativeAI(GEMINI_API_KEY);
  geminiModel = genAI.getGenerativeModel({ model: GEMINI_MODEL });
}

// ── Groq AI Client ────────────────────────────────────
let groqClient;
if (GROQ_API_KEY) {
  groqClient = new Groq({ apiKey: GROQ_API_KEY });
  console.log(`[Groq] Client initialized with model: ${GROQ_MODEL}`);
}

// ── Gmail SMTP Transporter ────────────────────────────
let emailTransporter = null;
if (ALERT_EMAIL_FROM && GMAIL_APP_PASSWORD && ALERT_EMAIL_TO) {
  emailTransporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: ALERT_EMAIL_FROM,
      pass: GMAIL_APP_PASSWORD,
    },
  });
  console.log(`[Email] Alert notifications enabled → ${ALERT_EMAIL_TO}`);
} else {
  console.warn('[Email] Alert email disabled — set ALERT_EMAIL_FROM, ALERT_EMAIL_TO, GMAIL_APP_PASSWORD in .env');
}

// ── Send Alert Email ──────────────────────────────────
let lastAlertEmailTime = 0;
const EMAIL_COOLDOWN_MS = 30000; // Minimum 30 seconds between emails to avoid spam

async function sendAlertEmail(result, frameBase64) {
  if (!emailTransporter) return false;

  const now = Date.now();
  if (now - lastAlertEmailTime < EMAIL_COOLDOWN_MS) {
    console.log(`[Email] Cooldown active — skipping (next email allowed in ${Math.ceil((EMAIL_COOLDOWN_MS - (now - lastAlertEmailTime)) / 1000)}s)`);
    return false;
  }

  const timestamp = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
  const statusLabel = result.status === 'aggressive' ? '🔴 CRITICAL — AGGRESSION DETECTED'
    : result.status === 'suspicious' ? '🟡 WARNING — SUSPICIOUS ACTIVITY'
      : '🟢 NORMAL';
  const confidencePct = (result.confidence * 100).toFixed(1);

  const htmlBody = `
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0b0e; border: 1px solid #ef4444; border-radius: 12px; overflow: hidden;">
      <div style="background: linear-gradient(135deg, #1a0000, #2d0a0a); padding: 24px; text-align: center;">
        <h1 style="color: #ef4444; margin: 0; font-size: 22px;">⚠️ ALERTVISION — SECURITY ALERT</h1>
        <p style="color: #9aa0b0; margin: 8px 0 0; font-size: 13px;">${timestamp}</p>
      </div>
      <div style="padding: 24px;">
        <div style="background: #161921; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
          <h2 style="color: #ef4444; margin: 0 0 8px; font-size: 16px;">${statusLabel}</h2>
          <p style="color: #e8eaed; margin: 0 0 12px; font-size: 14px;">${result.description || 'No description available'}</p>
          <table style="width: 100%; color: #9aa0b0; font-size: 13px;">
            <tr><td style="padding: 4px 0;"><strong>Confidence:</strong></td><td>${confidencePct}%</td></tr>
            <tr><td style="padding: 4px 0;"><strong>Status:</strong></td><td>${result.status.toUpperCase()}</td></tr>
            <tr><td style="padding: 4px 0;"><strong>Regions Detected:</strong></td><td>${(result.regions || []).length}</td></tr>
          </table>
        </div>
        <div style="text-align: center;">
          <p style="color: #9aa0b0; font-size: 12px; margin: 0 0 8px;">📷 Captured Frame:</p>
          <img src="cid:alertframe" style="max-width: 100%; border-radius: 8px; border: 2px solid #252836;" alt="Alert Frame" />
        </div>
      </div>
      <div style="background: #161921; padding: 12px; text-align: center;">
        <p style="color: #5c6270; margin: 0; font-size: 11px;">AlertVision Security AI — Automated Alert</p>
      </div>
    </div>
  `;

  try {
    await emailTransporter.sendMail({
      from: `"AlertVision Security" <${ALERT_EMAIL_FROM}>`,
      to: ALERT_EMAIL_TO,
      subject: `🚨 AlertVision: ${result.status.toUpperCase()} — ${result.description || 'Security Alert'}`,
      html: htmlBody,
      attachments: frameBase64 ? [{
        filename: `alert-frame-${Date.now()}.jpg`,
        content: Buffer.from(frameBase64, 'base64'),
        contentType: 'image/jpeg',
        cid: 'alertframe',
      }] : [],
    });

    lastAlertEmailTime = now;
    console.log(`[Email] ✓ Alert email sent to ${ALERT_EMAIL_TO}`);
    return true;
  } catch (err) {
    console.error('[Email] ✗ Failed to send alert email:', err.message);
    return false;
  }
}

// ── Enhanced Analysis Prompt ───────────────────────────
const ANALYSIS_PROMPT = `You are AlertVision, an expert real-time video surveillance AI specializing in aggression and threat detection. Your task is to analyze each video frame and classify the scene using the precise criteria below.

═══════════════════════════════════════
  CLASSIFICATION DEFINITIONS
═══════════════════════════════════════

🟢 NORMAL (status: "normal")
Scene is safe with no threat indicators present.
Behavioral indicators:
  • People walking, standing, sitting, or talking calmly
  • Normal social interactions (handshakes, friendly gestures, casual conversation)
  • Routine activities (shopping, working, waiting, using phone)
  • Groups gathered peacefully (queuing, socializing)
  • Empty scene or scene with no people
  • Children playing normally
  • People carrying bags/items in a non-threatening way
Confidence guide: 0.85–1.0 when clearly peaceful, 0.6–0.85 when unsure but likely safe

🟡 SUSPICIOUS (status: "suspicious")
Unusual behavior that COULD escalate but is NOT yet violent.
Behavioral indicators:
  • Aggressive body posture: squared shoulders, puffed chest, leaning forward confrontationally
  • Clenched fists while facing another person
  • Pointing aggressively or jabbing finger at someone
  • Invading personal space: standing face-to-face within arm's reach in a tense manner
  • Pacing back and forth aggressively or erratic movement
  • Raised arms/hands in a threatening gesture (but no contact)
  • Two or more people squared off facing each other tensely
  • Someone cornering or blocking another person's path
  • Throwing hands up in frustration, slamming table/objects (without hitting a person)
  • Loitering suspiciously near restricted areas or exits
  • Sudden running or fleeing behavior in otherwise calm environment
  • Following/stalking another person
  • Concealing face intentionally (masks in non-medical context, hoods pulled tight)
Confidence guide: 0.6–0.8 for mild signs, 0.8–0.95 for strong pre-violence cues

🔴 AGGRESSIVE (status: "aggressive")
Active physical violence or clear imminent threat of bodily harm.
Behavioral indicators:
  • Punching, hitting, slapping, or striking another person
  • Kicking another person
  • Pushing, shoving, or body-slamming someone
  • Grabbing, choking, or restraining someone by force
  • Hair-pulling or headlocking
  • Throwing objects AT a person (not just throwing in frustration)
  • Wielding a weapon (bat, stick, knife, bottle, etc.)
  • Multiple people ganging up on one person (mob violence)
  • Person on the ground being kicked or stomped
  • Headbutting or biting
  • Active brawl with multiple participants exchanging blows
Confidence guide: 0.85–1.0 for clear violence, 0.7–0.85 for partially obscured but likely violent

═══════════════════════════════════════
  IMPORTANT RULES
═══════════════════════════════════════

1. Be CONSERVATIVE — only use "aggressive" when there is CLEAR physical contact or weapon display
2. Sports, gym exercises, martial arts practice, and dance are NOT aggression — classify as "normal"
3. Hugging, friendly roughhousing, or playful interactions are "normal"
4. When in doubt between "suspicious" and "aggressive", choose "suspicious"
5. When in doubt between "normal" and "suspicious", choose "normal"
6. Always identify and draw bounding boxes around ALL people visible in the frame
7. Even in a "normal" scene, draw boxes around visible people with threat_level "normal"
8. If no people are visible, return status "normal", confidence 0.95, and empty regions

═══════════════════════════════════════
  RESPONSE FORMAT
═══════════════════════════════════════

Respond ONLY with valid JSON in this exact schema (no other text):
{
    "status": "normal" | "suspicious" | "aggressive",
    "confidence": 0.0 to 1.0,
    "description": "One sentence describing the scene and any detected behavior",
    "regions": [
        {
            "label": "brief description of the person or action",
            "bbox": [x1, y1, x2, y2],
            "threat_level": "normal" | "suspicious" | "aggressive"
        }
    ]
}

- bbox values are RELATIVE coordinates (0.0 to 1.0) as fractions of image width and height
- x1,y1 = top-left corner; x2,y2 = bottom-right corner
- Each person should have their own region entry
- Always return valid JSON, nothing else`;



// ── In-Memory State ────────────────────────────────────
const incidentHistory = [];
let incidentIdCounter = 0;

// ── State Machine (ported from Python) ─────────────────
class StateMachine {
  constructor() {
    this.currentState = 'normal';
    this.stateSince = Date.now();
    this.aggressiveStart = null;
    this.alertTriggered = false;
    this.history = [];
  }

  update(analysisResult) {
    const status = analysisResult.status || 'normal';
    const confidence = analysisResult.confidence || 0;
    const now = Date.now();

    this.history.push({ status, confidence, time: now });
    if (this.history.length > 5) this.history = this.history.slice(-5);

    const previousState = this.currentState;

    if (status === 'aggressive' && confidence >= AGGRESSION_THRESHOLD) {
      if (!this.aggressiveStart) this.aggressiveStart = now;
      if (now - this.aggressiveStart >= 1000) {
        this.currentState = 'alert';
        this.alertTriggered = true;
      } else {
        this.currentState = 'aggressive';
      }
    } else if (status === 'suspicious' && confidence >= CONFIDENCE_THRESHOLD) {
      this.currentState = 'suspicious';
      this.aggressiveStart = null;
    } else {
      this.currentState = 'normal';
      this.aggressiveStart = null;
      this.alertTriggered = false;
    }

    if (this.currentState !== previousState) {
      this.stateSince = now;
      console.log(`[FSM] State: ${previousState} → ${this.currentState}`);
    }

    return this.currentState;
  }

  shouldAlert() {
    if (this.alertTriggered) {
      this.alertTriggered = false;
      return true;
    }
    return false;
  }
}

// ── Analyze Frame with Groq (Primary) ─────────────────
async function analyzeFrameGroq(base64ImageData) {
  const result = await groqClient.chat.completions.create({
    model: GROQ_MODEL,
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'image_url',
            image_url: {
              url: `data:image/jpeg;base64,${base64ImageData}`,
            },
          },
          {
            type: 'text',
            text: ANALYSIS_PROMPT,
          },
        ],
      },
    ],
    temperature: 0.3,
    max_completion_tokens: 1024,
  });

  const text = result.choices[0]?.message?.content || '';
  return parseGeminiResponse(text); // same JSON format
}

// ── Analyze Frame with Gemini (Fallback) ──────────────
async function analyzeFrameGemini(base64ImageData) {
  const result = await geminiModel.generateContent([
    {
      inlineData: {
        mimeType: 'image/jpeg',
        data: base64ImageData,
      },
    },
    ANALYSIS_PROMPT,
  ]);

  const text = result.response.text();
  return parseGeminiResponse(text);
}

// ── Analyze Frame (Groq first → Gemini fallback) ──────
async function analyzeFrame(base64ImageData) {
  // Try Groq first
  if (groqClient) {
    try {
      const result = await analyzeFrameGroq(base64ImageData);
      console.log('[Analyzer] ✓ Groq analysis complete');
      return result;
    } catch (err) {
      console.error('[Analyzer] Groq error, trying Gemini fallback:', err.message);
    }
  }

  // Fallback to Gemini
  if (geminiModel) {
    try {
      const result = await analyzeFrameGemini(base64ImageData);
      console.log('[Analyzer] ✓ Gemini analysis complete');
      return result;
    } catch (err) {
      console.error('[Analyzer] Gemini error:', err.message);
      return defaultResponse(err.message);
    }
  }

  return defaultResponse('No AI provider available');
}

function parseGeminiResponse(text) {
  try {
    let cleaned = text.trim();
    // Remove markdown code fences if present (```json ... ``` or ``` ... ```)
    if (cleaned.startsWith('```')) {
      const lines = cleaned.split('\n');
      // Remove first line (```json or ```) and last line (```)
      const endIdx = lines.length - 1;
      cleaned = lines.slice(1, lines[endIdx].trim() === '```' ? endIdx : undefined).join('\n').trim();
    }

    // Try to extract JSON object if there's extra text around it
    if (!cleaned.startsWith('{')) {
      const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
      if (jsonMatch) cleaned = jsonMatch[0];
    }

    const result = JSON.parse(cleaned);

    // Validate/set defaults
    result.status = result.status || 'normal';
    result.confidence = result.confidence || 0;
    result.description = result.description || '';
    result.regions = result.regions || [];

    return result;
  } catch (e) {
    console.error('[Analyzer] JSON parse error:', text.substring(0, 300));
    return defaultResponse('JSON parse error');
  }
}

function defaultResponse(errorMsg = '') {
  return {
    status: 'normal',
    confidence: 0,
    description: `Analysis unavailable: ${errorMsg}`,
    regions: [],
  };
}

// ── Record Incident ────────────────────────────────────
function recordIncident(result, camera = 'SYSTEM') {
  incidentIdCounter++;
  const now = new Date();
  const incident = {
    id: incidentIdCounter,
    camera,
    status: result.status || 'normal',
    confidence: result.confidence || 0,
    description: result.description || '',
    timestamp: now.toISOString(),
    time: now.toTimeString().slice(0, 5),
    hour: now.toTimeString().slice(0, 2) + ':00',
    state: result.status || 'normal',
    regions: result.regions || [],
  };
  incidentHistory.push(incident);
  // Keep only last 200
  if (incidentHistory.length > 200) incidentHistory.splice(0, incidentHistory.length - 200);
  return incident;
}


// ═══════════════════════════════════════════════════════
//   EXPRESS APP
// ═══════════════════════════════════════════════════════

const app = express();
const server = http.createServer(app);

// Parse JSON bodies up to 50MB (for base64 frames)
app.use(express.json({ limit: '50mb' }));

// Serve frontend static files
app.use('/static', express.static(path.join(__dirname, 'frontend')));

// ── Routes ─────────────────────────────────────────────

// Dashboard
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'frontend', 'index.html'));
});

// Analyze a single frame
app.post('/api/analyze', async (req, res) => {
  try {
    const { frame } = req.body; // base64 JPEG string
    if (!frame) return res.status(400).json({ error: 'No frame data provided' });

    const result = await analyzeFrame(frame);
    const incident = recordIncident(result, req.body.camera || 'UPLOAD');

    res.json({ result, incident });
  } catch (err) {
    console.error('[API] Analyze error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// Analyze multiple frames (for video upload)
app.post('/api/analyze-batch', async (req, res) => {
  try {
    const { frames, filename } = req.body; // Array of { data: base64, timestamp: string }
    if (!frames || !Array.isArray(frames)) {
      return res.status(400).json({ error: 'No frames provided' });
    }

    const analyses = [];
    for (let i = 0; i < frames.length; i++) {
      const f = frames[i];
      console.log(`[Batch] Analyzing frame ${i + 1}/${frames.length}...`);
      const result = await analyzeFrame(f.data);
      recordIncident(result, 'UPLOAD');

      analyses.push({
        frame_index: f.index || i,
        timestamp: f.timestamp || `${i}s`,
        timestamp_sec: f.timestamp_sec || i,
        result,
      });
    }

    res.json({
      filename: filename || 'unknown',
      frames_analyzed: analyses.length,
      analyses,
    });
  } catch (err) {
    console.error('[API] Batch error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// Statistics
app.get('/api/stats', (req, res) => {
  const total = incidentHistory.length;
  const critical = incidentHistory.filter(i => i.status === 'aggressive').length;
  const warnings = incidentHistory.filter(i => i.status === 'suspicious').length;
  const safe = incidentHistory.filter(i => i.status === 'normal').length;
  res.json({ total_incidents: total, critical_alerts: critical, warnings, safe_events: safe });
});

// Incidents
app.get('/api/incidents', (req, res) => {
  res.json(incidentHistory.slice(-50));
});

// Analytics
app.get('/api/analytics', (req, res) => {
  const hourly = {};
  incidentHistory.forEach(i => {
    const hour = i.hour || '00:00';
    hourly[hour] = (hourly[hour] || 0) + 1;
  });

  const dist = { aggressive: 0, suspicious: 0, normal: 0 };
  incidentHistory.forEach(i => {
    const s = i.status || 'normal';
    dist[s] = (dist[s] || 0) + 1;
  });

  res.json({ hourly, distribution: dist });
});

// System info
app.get('/api/system', (req, res) => {
  res.json({
    version: '2.0.0',
    ai_model: GEMINI_MODEL,
    api_status: 'Connected',
    active_cameras: wss ? wss.clients.size : 0,
    email_alerts: !!emailTransporter,
  });
});

// Test alert email
app.post('/api/test-alert', async (req, res) => {
  const testResult = {
    status: 'aggressive',
    confidence: 0.95,
    description: 'TEST ALERT — This is a test email from AlertVision',
    regions: [],
  };
  const sent = await sendAlertEmail(testResult, null);
  res.json({ success: sent, message: sent ? `Test email sent to ${ALERT_EMAIL_TO}` : 'Failed to send email — check console logs' });
});


// ═══════════════════════════════════════════════════════
//   WEBSOCKET — Live Webcam Analysis
// ═══════════════════════════════════════════════════════

const wss = new WebSocketServer({ server, path: '/ws/feed' });

wss.on('connection', (ws, req) => {
  console.log('[WebSocket] Client connected');
  const fsm = new StateMachine();
  let isAnalyzing = false;

  ws.on('message', async (data) => {
    try {
      const msg = JSON.parse(data.toString());

      if (msg.type === 'frame' && !isAnalyzing) {
        isAnalyzing = true;

        // Analyze the frame
        const result = await analyzeFrame(msg.data);
        const state = fsm.update(result);
        const incident = recordIncident(result, msg.camera || 'WEBCAM');

        // Send result back
        if (ws.readyState === 1) { // WebSocket.OPEN
          ws.send(JSON.stringify({
            type: 'analysis',
            result,
            state,
            incident,
          }));

          // Send alert email for suspicious or aggressive detections
          const shouldEmail = result.status === 'aggressive' || result.status === 'suspicious';
          // Also check state machine for legacy alert support
          const fsmAlert = fsm.shouldAlert();

          if (shouldEmail || fsmAlert) {
            const emailSent = await sendAlertEmail(result, msg.data);
            if (emailSent) {
              console.log(`[Alert] 📧 Email sent for ${result.status.toUpperCase()} detection (confidence: ${(result.confidence * 100).toFixed(1)}%)`);
            }
            ws.send(JSON.stringify({
              type: 'alert_sent',
              emailSent,
              status: result.status,
              message: emailSent
                ? `🚨 Alert email sent to ${ALERT_EMAIL_TO} — ${result.status.toUpperCase()} detected`
                : 'Alert triggered but email skipped (cooldown or config)',
            }));
          }
        }

        isAnalyzing = false;
      }
    } catch (err) {
      console.error('[WebSocket] Error:', err.message);
      isAnalyzing = false;
    }
  });

  ws.on('close', () => {
    console.log('[WebSocket] Client disconnected');
  });
});


// ═══════════════════════════════════════════════════════
//   START SERVER
// ═══════════════════════════════════════════════════════

server.listen(PORT, () => {
  console.log('='.repeat(55));
  console.log('  AlertVision — Web Dashboard (Node.js)');
  console.log(`  Open http://localhost:${PORT} in your browser`);
  console.log(`  Primary AI : Groq ${GROQ_MODEL}`);
  console.log(`  Fallback AI: Gemini ${GEMINI_MODEL}`);
  console.log('='.repeat(55));
});
