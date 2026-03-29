/**
 * Diagnostic Routes — View and manage diagnostic reports.
 */
const { Router } = require('express');
const db = require('../db');
const authenticate = require('../middleware/auth');

const router = Router();

router.use(authenticate);

// ─────────────────────────────────────────────────────────────
// GET /api/diagnostics — All reports for the logged-in user
// ─────────────────────────────────────────────────────────────
router.get('/', async (req, res, next) => {
  try {
    const { resolved } = req.query; // optional filter

    let sql = `
      SELECT dr.*, v.vin, v.make, v.model, v.year
      FROM diagnostic_reports dr
      JOIN vehicles v ON dr.vehicle_id = v.id
      WHERE v.user_id = $1
    `;
    const params = [req.user.id];

    if (resolved === 'true')  { sql += ' AND dr.resolved = TRUE'; }
    if (resolved === 'false') { sql += ' AND dr.resolved = FALSE'; }

    sql += ' ORDER BY dr.created_at DESC';

    const { rows } = await db.query(sql, params);
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

// ─────────────────────────────────────────────────────────────
// GET /api/diagnostics/:id — Single report detail
// ─────────────────────────────────────────────────────────────
router.get('/:id', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      `SELECT dr.*, v.vin, v.make, v.model, v.year, v.mileage AS current_mileage
       FROM diagnostic_reports dr
       JOIN vehicles v ON dr.vehicle_id = v.id
       WHERE dr.id = $1 AND v.user_id = $2`,
      [req.params.id, req.user.id]
    );

    if (!rows.length) return res.status(404).json({ error: 'Report not found' });
    res.json(rows[0]);
  } catch (err) {
    next(err);
  }
});

// ─────────────────────────────────────────────────────────────
// PATCH /api/diagnostics/:id/resolve — Mark a report as resolved
// ─────────────────────────────────────────────────────────────
router.patch('/:id/resolve', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      `UPDATE diagnostic_reports dr
       SET resolved = TRUE, resolved_at = NOW()
       FROM vehicles v
       WHERE dr.id = $1 AND dr.vehicle_id = v.id AND v.user_id = $2
       RETURNING dr.*`,
      [req.params.id, req.user.id]
    );

    if (!rows.length) return res.status(404).json({ error: 'Report not found' });
    res.json(rows[0]);
  } catch (err) {
    next(err);
  }
});

// ─────────────────────────────────────────────────────────────
// GET /api/diagnostics/vehicle/:vehicleId — Reports for a specific vehicle
// ─────────────────────────────────────────────────────────────
router.get('/vehicle/:vehicleId', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      `SELECT dr.*
       FROM diagnostic_reports dr
       JOIN vehicles v ON dr.vehicle_id = v.id
       WHERE v.id = $1 AND v.user_id = $2
       ORDER BY dr.created_at DESC`,
      [req.params.vehicleId, req.user.id]
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

module.exports = router;
