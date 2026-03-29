/**
 * Vehicle Routes — CRUD for the user's vehicles.
 */
const { Router } = require('express');
const db = require('../db');
const authenticate = require('../middleware/auth');

const router = Router();

// All vehicle routes require authentication
router.use(authenticate);

// ─────────────────────────────────────────────────────────────
// GET /api/vehicles — List all vehicles for the logged-in user
// ─────────────────────────────────────────────────────────────
router.get('/', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT * FROM vehicles WHERE user_id = $1 ORDER BY created_at DESC',
      [req.user.id]
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

// ─────────────────────────────────────────────────────────────
// GET /api/vehicles/:id — Single vehicle detail
// ─────────────────────────────────────────────────────────────
router.get('/:id', async (req, res, next) => {
  try {
    const { rows } = await db.query(
      'SELECT * FROM vehicles WHERE id = $1 AND user_id = $2',
      [req.params.id, req.user.id]
    );

    if (!rows.length) return res.status(404).json({ error: 'Vehicle not found' });
    res.json(rows[0]);
  } catch (err) {
    next(err);
  }
});

// ─────────────────────────────────────────────────────────────
// POST /api/vehicles — Register a new vehicle
// ─────────────────────────────────────────────────────────────
router.post('/', async (req, res, next) => {
  try {
    const { vin, make, model, year, mileage, last_oil_change_km } = req.body;

    if (!vin) {
      return res.status(400).json({ error: 'VIN is required' });
    }

    const { rows } = await db.query(
      `INSERT INTO vehicles (user_id, vin, make, model, year, mileage, last_oil_change_km)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING *`,
      [req.user.id, vin, make || null, model || null, year || null, mileage || 0, last_oil_change_km || null]
    );

    res.status(201).json(rows[0]);
  } catch (err) {
    next(err);
  }
});

// ─────────────────────────────────────────────────────────────
// PATCH /api/vehicles/:id — Update vehicle info
// ─────────────────────────────────────────────────────────────
router.patch('/:id', async (req, res, next) => {
  try {
    const { make, model, year, mileage, last_oil_change_km } = req.body;

    // Build dynamic SET clause
    const fields = [];
    const values = [];
    let paramIndex = 1;

    if (make !== undefined)              { fields.push(`make = $${paramIndex++}`);              values.push(make); }
    if (model !== undefined)             { fields.push(`model = $${paramIndex++}`);             values.push(model); }
    if (year !== undefined)              { fields.push(`year = $${paramIndex++}`);              values.push(year); }
    if (mileage !== undefined)           { fields.push(`mileage = $${paramIndex++}`);           values.push(mileage); }
    if (last_oil_change_km !== undefined){ fields.push(`last_oil_change_km = $${paramIndex++}`);values.push(last_oil_change_km); }

    if (!fields.length) {
      return res.status(400).json({ error: 'No fields to update' });
    }

    values.push(req.params.id, req.user.id);

    const { rows } = await db.query(
      `UPDATE vehicles SET ${fields.join(', ')}
       WHERE id = $${paramIndex++} AND user_id = $${paramIndex}
       RETURNING *`,
      values
    );

    if (!rows.length) return res.status(404).json({ error: 'Vehicle not found' });
    res.json(rows[0]);
  } catch (err) {
    next(err);
  }
});

// ─────────────────────────────────────────────────────────────
// DELETE /api/vehicles/:id
// ─────────────────────────────────────────────────────────────
router.delete('/:id', async (req, res, next) => {
  try {
    const { rowCount } = await db.query(
      'DELETE FROM vehicles WHERE id = $1 AND user_id = $2',
      [req.params.id, req.user.id]
    );

    if (!rowCount) return res.status(404).json({ error: 'Vehicle not found' });
    res.json({ message: 'Vehicle deleted' });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
