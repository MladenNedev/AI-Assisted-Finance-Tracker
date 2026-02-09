# OPERATIONS

## Runtime Checks
- `GET /api/v1/health`: basic liveness.
- `GET /api/v1/health/ready`: readiness with dependency checks.
- Database is required for readiness.
- Redis is optional for readiness; if unavailable, cache/rate limiting gracefully degrades.

## Security Controls
- Session auth via cookie: `COOKIE_NAME`.
- CSRF protection (double-submit cookie):
- Cookie name: `CSRF_COOKIE_NAME`
- Header name: `CSRF_HEADER_NAME`
- Enforced on mutating `/api/v1/*` requests when a session cookie is present.
- Rate limiting (Redis-backed):
- Auth login/register limits.
- Reporting endpoint limits.
- Can be disabled with `RATE_LIMIT_ENABLED=false`.

## Core Environment Variables
- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `COOKIE_NAME`
- `SESSION_MAX_AGE_SECONDS`
- `CSRF_ENABLED`
- `CSRF_COOKIE_NAME`
- `CSRF_HEADER_NAME`
- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_LOGIN_LIMIT`
- `RATE_LIMIT_LOGIN_WINDOW_SECONDS`
- `RATE_LIMIT_REGISTER_LIMIT`
- `RATE_LIMIT_REGISTER_WINDOW_SECONDS`
- `RATE_LIMIT_REPORTING_LIMIT`
- `RATE_LIMIT_REPORTING_WINDOW_SECONDS`

## Production Notes
- Set `ENVIRONMENT=production` and a strong `SECRET_KEY`.
- Keep CORS explicitly scoped (`CORS_ORIGINS`).
- Use HTTPS so cookies run with `secure=true`.
