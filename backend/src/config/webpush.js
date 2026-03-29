/**
 * Web Push (VAPID) configuration.
 */
const webpush = require('web-push');
const config = require('./env');

if (config.vapid.publicKey && config.vapid.privateKey) {
  webpush.setVapidDetails(
    config.vapid.mailto,
    config.vapid.publicKey,
    config.vapid.privateKey,
  );
  console.log('[PUSH] VAPID keys configured');
} else {
  console.warn('[PUSH] VAPID keys missing — web push disabled');
}

module.exports = webpush;
