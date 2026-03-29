/**
 * Chat Routes — Conversation with the AI Mechanic.
 *
 * Each chat session is tied to a specific diagnostic report, so the LLM
 * always knows which car/problem the user is asking about.
 */
const { Router } = require('express');
const db = require('../db');
const llmService = require('../services/llm.service');
const authenticate = require('../middleware/auth');

const router = Router();

router.use(authenticate);

// ─────────────────────────────────────────────────────────────
// POST /api/chat/:reportId — Send a message, get LLM reply
// ─────────────────────────────────────────────────────────────
router.post('/:reportId', async (req, res, next) => {
  try {
    const { reportId } = req.params;
    const { message } = req.body;

    if (!message || !message.trim()) {
      return res.status(400).json({ error: 'Message is required' });
    }

    // ── Verify user owns this report ──────────────────────────
    const reportResult = await db.query(
      `SELECT dr.*, v.make, v.model, v.year, v.mileage, v.vin
       FROM diagnostic_reports dr
       JOIN vehicles v ON dr.vehicle_id = v.id
       WHERE dr.id = $1 AND v.user_id = $2`,
      [reportId, req.user.id]
    );

    if (!reportResult.rows.length) {
      return res.status(404).json({ error: 'Report not found' });
    }

    const report = reportResult.rows[0];

    // ── Find or create chat session ───────────────────────────
    let sessionResult = await db.query(
      'SELECT id FROM chat_sessions WHERE report_id = $1 AND user_id = $2',
      [reportId, req.user.id]
    );

    let sessionId;
    if (sessionResult.rows.length) {
      sessionId = sessionResult.rows[0].id;
    } else {
      const newSession = await db.query(
        'INSERT INTO chat_sessions (report_id, user_id) VALUES ($1, $2) RETURNING id',
        [reportId, req.user.id]
      );
      sessionId = newSession.rows[0].id;
    }

    // ── Load conversation history ─────────────────────────────
    const historyResult = await db.query(
      'SELECT role, content FROM chat_messages WHERE session_id = $1 ORDER BY created_at ASC',
      [sessionId]
    );
    const history = historyResult.rows;

    // ── Save the user's message ───────────────────────────────
    await db.query(
      'INSERT INTO chat_messages (session_id, role, content) VALUES ($1, $2, $3)',
      [sessionId, 'user', message]
    );

    // ── Call the LLM ──────────────────────────────────────────
    const vehicle = {
      make: report.make,
      model: report.model,
      year: report.year,
      mileage: report.mileage,
    };

    const assistantReply = await llmService.chat({
      report,
      vehicle,
      history,
      userMessage: message,
    });

    // ── Save assistant reply ──────────────────────────────────
    await db.query(
      'INSERT INTO chat_messages (session_id, role, content) VALUES ($1, $2, $3)',
      [sessionId, 'assistant', assistantReply]
    );

    res.json({
      sessionId,
      reply: assistantReply,
    });
  } catch (err) {
    next(err);
  }
});

// ─────────────────────────────────────────────────────────────
// GET /api/chat/:reportId/history — Full conversation history
// ─────────────────────────────────────────────────────────────
router.get('/:reportId/history', async (req, res, next) => {
  try {
    const { reportId } = req.params;

    // Find the session
    const sessionResult = await db.query(
      'SELECT id FROM chat_sessions WHERE report_id = $1 AND user_id = $2',
      [reportId, req.user.id]
    );

    if (!sessionResult.rows.length) {
      return res.json({ sessionId: null, messages: [] });
    }

    const sessionId = sessionResult.rows[0].id;
    const { rows } = await db.query(
      'SELECT role, content, created_at FROM chat_messages WHERE session_id = $1 ORDER BY created_at ASC',
      [sessionId]
    );

    res.json({ sessionId, messages: rows });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
