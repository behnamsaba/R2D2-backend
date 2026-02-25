# R2D2 Copilot Backend

Flask API service for the R2D2 Copilot project.

This backend provides:
- user authentication (register/login/token-based access)
- AI generation endpoints (Market Research, Personalize Email, CRM, Marketing, Sales Call Pipeline)
- quality guardrails on generated outputs
- SQLite persistence for users and generation history
- structured export for sales pipeline outputs (`json`, `csv`, `markdown`, `pdf`)

Author:
- GitHub: [@ben-saba](https://github.com/ben-saba)

## Tech Stack

- Python + Flask
- LangChain + OpenAI
- SQLite (`sqlite3`, built into Python)
- `itsdangerous` signed tokens for auth

## Project Structure

- `app.py` - thin runtime entrypoint (`app = create_app()`)
- `storage.py` - SQLite schema + persistence helpers
- `r2d2_backend/app_factory.py` - app factory + CORS + extension wiring
- `r2d2_backend/api.py` - all `/api/*` routes
- `r2d2_backend/auth_service.py` - auth token + password policy + user auth helpers
- `r2d2_backend/llm_service.py` - prompt templates + OpenAI/LangChain calls
- `r2d2_backend/structured_output.py` - structured response builders
- `r2d2_backend/quality.py` - quality guardrails scoring/checks
- `r2d2_backend/export_utils.py` - JSON/CSV/Markdown/PDF export builders
- `r2d2_backend/http_utils.py` - request validation helpers
- `r2d2_backend/settings.py` - environment/config loader
- `test_app.py` - backend test suite
- `requirements.txt` - Python dependencies

## Prerequisites

- Python 3.9+
- OpenAI API key

## Environment Variables

Create `.env` in `R2D2-backend/`:

```env
OPENAI_API_KEY=sk-...
APP_SECRET_KEY=replace_with_a_long_random_secret
APP_ENV=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_PATH=/absolute/path/to/r2d2.sqlite3
PORT=5000
```

Behavior:
- `OPENAI_API_KEY` is required for generation endpoints.
- `APP_SECRET_KEY` is required when `APP_ENV=production` (or `prod`).
- `CORS_ORIGINS` is required when `APP_ENV=production` (comma-separated list).
- In development only, a fallback secret is used if `APP_SECRET_KEY` is absent.
- `DATABASE_PATH` is optional. If omitted, DB defaults to `R2D2-backend/r2d2.sqlite3`.
- `PORT` is optional; default is `5000`.

## Setup

```bash
cd /Users/ben/Projects/r2d2/R2D2-backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run Server

```bash
source .venv/bin/activate
python app.py
```

Default URL:
- `http://127.0.0.1:5000`

Production example:

```bash
source .venv/bin/activate
APP_ENV=production \
APP_SECRET_KEY='replace_with_strong_secret' \
CORS_ORIGINS='https://your-frontend-domain.com' \
gunicorn --bind 0.0.0.0:5000 app:app
```

## Authentication

Auth is bearer-token based.

1. Register or login.
2. Read token from response.
3. Send token in header:

```http
Authorization: Bearer <token>
```

Token details:
- signed with `APP_SECRET_KEY`
- max age: 7 days

Password policy (registration):
- minimum 12 characters
- at least 1 uppercase letter
- at least 1 lowercase letter
- at least 1 number
- at least 1 special character

## API Reference

Base URL examples assume `http://127.0.0.1:5000`.

### Health

#### `GET /api/health`
Returns:

```json
{ "status": "ok" }
```

### Auth

#### `POST /api/auth/register`
Body:

```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```

Success response:

```json
{
  "token": "<signed-token>",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "createdAt": "2026-02-25T...Z"
  }
}
```

Possible errors:
- `400` invalid email/password policy failure
- `409` user already exists

#### `POST /api/auth/login`
Body:

```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```

Success response:

```json
{
  "token": "<signed-token>",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "createdAt": "2026-02-25T...Z"
  }
}
```

Possible errors:
- `401` invalid credentials

#### `GET /api/auth/me`
Auth required.

Success response:

```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "createdAt": "2026-02-25T...Z"
  }
}
```

### History

#### `GET /api/history?feature=<name>&limit=<1-100>`
Auth required.

Notes:
- `feature` is optional
- `limit` default is `20`

Returns persisted generation rows:

```json
{
  "data": [
    {
      "id": 123,
      "feature": "personalize_email",
      "input": { "prompt": "..." },
      "output": { "data": "...", "structured": { } },
      "createdAt": "2026-02-25T...Z"
    }
  ]
}
```

#### `GET /api/market-research/history?limit=<1-100>`
Auth required.

Returns market history normalized for client display:

```json
{
  "data": [
    {
      "id": "Acme",
      "competitors": "...",
      "analysis": "...",
      "analyze": "...",
      "structured": { },
      "createdAt": "2026-02-25T...Z"
    }
  ]
}
```

### Generation Endpoints

All generation endpoints require auth and persist output to SQLite.

#### `POST /api/market-research`
Body:

```json
{ "prompt": "Stripe" }
```

Response shape:

```json
{
  "id": "Stripe",
  "competitors": "...",
  "analysis": "...",
  "analyze": "...",
  "structured": {
    "company": "Stripe",
    "competitorList": ["..."],
    "summary": "...",
    "opportunities": ["..."],
    "risks": ["..."],
    "recommendedActions": ["..."],
    "quality": {
      "clarityScore": 88,
      "ctaPresent": false,
      "spamRiskWording": [],
      "sensitiveDataWarnings": []
    }
  }
}
```

#### `POST /api/personalize-email`
Body:

```json
{ "prompt": "Draft email text..." }
```

Response shape:

```json
{
  "data": "Rewritten email...",
  "structured": {
    "rewrittenBody": "...",
    "subjectSuggestion": "...",
    "callToAction": "...",
    "keyPoints": ["..."],
    "quality": {
      "clarityScore": 90,
      "ctaPresent": true,
      "spamRiskWording": [],
      "sensitiveDataWarnings": []
    }
  }
}
```

#### `POST /api/crm`
Body must match one mode only.

Welcome mode:

```json
{
  "customerName": "Jane",
  "productName": "R2D2 Copilot"
}
```

Follow-up mode:

```json
{
  "prospectName": "Alex",
  "followUpReason": "Pricing review",
  "note": "Met at conference"
}
```

Response shape:

```json
{
  "data": "Generated CRM message...",
  "structured": {
    "message": "...",
    "nextStepQuestion": "...",
    "keyPoints": ["..."],
    "goal": "...",
    "quality": {
      "clarityScore": 85,
      "ctaPresent": true,
      "spamRiskWording": [],
      "sensitiveDataWarnings": []
    }
  }
}
```

Validation rule:
- cannot mix welcome and follow-up fields in one request (`400`)

#### `POST /api/marketing`
Has two modes based on payload fields.

Post mode (when `platform`/`postObjective` present):

```json
{
  "platform": "LinkedIn",
  "postObjective": "Drive demo bookings",
  "postContent": "Release highlights..."
}
```

Caption mode:

```json
{
  "postContent": "New release screenshot...",
  "postTone": "Professional"
}
```

Response shape:

```json
{
  "data": "Generated marketing content...",
  "structured": {
    "copy": "...",
    "hashtags": ["#..."],
    "callToAction": "...",
    "keyPoints": ["..."],
    "quality": {
      "clarityScore": 87,
      "ctaPresent": true,
      "spamRiskWording": [],
      "sensitiveDataWarnings": []
    }
  }
}
```

#### `POST /api/sales-call-pipeline`
Body:

```json
{
  "transcriptNotes": "Call notes/transcript text..."
}
```

Response shape:

```json
{
  "data": "Raw model output...",
  "structured": {
    "summary": "...",
    "objections": ["..."],
    "nextActions": ["..."],
    "followUpEmails": ["...", "...", "..."],
    "quality": {
      "clarityScore": 91,
      "ctaPresent": true,
      "spamRiskWording": [],
      "sensitiveDataWarnings": []
    }
  }
}
```

### Structured Exports

#### `POST /api/sales-call-pipeline/export`
Auth required.

Body:

```json
{
  "format": "json",
  "pipeline": {
    "summary": "...",
    "objections": ["..."],
    "nextActions": ["..."],
    "followUpEmails": ["...", "...", "..."],
    "quality": {
      "clarityScore": 90,
      "ctaPresent": true,
      "spamRiskWording": [],
      "sensitiveDataWarnings": []
    }
  }
}
```

`format` must be one of:
- `json`
- `csv`
- `markdown`
- `pdf`

Strict payload validation:
- `pipeline.summary` must be a non-empty string
- `pipeline.objections`, `pipeline.nextActions`, `pipeline.followUpEmails` must be arrays of non-empty strings
- `pipeline.quality` must be an object
- `pipeline.quality.spamRiskWording` and `pipeline.quality.sensitiveDataWarnings` must be arrays

Response:
- file download attachment (`Content-Disposition: attachment; filename="sales-call-pipeline.<ext>"`)

## Quality Guardrails

Structured generation payloads include:
- `clarityScore` (0-100)
- `ctaPresent` (boolean)
- `spamRiskWording` (matched risky terms)
- `sensitiveDataWarnings` (detected personal/secret-like data warnings)

## Persistence Model

Database tables:
- `users`
  - `id`, `email`, `password_hash`, `created_at`
- `generations`
  - `id`, `feature`, `input_json`, `output_json`, `user_id`, `created_at`

Indexes:
- `idx_generations_feature_created_at`
- `idx_generations_user_feature_created_at`

## CORS

CORS is enabled (`CORS(app)`) for local frontend/backend integration.
For production, restrict allowed origins to your deployed client domain(s).

## Testing

Run backend tests:

```bash
source .venv/bin/activate
python -m unittest -q
```

Current test coverage includes:
- auth flows and password policy
- route auth requirements
- generation endpoint success/error paths
- history isolation by user
- sales pipeline + export format behavior + payload validation

## Deployment Notes

Minimal production checklist:
1. Set `APP_ENV=production`.
2. Set a strong `APP_SECRET_KEY`.
3. Set `OPENAI_API_KEY`.
4. Set `DATABASE_PATH` to persistent storage.
5. Run behind a production WSGI server (e.g., `gunicorn`).
6. Restrict CORS origins.

Example gunicorn command:

```bash
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

## Troubleshooting

- `OPENAI_API_KEY is not set.`
  - Add key in `.env`, restart backend.

- `APP_SECRET_KEY must be set when APP_ENV is production.`
  - Set `APP_SECRET_KEY` before startup.

- `Authentication required.`
  - Send `Authorization: Bearer <token>` header.

- SQLite install?
  - No extra install needed; Python already includes `sqlite3`.
