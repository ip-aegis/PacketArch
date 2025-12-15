# PacketArch Backend

OT Traffic Simulation Platform - Backend API

## Setup

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Run migrations:
   ```bash
   poetry run alembic upgrade head
   ```

3. Start the server:
   ```bash
   poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

## API Documentation

- Swagger UI: http://localhost:8001/api/docs
- ReDoc: http://localhost:8001/api/redoc
