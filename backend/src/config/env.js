/**
 * Centralized environment configuration.
 * Loads .env and exports typed, validated config values.
 */
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

function required(key) {
  const val = process.env[key];
  if (!val && process.env.NODE_ENV === 'production') {
    throw new Error(`Missing required env variable: ${key}`);
  }
  return val || '';
}

module.exports = {
  port: parseInt(process.env.PORT, 10) || 4000,
  nodeEnv: process.env.NODE_ENV || 'development',
  isDev: (process.env.NODE_ENV || 'development') === 'development',

  db: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT, 10) || 5432,
    database: process.env.DB_NAME || 'carbrain',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || '',
  },

  jwt: {
    secret: required('JWT_SECRET'),
    expiresIn: process.env.JWT_EXPIRES_IN || '7d',
  },

  mqtt: {
    brokerUrl: process.env.MQTT_BROKER_URL || 'mqtt://localhost:1883',
    topic: process.env.MQTT_TOPIC || 'obd2/dtc/#',
    username: process.env.MQTT_USERNAME || undefined,
    password: process.env.MQTT_PASSWORD || undefined,
  },

  llm: {
    baseUrl: process.env.LLM_BASE_URL || 'http://localhost:5000',
    analyzePath: process.env.LLM_ANALYZE_PATH || '/api/llm/analyze',
    chatPath: process.env.LLM_CHAT_PATH || '/api/llm/chat',
    apiKey: process.env.LLM_API_KEY || '',
  },

  smtp: {
    host: process.env.SMTP_HOST || 'smtp.gmail.com',
    port: parseInt(process.env.SMTP_PORT, 10) || 587,
    user: process.env.SMTP_USER || '',
    pass: process.env.SMTP_PASS || '',
    from: process.env.EMAIL_FROM || 'CarBrain <noreply@carbrain.app>',
  },

  vapid: {
    publicKey: process.env.VAPID_PUBLIC_KEY || '',
    privateKey: process.env.VAPID_PRIVATE_KEY || '',
    mailto: process.env.VAPID_MAILTO || '',
  },
};
