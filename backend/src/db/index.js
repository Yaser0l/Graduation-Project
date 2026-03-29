/**
 * Thin query helpers around the pg pool.
 */
const pool = require('../config/db');

/**
 * Run a parameterized query.
 * @param {string} text  SQL query with $1, $2… placeholders
 * @param {any[]}  params
 * @returns {Promise<import('pg').QueryResult>}
 */
const query = (text, params) => pool.query(text, params);

/**
 * Grab a client from the pool for transactions.
 */
const getClient = () => pool.connect();

module.exports = { query, getClient, pool };
