# Deployment Notes — Ethara Seat Allocation System

| Layer    | Service  | URL                                              |
| -------- | -------- | ------------------------------------------------ |
| Frontend | Netlify  | https://ethara-frontend12.netlify.app            |
| Backend  | Render   | https://ethara-backend-xnma.onrender.com         |
| Database | Neon     | PostgreSQL 16 — ap-southeast-1                   |

---

## Backend — Render

### Service Type
Python web service (free tier). Spins down after ~15 min inactivity — first request after sleep takes ~30s.

### Build Command
```
pip install -r requirements.txt
```

### Start Command
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips "*"
```

> `--proxy-headers` is **required**. Without it, Render's reverse proxy strips POST request bodies → every login/create returns 422 with `input: null`.

### Root Directory
`backend/`

### Environment Variables (set in Render dashboard)

| Key                  | Value                                | Notes                             |
| -------------------- | ------------------------------------ | --------------------------------- |
| `DATABASE_URL`       | `postgresql://...neon.tech/neondb?sslmode=require` | Neon pooled URL    |
| `JWT_SECRET_KEY`     | 64-char hex string                   | Fixed — tokens survive restarts   |
| `ALLOWED_ORIGINS_RAW`| `https://ethara-frontend12.netlify.app` | Comma-separated, no quotes      |
| `GROQ_API_KEY`       | `gsk_...`                            | Free at console.groq.com/keys     |
| `DEBUG`              | `false`                              |                                   |

Generate JWT key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Auto-deploy
Render auto-deploys on every push to `main`. To trigger manually: Render dashboard → Manual Deploy → Deploy latest commit.

### CORS
`ALLOWED_ORIGINS_RAW` accepts comma-separated values or JSON array. Both work — pydantic-settings reads it as a plain string then parses in the `@property`.

---

## Frontend — Netlify

### Build Command
```
npm run build
```

### Publish Directory
`frontend/build`

### Environment Variables (set in Netlify dashboard)

| Key                   | Value                                          |
| --------------------- | ---------------------------------------------- |
| `REACT_APP_API_URL`   | `https://ethara-backend-xnma.onrender.com`     |

> This is baked into the CRA bundle at build time. Netlify injects it automatically during `npm run build`.

### SPA Routing — `_redirects`
The file `frontend/public/_redirects` contains:
```
/*    /index.html   200
```
This tells Netlify to serve `index.html` for every path. Without it, refreshing `/login` or `/ai` returns a 404 "Page not found" from Netlify.

CRA copies everything from `public/` into `build/` automatically — verify with `ls frontend/build/_redirects`.

### Auto-deploy
Netlify auto-deploys on every push to `main` from GitHub.

---

## Database — Neon

### Connection
- **Pooled URL** (used in app): `ep-wandering-dream-aoynlys3-pooler.c-2.ap-southeast-1.aws.neon.tech`
- **Direct URL** (for migrations/admin): `ep-wandering-dream-aoynlys3.c-2.ap-southeast-1.aws.neon.tech`

### Schema Setup
Schema was created via `Base.metadata.create_all()` — not Alembic migrations. The `alembic_version` table exists but is empty.

For future schema changes:
```bash
cd backend
DATABASE_URL=<neon-url> alembic revision --autogenerate -m "description"
DATABASE_URL=<neon-url> alembic upgrade head
```

### Data Migration (SQLite → Neon)
Data was bulk-migrated from `ethara_seats.db` using a custom script. After migration, PostgreSQL sequences were reset manually:
```sql
SELECT setval(pg_get_serial_sequence('employees', 'id'), MAX(id)) FROM employees;
-- repeat for all tables
```
Without this, the next INSERT would try `id=1` and fail with `UniqueViolation`.

### Viewing Data
- **Neon Console:** https://console.neon.tech → Tables tab
- **psql:**
  ```bash
  psql "postgresql://neondb_owner:<password>@ep-wandering-dream-aoynlys3-pooler...neon.tech/neondb?sslmode=require"
  ```

---

## Local Development

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # fill in DATABASE_URL
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm start     # http://localhost:3000
```

For local dev, `DATABASE_URL` can point to SQLite (`sqlite:///./ethara_seats.db`) — no Neon needed.

---

## Deployment Checklist

```
[ ] backend/.env has correct DATABASE_URL (Neon), JWT_SECRET_KEY, GROQ_API_KEY
[ ] Render env vars: DATABASE_URL, JWT_SECRET_KEY, ALLOWED_ORIGINS_RAW, GROQ_API_KEY
[ ] Render start command has --proxy-headers flag
[ ] frontend/.env.production has REACT_APP_API_URL
[ ] Netlify env var: REACT_APP_API_URL
[ ] frontend/public/_redirects exists with  /*    /index.html   200
[ ] npm run build succeeds and build/_redirects is present
[ ] python -m pytest tests/ → 174 passed, 3 skipped
[ ] Render redeployed (auto on git push to main)
[ ] Netlify redeployed (auto on git push to main)
[ ] POST /auth/login returns 200 with token (not 422)
[ ] POST /ai/query returns source: "groq" (when GROQ_API_KEY set)
```
