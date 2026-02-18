# Contributing to PacketArch

Thank you for your interest in contributing to PacketArch!

## Development Setup

### Prerequisites
- Python 3.11+ with [Poetry](https://python-poetry.org/)
- Node.js 18+ with [pnpm](https://pnpm.io/)
- Docker and Docker Compose

### Getting Started

```bash
# Clone the repository
git clone git@github.com:ip-aegis/PacketArch.git
cd PacketArch

# Backend
cd backend && poetry lock && poetry install

# Frontend
cd ../frontend && pnpm install

# Start infrastructure (PostgreSQL, Redis)
cd ../docker && docker-compose -f docker-compose.dev.yml up -d

# Start backend
cd ../backend && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Start frontend (in a separate terminal)
cd frontend && pnpm dev
```

## Code Standards

### Backend (Python)
- Type hints on all function signatures
- Format with `ruff format`, lint with `ruff check`
- Follow SQLAlchemy 2.0 async patterns
- Use Pydantic schemas for all API request/response models
- Custom exceptions from `app.core.exceptions` (not raw `HTTPException`)

### Frontend (TypeScript)
- TypeScript strict mode enabled
- Lint with ESLint (`pnpm lint`)
- Zustand for state management
- Ant Design components with the project's dark theme

### Testing
- Backend: `cd backend && poetry run pytest tests/`
- Frontend: `cd frontend && pnpm test`

## Agent Versioning Rule

Any change to files under `docker/packetarch-agent/` or to shared code in `backend/app/protocol_engines/` **must** include a version bump in `docker/packetarch-agent/app/version.py`.

Use semantic versioning:
- **MAJOR** — Breaking changes to agent/server WebSocket protocol
- **MINOR** — New features (backward compatible)
- **PATCH** — Bug fixes, minor improvements

## Pull Request Process

1. Create a feature branch from `master`
2. Make your changes with clear, focused commits
3. Ensure linting passes: `ruff check` (backend) and `pnpm lint` (frontend)
4. Ensure tests pass: `pytest` (backend)
5. Open a PR against `master` with a clear description
6. Address review feedback

## Reporting Issues

Use [GitHub Issues](https://github.com/ip-aegis/PacketArch/issues) for bug reports and feature requests. Include:
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Environment details (OS, browser, Docker version)
