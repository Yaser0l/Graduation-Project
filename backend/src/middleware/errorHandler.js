/**
 * Global error handler middleware.
 */
function errorHandler(err, req, res, _next) {
  console.error('[ERROR]', err);

  // Postgres unique violation
  if (err.code === '23505') {
    return res.status(409).json({ error: 'Resource already exists' });
  }

  // Postgres foreign key violation
  if (err.code === '23503') {
    return res.status(400).json({ error: 'Referenced resource not found' });
  }

  const status = err.statusCode || err.status || 500;
  const message = err.message || 'Internal server error'; // Always expose for debugging

  res.status(status).json({ error: message, stack: err.stack });
}

module.exports = errorHandler;
