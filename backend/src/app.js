/**
 * ═══════════════════════════════════════════════════════════════
 *  CarBrain Backend — Main Entry Point
 *
 *  Boots: Express server, MQTT subscriber, WebSocket broadcast
 * ═══════════════════════════════════════════════════════════════
 */
const http = require('http');
const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');

const config = require('./config/env');
const { createMqttClient } = require('./config/mqtt');
const { initSubscriber } = require('./mqtt/subscriber');
const errorHandler = require('./middleware/errorHandler');

// ─── Routes ──────────────────────────────────────────────────
const authRoutes = require('./routes/auth.routes');
const vehicleRoutes = require('./routes/vehicle.routes');
const diagnosticRoutes = require('./routes/diagnostic.routes');
const chatRoutes = require('./routes/chat.routes');
const internalRoutes = require('./routes/internal.routes');

// ─── Express App ─────────────────────────────────────────────
const app = express();

app.use(cors());
app.use(express.json({ limit: '1mb' }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 200,
  standardHeaders: true,
  message: { error: 'Too many requests, please try again later.' },
});
app.use('/api/', limiter);

// ─── Mount Routes ────────────────────────────────────────────
app.use('/api/auth', authRoutes);
app.use('/api/vehicles', vehicleRoutes);
app.use('/api/diagnostics', diagnosticRoutes);
app.use('/api/chat', chatRoutes);
app.use('/api/internal', internalRoutes);

// ─── 404 catch-all ───────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({ error: `Route ${req.method} ${req.path} not found` });
});

// ─── Error Handler ───────────────────────────────────────────
app.use(errorHandler);

// ─── HTTP Server + WebSocket ─────────────────────────────────
const server = http.createServer(app);

// Simple WebSocket-like event emitter for real-time diagnostic alerts
// (Dev 4 can connect via Socket.IO or raw WS — this is a minimal broadcast stub)
const connectedClients = new Map(); // userId → Set<res> (SSE connections)

/**
 * SSE endpoint for real-time diagnostic alerts.
 * Frontend opens: new EventSource('/api/events')
 */
const authenticate = require('./middleware/auth');

app.get('/api/events', (req, res) => {
  // Extract token from query param for SSE (headers don't work with EventSource)
  const jwt = require('jsonwebtoken');
  const token = req.query.token;

  if (!token) {
    return res.status(401).json({ error: 'Token required as query param' });
  }

  let decoded;
  try {
    decoded = jwt.verify(token, config.jwt.secret);
  } catch {
    return res.status(401).json({ error: 'Invalid token' });
  }

  // Set up SSE
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  });

  res.write('data: {"type":"connected"}\n\n');

  const userId = decoded.id;
  if (!connectedClients.has(userId)) {
    connectedClients.set(userId, new Set());
  }
  connectedClients.get(userId).add(res);

  req.on('close', () => {
    connectedClients.get(userId)?.delete(res);
    if (connectedClients.get(userId)?.size === 0) {
      connectedClients.delete(userId);
    }
  });
});

/**
 * Broadcast a new diagnostic report to the vehicle owner via SSE.
 */
function onReportCreated(userId, report) {
  const clients = connectedClients.get(userId);
  if (!clients) return;

  const event = `data: ${JSON.stringify({ type: 'diagnostic:new', report })}\n\n`;
  for (const client of clients) {
    client.write(event);
  }
  console.log(`[SSE] Broadcast diagnostic:new to ${clients.size} client(s) for user ${userId}`);
}

// ─── Start MQTT Subscriber ──────────────────────────────────
let mqttClient;
try {
  mqttClient = createMqttClient();
  initSubscriber(mqttClient, onReportCreated);
} catch (err) {
  console.warn('[MQTT] Failed to initialize (non-fatal):', err.message);
  console.warn('[MQTT] The backend will run without live MQTT. Use /api/internal/simulate-dtc instead.');
}

// ─── Boot Server ─────────────────────────────────────────────
server.listen(config.port, () => {
  console.log('');
  console.log('  ╔══════════════════════════════════════════════╗');
  console.log('  ║   🚗  CarBrain Backend — Running             ║');
  console.log(`  ║   📡  Port: ${config.port}                           ║`);
  console.log(`  ║   🌍  Env:  ${config.nodeEnv.padEnd(26)}║`);
  console.log('  ║                                              ║');
  console.log('  ║   Endpoints:                                 ║');
  console.log(`  ║     POST /api/auth/register                  ║`);
  console.log(`  ║     POST /api/auth/login                     ║`);
  console.log(`  ║     GET  /api/vehicles                       ║`);
  console.log(`  ║     GET  /api/diagnostics                    ║`);
  console.log(`  ║     POST /api/chat/:reportId                 ║`);
  console.log(`  ║     POST /api/internal/simulate-dtc          ║`);
  console.log(`  ║     GET  /api/internal/health                ║`);
  console.log('  ╚══════════════════════════════════════════════╝');
  console.log('');
});

// ─── Graceful Shutdown ───────────────────────────────────────
process.on('SIGTERM', () => {
  console.log('[APP] SIGTERM received — shutting down…');
  if (mqttClient) mqttClient.end();
  server.close(() => {
    const { pool } = require('./db');
    pool.end();
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('[APP] SIGINT received — shutting down…');
  if (mqttClient) mqttClient.end();
  server.close(() => {
    const { pool } = require('./db');
    pool.end();
    process.exit(0);
  });
});
