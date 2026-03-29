/**
 * MQTT Subscriber — listens for OBD-II DTC events and feeds them
 * into the diagnostic pipeline.
 *
 * Expected MQTT payload (JSON):
 * {
 *   "vin": "1HGBH41JXMN109186",
 *   "dtc_list": ["P0420", "P0171"],
 *   "mileage": 87432,
 *   "timestamp": "2026-03-29T08:30:00Z"
 * }
 */
const diagnosticService = require('../services/diagnostic.service');

/**
 * Initialize the MQTT message handler.
 *
 * @param {import('mqtt').MqttClient} client   The connected MQTT client
 * @param {Function} [onReportCreated]         Optional callback for WebSocket broadcast
 */
function initSubscriber(client, onReportCreated) {
  client.on('message', async (topic, messageBuffer) => {
    console.log(`[MQTT] Message on ${topic}`);

    let payload;
    try {
      payload = JSON.parse(messageBuffer.toString());
    } catch (err) {
      console.error('[MQTT] Invalid JSON payload:', err.message);
      return;
    }

    // ── Validate required fields ──────────────────────────────
    const { vin, dtc_list, mileage, timestamp } = payload;

    if (!vin || !Array.isArray(dtc_list) || dtc_list.length === 0) {
      console.warn('[MQTT] Malformed payload — missing vin or dtc_list');
      return;
    }

    // ── Feed into the diagnostic pipeline ─────────────────────
    try {
      const report = await diagnosticService.processDtcEvent(
        {
          vin,
          dtc_list,
          mileage: mileage || 0,
          timestamp: timestamp || new Date().toISOString(),
        },
        onReportCreated
      );

      if (report) {
        console.log(`[MQTT] Pipeline completed → report ${report.id}`);
      } else {
        console.log('[MQTT] Pipeline completed → deduplicated (no new report)');
      }
    } catch (err) {
      console.error('[MQTT] Pipeline error:', err);
    }
  });

  console.log('[MQTT] Subscriber initialized — waiting for messages…');
}

module.exports = { initSubscriber };
