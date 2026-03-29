/**
 * MQTT client factory.
 */
const mqtt = require('mqtt');
const config = require('./env');

function createMqttClient() {
  const opts = {
    clientId: `carbrain-backend-${Date.now()}`,
    clean: true,
    reconnectPeriod: 5000,
  };

  if (config.mqtt.username) {
    opts.username = config.mqtt.username;
    opts.password = config.mqtt.password;
  }

  const client = mqtt.connect(config.mqtt.brokerUrl, opts);

  client.on('connect', () => {
    console.log(`[MQTT] Connected to ${config.mqtt.brokerUrl}`);
    client.subscribe(config.mqtt.topic, { qos: 1 }, (err) => {
      if (err) console.error('[MQTT] Subscribe error:', err.message);
      else console.log(`[MQTT] Subscribed to ${config.mqtt.topic}`);
    });
  });

  client.on('reconnect', () => console.log('[MQTT] Reconnecting…'));
  client.on('error', (err) => console.error('[MQTT] Error:', err.message));
  client.on('offline', () => console.warn('[MQTT] Client went offline'));

  return client;
}

module.exports = { createMqttClient };
