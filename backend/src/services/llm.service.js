/**
 * LLM Service — HTTP interface to Developer 3's LLM endpoint.
 *
 * Two operations:
 *   1. analyze()  – send DTC codes + vehicle info, get structured diagnosis
 *   2. chat()     – send a user message with diagnostic context, get reply
 */
const axios = require('axios');
const config = require('../config/env');

const llmClient = axios.create({
  baseURL: config.llm.baseUrl,
  timeout: 30000, // LLM can be slow
  headers: {
    'Content-Type': 'application/json',
    ...(config.llm.apiKey ? { Authorization: `Bearer ${config.llm.apiKey}` } : {}),
  },
});

/**
 * Request a structured diagnosis from the LLM.
 *
 * @param {Object} payload
 * @param {string[]} payload.dtc_codes   e.g. ['P0420','P0171']
 * @param {Object}   payload.vehicle     { make, model, year, mileage, last_oil_change_km }
 * @returns {Promise<{explanation:string, urgency:string, estimated_cost_min:number, estimated_cost_max:number}>}
 */
async function analyze({ dtc_codes, vehicle }) {
  try {
    const { data } = await llmClient.post(config.llm.analyzePath, {
      dtc_codes,
      vehicle,
    });

    // Normalize — Dev 3 may return slightly different shapes
    return {
      explanation: data.explanation || data.message || JSON.stringify(data),
      urgency: data.urgency || 'medium',
      estimated_cost_min: data.estimated_cost_min ?? data.cost_range?.[0] ?? null,
      estimated_cost_max: data.estimated_cost_max ?? data.cost_range?.[1] ?? null,
    };
  } catch (err) {
    console.error('[LLM] analyze() failed:', err.message);
    // Return a fallback so the pipeline doesn't crash
    return {
      explanation: `LLM service unavailable. Raw DTC codes: ${dtc_codes.join(', ')}. Please consult a mechanic.`,
      urgency: 'medium',
      estimated_cost_min: null,
      estimated_cost_max: null,
    };
  }
}

/**
 * Send a chat message in the context of an existing diagnostic report.
 *
 * @param {Object} payload
 * @param {Object}   payload.report       The diagnostic report row
 * @param {Object}   payload.vehicle      The vehicle row
 * @param {Object[]} payload.history      Previous messages [{role, content}]
 * @param {string}   payload.userMessage  The new user message
 * @returns {Promise<string>}  LLM assistant reply text
 */
async function chat({ report, vehicle, history, userMessage }) {
  try {
    const { data } = await llmClient.post(config.llm.chatPath, {
      report: {
        dtc_codes: report.dtc_codes,
        explanation: report.llm_explanation,
        urgency: report.urgency,
        estimated_cost_min: report.estimated_cost_min,
        estimated_cost_max: report.estimated_cost_max,
      },
      vehicle: {
        make: vehicle.make,
        model: vehicle.model,
        year: vehicle.year,
        mileage: vehicle.mileage,
      },
      history,
      message: userMessage,
    });

    return data.reply || data.message || data.content || JSON.stringify(data);
  } catch (err) {
    console.error('[LLM] chat() failed:', err.message);
    return 'Sorry, the AI mechanic is temporarily unavailable. Please try again in a moment.';
  }
}

module.exports = { analyze, chat };
