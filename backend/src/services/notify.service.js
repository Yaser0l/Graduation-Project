/**
 * Notification Service — Email (Nodemailer) + Web Push.
 */
const transporter = require('../config/mailer');
const webpush = require('../config/webpush');
const config = require('../config/env');
const db = require('../db');

/**
 * Send an email alert for a new diagnostic report.
 *
 * @param {string} toEmail
 * @param {Object} report  { dtc_codes, llm_explanation, urgency }
 * @param {Object} vehicle { make, model, year, vin }
 */
async function sendEmailAlert(toEmail, report, vehicle) {
  const urgencyColors = {
    low: '#22c55e',
    medium: '#eab308',
    high: '#f97316',
    critical: '#ef4444',
  };
  const color = urgencyColors[report.urgency] || '#6b7280';

  const html = `
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <h2 style="color:${color}">⚠️ Diagnostic Alert — ${report.urgency.toUpperCase()}</h2>
      <p><strong>Vehicle:</strong> ${vehicle.year || ''} ${vehicle.make || ''} ${vehicle.model || ''} (${vehicle.vin})</p>
      <p><strong>Trouble Codes:</strong> ${report.dtc_codes.join(', ')}</p>
      <hr/>
      <div style="background:#f9fafb;padding:16px;border-radius:8px">
        ${report.llm_explanation}
      </div>
      <br/>
      <p>Log in to <strong>CarBrain</strong> to chat with the AI Mechanic for more details.</p>
    </div>
  `;

  await transporter.sendMail({
    from: config.smtp.from,
    to: toEmail,
    subject: `🚗 CarBrain Alert: ${report.dtc_codes.join(', ')} — ${report.urgency.toUpperCase()}`,
    html,
  });
  console.log(`[NOTIFY] Email sent to ${toEmail}`);
}

/**
 * Send a Web Push notification.
 *
 * @param {Object} subscription  PushSubscription JSON from the browser
 * @param {Object} report
 */
async function sendPushNotification(subscription, report) {
  if (!subscription || !config.vapid.publicKey) return;

  const payload = JSON.stringify({
    title: `🚗 Engine Alert — ${report.urgency.toUpperCase()}`,
    body: `Codes: ${report.dtc_codes.join(', ')}. Tap to view diagnosis.`,
    data: { reportId: report.id },
  });

  try {
    await webpush.sendNotification(subscription, payload);
    console.log('[NOTIFY] Web Push sent');
  } catch (err) {
    console.error('[NOTIFY] Web Push failed:', err.message);
    // If subscription expired (410), remove it
    if (err.statusCode === 410) {
      console.log('[NOTIFY] Removing expired push subscription');
    }
  }
}

/**
 * Notify the vehicle's owner via all channels.
 *
 * @param {string} vehicleId
 * @param {Object} report   Saved diagnostic_reports row
 * @param {Object} vehicle  The vehicle row
 */
async function notifyOwner(vehicleId, report, vehicle) {
  try {
    // Find the user who owns this vehicle
    const { rows } = await db.query(
      'SELECT email, push_subscription FROM users WHERE id = $1',
      [vehicle.user_id]
    );

    if (!rows.length) {
      console.warn('[NOTIFY] No user found for vehicle', vehicleId);
      return;
    }

    const user = rows[0];

    // Fire both in parallel
    await Promise.allSettled([
      sendEmailAlert(user.email, report, vehicle),
      sendPushNotification(user.push_subscription, report),
    ]);
  } catch (err) {
    console.error('[NOTIFY] notifyOwner error:', err.message);
  }
}

module.exports = { sendEmailAlert, sendPushNotification, notifyOwner };
