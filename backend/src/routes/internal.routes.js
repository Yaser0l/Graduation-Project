/**
 * Internal / Dev Routes — Simulate OBD-II events without real hardware.
 * These routes are only available in development mode.
 */
const { Router } = require('express');
const config = require('../config/env');
const diagnosticService = require('../services/diagnostic.service');

const router = Router();

// ─────────────────────────────────────────────────────────────
// POST /api/internal/simulate-dtc
//
// Body:
// {
//   "vin": "1HGBH41JXMN109186",
//   "dtc_list": ["P0420"],
//   "mileage": 87432
// }
// ─────────────────────────────────────────────────────────────
router.post('/simulate-dtc', async (req, res, next) => {
  if (!config.isDev) {
    return res.status(403).json({ error: 'Simulation only available in development' });
  }

  try {
    const { vin, dtc_list, mileage } = req.body;

    if (!vin || !Array.isArray(dtc_list) || dtc_list.length === 0) {
      return res.status(400).json({ error: 'vin and dtc_list (non-empty array) are required' });
    }

    const report = await diagnosticService.processDtcEvent({
      vin,
      dtc_list,
      mileage: mileage || 0,
      timestamp: new Date().toISOString(),
    });

    if (report) {
      res.status(201).json({ message: 'Simulated DTC processed — new report created', report });
    } else {
      res.json({ message: 'DTC already known (deduplicated) — no new report' });
    }
  } catch (err) {
    next(err);
  }
});

// ─────────────────────────────────────────────────────────────
// GET /api/internal/health
// ─────────────────────────────────────────────────────────────
router.get('/health', async (req, res) => {
  const db = require('../db');
  try {
    await db.query('SELECT 1');
    res.json({ status: 'ok', db: 'connected', timestamp: new Date().toISOString() });
  } catch (err) {
    res.status(503).json({ status: 'error', db: 'disconnected', error: err.message });
  }
});

module.exports = router;
