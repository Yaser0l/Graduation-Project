/**
 * Diagnostic Service — Core orchestration logic.
 *
 * This is the heart of Developer 2's work. It:
 *   1. Receives parsed DTC data (from MQTT or the simulate endpoint)
 *   2. Deduplicates against existing open reports
 *   3. Calls the LLM for analysis
 *   4. Stores the report in the DB
 *   5. Triggers notifications
 */
const db = require('../db');
const llmService = require('./llm.service');
const notifyService = require('./notify.service');

/**
 * Process incoming DTC data from the OBD-II device.
 *
 * @param {Object} payload
 * @param {string}   payload.vin        Vehicle Identification Number
 * @param {string[]} payload.dtc_list   Array of DTC codes
 * @param {number}   payload.mileage    Current mileage reading
 * @param {string}   payload.timestamp  ISO 8601
 * @param {Function} [onReportCreated]  Optional callback (used by WebSocket to emit events)
 * @returns {Promise<Object|null>}      The new report, or null if deduplicated
 */
async function processDtcEvent({ vin, dtc_list, mileage, make, model, year, timestamp }, onReportCreated) {
  console.log(`[DIAG] Processing DTC event: VIN=${vin}, codes=${dtc_list.join(',')}, mileage=${mileage}`);

  // ── Step 1: Find the vehicle ────────────────────────────────
  const vehicleResult = await db.query('SELECT * FROM vehicles WHERE vin = $1', [vin]);

  if (!vehicleResult.rows.length) {
    console.error(`[DIAG] Rejected! VIN ${vin} is not registered in the database. Contact support or add vehicle first.`);
    return { error: 'Vehicle unregistered' };
  }

  const vehicle = vehicleResult.rows[0];
  // Always update mileage to the latest reading
  await db.query('UPDATE vehicles SET mileage = $1 WHERE id = $2', [mileage, vehicle.id]);
  vehicle.mileage = mileage;

  // ── Step 2: Deduplication ───────────────────────────────────
  // Check if there's already an OPEN (unresolved) report for this vehicle
  // with the exact same set of DTC codes.
  const existing = await db.query(
    `SELECT id FROM diagnostic_reports
     WHERE vehicle_id = $1 AND resolved = FALSE AND dtc_codes = $2`,
    [vehicle.id, dtc_list]
  );

  if (existing.rows.length) {
    console.log(`[DIAG] Duplicate DTC set for vehicle ${vin} — skipping`);
    // Update mileage on existing report
    await db.query(
      'UPDATE diagnostic_reports SET mileage_at_fault = $1 WHERE id = $2',
      [mileage, existing.rows[0].id]
    );
    return null;
  }

  // ── Step 3: Call LLM for analysis ───────────────────────────
  const llmResult = await llmService.analyze({
    dtc_codes: dtc_list,
    vehicle: {
      make: vehicle.make,
      model: vehicle.model,
      year: vehicle.year,
      mileage: vehicle.mileage,
      last_oil_change_km: vehicle.last_oil_change_km,
    },
  });

  // ── Step 4: Store the report ────────────────────────────────
  const reportResult = await db.query(
    `INSERT INTO diagnostic_reports
       (vehicle_id, dtc_codes, mileage_at_fault, llm_explanation, urgency, estimated_cost_min, estimated_cost_max)
     VALUES ($1, $2, $3, $4, $5, $6, $7)
     RETURNING *`,
    [
      vehicle.id,
      dtc_list,
      mileage,
      llmResult.explanation,
      llmResult.urgency,
      llmResult.estimated_cost_min,
      llmResult.estimated_cost_max,
    ]
  );
  const report = reportResult.rows[0];
  console.log(`[DIAG] Report ${report.id} created for VIN ${vin}`);

  // ── Step 5: Notify the owner ────────────────────────────────
  await notifyService.notifyOwner(vehicle.id, report, vehicle);

  // ── Step 6: Emit event for WebSocket listeners ──────────────
  if (onReportCreated) {
    onReportCreated(vehicle.user_id, report);
  }

  return report;
}

module.exports = { processDtcEvent };
