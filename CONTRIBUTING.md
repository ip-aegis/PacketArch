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
git clone https://github.com/ip-aegis/PacketArch.git
cd PacketArch

# Create .env (see DEPLOY.md), then build and start the whole stack
docker compose up -d --build

# Rebuild after code changes
docker compose up -d --build backend frontend
```

Dev and prod are the same Compose stack; nothing runs on the host directly. Poetry and
pnpm are still needed for running the test suites and linters locally (below).

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
