# Architecture Overview

## Style
- Modular monolith.
- Clear separation between API, domain, services, and persistence.
- Async backend stack with FastAPI and SQLAlchemy 2.0.

## Backend Modules
- `app/api`: HTTP routers, dependencies, request/response handling.
- `app/core`: configuration, logging, security primitives, cross-cutting concerns.
- `app/domain`: domain objects and invariants.
- `app/services`: application services and orchestration.
- `app/persistence`: database models, sessions, repositories.
- `app/schemas`: Pydantic transport schemas.

## Request Flow
1. Client calls `/api/v1/...`.
2. Router validates input and resolves dependencies.
3. Service layer coordinates domain and persistence operations.
4. Repository and SQLAlchemy session persist/query data.
5. Router returns schema-based response or standardized error payload.

## Frontend Modules
- `src/pages`: route-level UI placeholders (`Login`, `Dashboard`).
- `src/api`: fetch client and API type definitions.
- `src/components`: reusable UI building blocks.

## Runtime Topology
- `frontend` container serves Vite dev server.
- `backend` container serves FastAPI app.
- `postgres` container stores application data.
