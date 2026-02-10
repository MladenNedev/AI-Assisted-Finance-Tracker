# Deployment

## Target
- Single-origin deployment (frontend served by backend).
- Use `Dockerfile` at repo root (builds frontend + backend).

## Production Environment
Copy `backend/.env.production.example` and fill values for:
- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `CORS_ORIGINS`
- `SENTRY_DSN` (optional)

Frontend should use `VITE_API_BASE_URL=/api/v1` for same-origin API calls.

## Railway (recommended)
1. Create a new Railway project.
2. Add a service from this repo (uses the root `Dockerfile`).
3. Add a PostgreSQL plugin and copy its connection URL into `DATABASE_URL`.
4. Add a Redis plugin and copy its connection URL into `REDIS_URL`.
5. Set required environment variables:
   - `ENVIRONMENT=production`
   - `SECRET_KEY`
   - `DATABASE_URL`
   - `REDIS_URL`
   - `CORS_ORIGINS` (use your production domain)
6. Deploy from the Railway dashboard or via CLI.

## Runtime Checks
- `GET /api/v1/health`
- `GET /api/v1/health/ready`

## Notes
- Cookies are secure when `ENVIRONMENT=production`.
- Static frontend assets are served from `FRONTEND_DIST_DIR`.
