/**
 * Nodemailer transporter.
 */
const nodemailer = require('nodemailer');
const config = require('./env');

let transporter;

if (config.smtp.user) {
  transporter = nodemailer.createTransport({
    host: config.smtp.host,
    port: config.smtp.port,
    secure: config.smtp.port === 465,
    auth: {
      user: config.smtp.user,
      pass: config.smtp.pass,
    },
  });

  transporter.verify()
    .then(() => console.log('[MAIL] SMTP transporter ready'))
    .catch((err) => console.warn('[MAIL] SMTP verify failed (non-fatal):', err.message));
} else {
  console.warn('[MAIL] No SMTP_USER configured — email notifications disabled');
  // Create a dummy transporter that logs instead of sending
  transporter = {
    sendMail: async (opts) => {
      console.log('[MAIL-STUB] Would send email:', opts.subject, '→', opts.to);
      return { messageId: 'stub' };
    },
  };
}

module.exports = transporter;
