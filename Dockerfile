FROM node:20-alpine AS frontend-build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./frontend/
RUN cd frontend && npm install

COPY frontend ./frontend
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_DEMO_EMAIL
ARG VITE_DEMO_PASSWORD
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_DEMO_EMAIL=${VITE_DEMO_EMAIL}
ENV VITE_DEMO_PASSWORD=${VITE_DEMO_PASSWORD}
RUN cd frontend && npm run build


FROM python:3.12-slim AS backend

WORKDIR /app/backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/ /app/backend/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY --from=frontend-build /app/frontend/dist /app/frontend_dist
ENV FRONTEND_DIST_DIR=/app/frontend_dist

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
