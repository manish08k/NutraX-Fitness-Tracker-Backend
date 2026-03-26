# NutraX Fitness Tracker — Backend API

> Production-grade FastAPI backend for the NutraX fitness tracking app. Built for scale with async Python, background task processing, AI coaching, and real-time push notifications.

---

## 🏗️ System Architecture

```
Flutter App (iOS / Android)
         │
         │  Firebase ID Token (JWT)
         ▼
  ┌─────────────────────────────────────────┐
  │           Fly.io Edge Proxy             │  ← TLS termination, load balancing
  │         (built-in Nginx layer)          │    No manual Nginx config needed
  └─────────────────┬───────────────────────┘
                    │
         ┌──────────▼──────────┐
         │   FastAPI (Python)  │  2 worker processes on Fly.io
         │   Uvicorn ASGI      │  async/await throughout
         └──────┬──────┬───────┘
                │      │
    ┌───────────▼─┐  ┌─▼────────────────┐
    │  Supabase   │  │   Redis Cloud     │
    │ PostgreSQL  │  │  (broker + cache) │
    │  (async)    │  └─┬────────────────┘
    └─────────────┘    │
                  ┌────▼────────────────┐
                  │  Celery Worker      │  separate process on Fly.io
                  │  Background Tasks   │
                  └────┬────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    Firebase Admin   Gemini AI   Resend Email
    (Auth + FCM)    (AI Coach)  (Transactional)
```

### Why this architecture is efficient

| Component | Role | Why chosen |
|-----------|------|------------|
| **FastAPI** | HTTP API layer | Async-first, fastest Python framework, auto OpenAPI docs |
| **Uvicorn** | ASGI server | Non-blocking I/O, handles thousands of concurrent connections |
| **SQLAlchemy async** | ORM | Non-blocking DB queries with asyncpg driver |
| **Celery + Redis** | Task queue | Heavy work (AI, emails, push) offloaded — API stays fast |
| **Redis Cloud** | Broker + result backend | Sub-millisecond pub/sub, persistent task results |
| **Supabase** | PostgreSQL | Managed Postgres with connection pooling built in |
| **Fly.io proxy** | TLS + routing | Zero-config HTTPS, replaces need for manual Nginx |
| **Firebase Auth** | Authentication | Stateless JWT verification, no session storage needed |

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point, startup/shutdown hooks
│   ├── core/
│   │   ├── config.py        # Pydantic settings — all env vars in one place
│   │   ├── database.py      # Async SQLAlchemy engine + session factory
│   │   ├── firebase.py      # Firebase Admin SDK initialization
│   │   └── security.py      # JWT verification middleware
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py      # /auth/verify, /auth/onboard, /auth/me
│   │       ├── users.py     # /users/profile, /users/tdee
│   │       ├── workouts.py  # /workouts/sessions, /workouts/stats, PRs
│   │       ├── diet.py      # /diet/logs, /diet/water
│   │       └── ai.py        # /ai/chat, /ai/workout-plan, /ai/meal-plan
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic layer
│   └── tasks/
│       ├── worker.py        # Celery app configuration
│       └── tasks.py         # Background task definitions
├── migrations/              # Alembic migration files
├── tests/                   # pytest test suite
├── scripts/                 # Utility scripts
├── Dockerfile               # Multi-stage production build
├── fly.toml                 # Fly.io deployment config
├── alembic.ini              # Alembic configuration
└── requirements.txt         # Python dependencies
```

---

## ⚡ Tech Stack

- **Runtime**: Python 3.11
- **Framework**: FastAPI 0.115 + Uvicorn 0.32 (ASGI)
- **Database**: PostgreSQL via SQLAlchemy 2.0 (async) + asyncpg driver
- **Migrations**: Alembic 1.14
- **Task Queue**: Celery 5.4 + Redis 5.2
- **Auth**: Firebase Admin 6.6 (JWT verification)
- **AI**: Google Gemini 2.0 Flash
- **Push Notifications**: Firebase Cloud Messaging (FCM)
- **Email**: Resend
- **Deployment**: Fly.io (Docker-based, Mumbai region)

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Redis (via Homebrew on Mac)
- PostgreSQL (via Supabase — no local install needed)

### 1. Clone and set up

```bash
git clone https://github.com/manish08k/NutraX-Fitness-Tracker-Backend.git
cd NutraX-Fitness-Tracker-Backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install and start local Redis

```bash
brew install redis
brew services start redis
redis-cli ping   # should return PONG
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# App
SECRET_KEY=your-32-char-secret-key
ENVIRONMENT=development
DEBUG=true

# PostgreSQL (Supabase)
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres

# Redis — use local for dev, Redis Cloud URL for prod
REDIS_URL=redis://localhost:6379/0

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}

# Gemini AI
GEMINI_API_KEY=AIza...

# Email (optional for dev)
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@yourdomain.com
```

### 4. Run database migrations

```bash
./venv/bin/alembic upgrade head
```

### 5. Start the API server

```bash
# Terminal 1 — API
./venv/bin/uvicorn app.main:app --reload

# Terminal 2 — Background worker
./venv/bin/celery -A app.tasks.worker worker --loglevel=info
```

API docs available at: http://localhost:8000/docs

---

## 🌐 Deploying to Production (Fly.io)

### 1. Install Fly CLI and login

```bash
curl -L https://fly.io/install.sh | sh
flyctl auth login
```

### 2. Create the app

```bash
flyctl apps create gymbrain-api
flyctl regions set bom    # Mumbai region
```

### 3. Set production secrets

```bash
flyctl secrets set \
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  DATABASE_URL="postgresql+asyncpg://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres" \
  REDIS_URL="redis://default:PASSWORD@redis-14204.c228.us-central1-1.gce.redislabs.com:14204" \
  FIREBASE_PROJECT_ID="your-project-id" \
  GEMINI_API_KEY="AIza..." \
  RESEND_API_KEY="re_..." \
  EMAIL_FROM="noreply@yourdomain.com"

flyctl secrets set FIREBASE_CREDENTIALS_JSON="$(cat firebase-credentials.json | tr -d '\n')"
```

### 4. Deploy

```bash
flyctl deploy
```

### 5. Run migrations on production

```bash
flyctl ssh console -C "alembic upgrade head"
```

### 6. Verify

```bash
curl https://gymbrain-api.fly.dev/health
# {"status":"healthy","version":"1.0.0","services":{"postgres":true,"redis":true}}

curl https://gymbrain-api.fly.dev/docs
```

### 7. Monitor logs

```bash
flyctl logs --tail
```

---

## 📡 API Reference

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/verify` | None | Check if Firebase user exists |
| POST | `/api/v1/auth/onboard` | None | Register new user with profile |
| POST | `/api/v1/auth/logout` | Bearer | Logout and invalidate token |
| GET | `/api/v1/auth/me` | Bearer | Get current user info |

### User Profile

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/users/profile` | Bearer | Get full profile |
| PATCH | `/api/v1/users/profile` | Bearer | Update profile fields |
| GET | `/api/v1/users/tdee` | Bearer | Calculate TDEE + macro targets |

### Workouts

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/workouts/exercises` | Bearer | Full exercise library |
| POST | `/api/v1/workouts/sessions` | Bearer | Log a workout session |
| GET | `/api/v1/workouts/sessions` | Bearer | Workout history |
| GET | `/api/v1/workouts/stats` | Bearer | Aggregate stats + PRs |
| GET | `/api/v1/workouts/personal-records` | Bearer | All personal records |

### Diet & Nutrition

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/diet/logs` | Bearer | Log a meal |
| GET | `/api/v1/diet/logs/{date}` | Bearer | Daily nutrition breakdown |
| GET | `/api/v1/diet/logs/week/{date}` | Bearer | Weekly nutrition summary |
| POST | `/api/v1/diet/water` | Bearer | Log water intake |
| GET | `/api/v1/diet/water/{date}` | Bearer | Daily water tracking |

### AI Coach

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/ai/chat` | Bearer | Conversational AI coach |
| POST | `/api/v1/ai/workout-plan` | Premium | Generate personalised workout plan |
| POST | `/api/v1/ai/meal-plan` | Premium | Generate personalised meal plan |
| POST | `/api/v1/ai/analyze-workout` | Bearer | Analyse last workout session |
| POST | `/api/v1/ai/form-tips` | Bearer | Exercise form guidance |
| GET | `/api/v1/ai/nutrition-advice` | Bearer | Today's nutrition AI feedback |
| GET | `/api/v1/ai/motivate` | Bearer | Personalised motivational message |

### Authentication Flow (Flutter)

```dart
// 1. Sign in with Firebase
final userCredential = await FirebaseAuth.instance.signInWithGoogle(...);
final idToken = await userCredential.user!.getIdToken();

// 2. Check if user exists
final res = await dio.post('/api/v1/auth/verify', data: {'id_token': idToken});
if (res.data['status'] == 'new_user') {
  // → Onboarding screen
} else {
  // → Home screen
}

// 3. All requests use Bearer token
dio.options.headers['Authorization'] = 'Bearer $idToken';

// 4. Auto-refresh Firebase token (expires every 1 hour)
FirebaseAuth.instance.idTokenChanges().listen((user) async {
  if (user != null) {
    final fresh = await user.getIdToken(true);
    dio.options.headers['Authorization'] = 'Bearer $fresh';
  }
});
```

---

## ⚙️ Background Tasks (Celery)

Tasks are processed asynchronously — API responses stay fast while heavy work runs in the background.

| Task | Queue | Trigger |
|------|-------|---------|
| `send_welcome_notification` | notifications | New user onboards |
| `post_workout_analytics` | analytics | Workout session logged |
| `send_push_notification` | notifications | Various user events |
| `send_email_notification` | email | Account events |
| `send_streak_reminders` | notifications | Daily cron at 6 PM IST |

---

## 🔧 Infrastructure Notes

### Nginx
Not needed locally or on Fly.io. Fly's built-in edge proxy handles TLS termination, HTTP→HTTPS redirect, and load balancing across your app instances automatically.

### Docker
Not needed locally. Fly.io uses the `Dockerfile` in the repo automatically when you run `flyctl deploy`. Docker is only used in the CI/CD pipeline and by Fly — you never run it manually.

### Redis
- **Local dev**: `redis://localhost:6379/0` (brew-managed)
- **Production**: Redis Cloud instance via `redis://` (free tier, no TLS)
- Celery uses Redis as both the **message broker** (task dispatch) and **result backend** (task status/output)

### Scaling

```bash
# Scale to 2 API instances (zero downtime)
flyctl scale count 2 --process-group app

# Add more Celery workers
flyctl scale count 2 --process-group worker

# Upgrade machine size
flyctl scale vm shared-cpu-2x --process-group app
```

---

## 🧪 Running Tests

```bash
./venv/bin/pytest tests/ -v
```

---

## 📊 Health Check

```
GET /health
```

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "postgres": true,
    "redis": true
  }
}
```

---

## 🔑 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | 32-char random hex for JWT signing |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://...` Supabase URI |
| `REDIS_URL` | ✅ | Redis connection URL |
| `FIREBASE_PROJECT_ID` | ✅ | Firebase project ID |
| `FIREBASE_CREDENTIALS_JSON` | ✅ | Full service account JSON as string |
| `GEMINI_API_KEY` | ✅ | Google AI Studio API key |
| `RESEND_API_KEY` | ❌ | Resend email API key (optional) |
| `EMAIL_FROM` | ❌ | Sender email address |
| `ENVIRONMENT` | ❌ | `development` or `production` |
| `DEBUG` | ❌ | `true` / `false` |

---

## 📄 License

MIT
