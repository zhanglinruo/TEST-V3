# AI BI MVP

Minimal, clean repository structure for an AI-powered BI MVP.

## Tech Stack
- Backend: FastAPI (Python)
- Frontend: React (Vite)
- Database: ClickHouse
- AI: OpenAI API

## Structure
- backend: FastAPI service with modular AI/BI components
- frontend: React UI
- infra: local infrastructure (ClickHouse)

## Quick Start
1) Start ClickHouse:
   - docker compose -f infra/docker-compose.yml up -d
2) Backend:
   - cd backend
   - python -m venv .venv
   - .venv\Scripts\activate
   - pip install -e .
   - uvicorn app.main:app --reload
3) Frontend:
   - cd frontend
   - npm install
   - npm run dev

