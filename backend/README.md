# EthioPrep Backend

Django + DRF backend for Ethiopian exam preparation (Grade 12 and University Exit exam tracks).

## Features
- JWT auth (`/api/auth/register`, `/api/auth/login`, `/api/auth/me`)
- Google OAuth redirect/callback login (`/api/auth/google/start`, `/api/auth/google/callback`)
- Telegram login widget verification (`/api/auth/telegram/verify`)
- Subjects and questions with pagination, filters, random practice
- Explanation access control with free limits and paid package upgrades
- Practice sessions and exam simulation result tracking
- Payment screenshot workflow with admin approve/reject actions
- Analytics endpoints for summary, subject accuracy, weak topics, and study history
- Celery + Redis AI question generation jobs
- Telegram bot-compatible endpoints

## Tech Stack
- Django, DRF
- PostgreSQL (Supabase-ready through `DATABASE_URL`)
- Redis + Celery
- Docker

## Quick Start
1. Copy `.env.example` to `.env` and edit values.
	- For local PostgreSQL, set: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
	- Example: `DB_NAME=ethioprep`, `DB_USER=postgres`, `DB_PASSWORD=postgres`, `DB_HOST=localhost`, `DB_PORT=5432`.
	- For Google OAuth, set: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.
	- For Telegram OAuth, set: `TELEGRAM_BOT_TOKEN`.
	- Set `FRONTEND_URL` so backend OAuth callbacks can redirect back to your frontend.
2. Run locally:

```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

3. Seed demo data (recommended for frontend testing):

```bash
python manage.py seed_demo_data
```

3. Run with Docker:

```bash
docker compose up --build
```

## Important Endpoints
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET/PATCH /api/auth/me`
- `GET /api/auth/google/start`
- `GET /api/auth/google/callback`
- `POST /api/auth/telegram/verify`
- `GET /api/subjects/`
- `GET /api/questions/`
- `POST /api/questions/{id}/explanation/`
- `POST /api/practice/start/`
- `POST /api/practice/answer/`
- `POST /api/payments/`
- `POST /api/payments/{id}/review/`
- `GET /api/analytics/`
- `POST /api/ai/jobs/`

## Notes
- Free explanation limits: simple=20, detailed=10, deep=5.
- Packages: simple=50 birr, detailed=100 birr, deep=200 birr.
- Frontend can use this backend by pointing API base URL to `http://localhost:8000`.
- For local frontend auth preflight, ensure your frontend origin is present in `DJANGO_CORS_ALLOWED_ORIGINS`.
