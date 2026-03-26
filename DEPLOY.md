# GymBrain Backend — Production Deployment Guide

## Architecture
```
Flutter App
    ↓  (Firebase ID Token)
Fly.io → FastAPI (2 workers)
    ↓
Supabase (PostgreSQL)   Upstash (Redis TLS)
    ↓
Celery Worker (same Fly.io app, separate process)
    ↓
Firebase Admin (Auth + FCM Push)   Gemini AI
```

---

## Step 1: Services to Set Up (All Free Tiers)

### 1.1 Supabase (PostgreSQL)
1. Go to https://supabase.com → New Project
2. **Settings → Database → Connection String → URI**
3. Copy the URI — it looks like:
   `postgresql://postgres:[password]@db.xxxx.supabase.co:5432/postgres`
4. **Change** `postgresql://` → `postgresql+asyncpg://` for async driver

### 1.2 Upstash (Redis)
1. Go to https://upstash.com → Create Database → Redis
2. Choose **Global** region (or Mumbai)
3. **Details tab** → Copy **Redis URL** (starts with `rediss://`)

### 1.3 Firebase
1. Firebase Console → Project Settings → Service Accounts
2. **Generate new private key** → downloads `firebase-credentials.json`
3. Enable **Authentication** → Sign-in methods (Google, Phone, Email)
4. Enable **Cloud Messaging** (for push notifications)
5. Copy your **Project ID** from Project Settings

### 1.4 Gemini API
1. Go to https://aistudio.google.com/app/apikey
2. Create API key → copy it

### 1.5 Resend (Email) — Optional
1. Go to https://resend.com → create account (free: 3000 emails/month)
2. Add your domain or use `onboarding@resend.dev` for testing
3. Copy API key

---

## Step 2: Fly.io Setup

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Create app (run from backend/ directory)
flyctl apps create gymbrain-api

# Set your primary region (Mumbai)
flyctl regions set bom
```

---

## Step 3: Set All Secrets on Fly.io

```bash
# Generate a strong secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Set all secrets (replace values with your actual ones)
flyctl secrets set \
  SECRET_KEY="your-32-char-secret-key-here" \
  DATABASE_URL="postgresql+asyncpg://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres" \
  REDIS_URL="rediss://default:PASSWORD@xxxx.upstash.io:6379" \
  FIREBASE_PROJECT_ID="your-firebase-project-id" \
  GEMINI_API_KEY="AIza..." \
  RESEND_API_KEY="re_..." \
  EMAIL_FROM="noreply@yourdomain.com"

# Firebase credentials (paste entire JSON as a string)
flyctl secrets set FIREBASE_CREDENTIALS_JSON="$(cat firebase-credentials.json | tr -d '\n')"
```

---

## Step 4: Deploy

```bash
# From the backend/ directory
flyctl deploy

# Watch logs
flyctl logs

# Check health
curl https://gymbrain-api.fly.dev/health
```

---

## Step 5: Database Migrations

Migrations run **automatically** on every deploy (in the Dockerfile CMD).

To run manually:
```bash
flyctl ssh console
alembic upgrade head
```

To create a new migration after changing models:
```bash
# Locally with .env set
alembic revision --autogenerate -m "add_new_field"
# Then deploy → migrations run automatically
```

---

## Step 6: Verify Everything Works

```bash
# Health check
curl https://gymbrain-api.fly.dev/health

# Should return:
# {"status":"healthy","version":"1.0.0","services":{"postgres":true,"redis":true}}

# Test auth flow (replace TOKEN with a real Firebase ID token)
curl -X POST https://gymbrain-api.fly.dev/api/v1/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"id_token": "YOUR_FIREBASE_ID_TOKEN"}'
```

---

## Flutter App Integration

### Auth Flow
```dart
// 1. Sign in with Firebase on client
final userCredential = await FirebaseAuth.instance.signInWithGoogle(...);
final idToken = await userCredential.user!.getIdToken();

// 2. Verify with backend
final response = await dio.post('/api/v1/auth/verify', data: {'id_token': idToken});

if (response.data['status'] == 'new_user') {
  // Go to onboarding screen
} else {
  // User exists, proceed to home
}

// 3. Onboard new users
await dio.post('/api/v1/auth/onboard', data: {
  'id_token': idToken,
  'full_name': 'John Doe',
  'username': 'johndoe',
  'fitness_goal': 'muscle_gain',
  ...
});

// 4. All subsequent requests: attach token as Bearer
dio.options.headers['Authorization'] = 'Bearer $idToken';

// Note: Firebase tokens expire every 1 hour — refresh automatically:
FirebaseAuth.instance.idTokenChanges().listen((user) async {
  if (user != null) {
    final freshToken = await user.getIdToken(true);
    dio.options.headers['Authorization'] = 'Bearer $freshToken';
  }
});
```

---

## API Endpoints Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/verify` | None | Check if user exists |
| POST | `/api/v1/auth/onboard` | None | Register new user |
| POST | `/api/v1/auth/logout` | Bearer | Logout |
| GET | `/api/v1/auth/me` | Bearer | Current user |
| GET | `/api/v1/users/profile` | Bearer | My profile |
| PATCH | `/api/v1/users/profile` | Bearer | Update profile |
| GET | `/api/v1/users/tdee` | Bearer | Calculate TDEE + macros |
| GET | `/api/v1/workouts/exercises` | Bearer | Exercise library |
| POST | `/api/v1/workouts/sessions` | Bearer | Log workout |
| GET | `/api/v1/workouts/sessions` | Bearer | Workout history |
| GET | `/api/v1/workouts/stats` | Bearer | Full stats + PRs |
| GET | `/api/v1/workouts/personal-records` | Bearer | Personal records |
| POST | `/api/v1/diet/logs` | Bearer | Log meal |
| GET | `/api/v1/diet/logs/{date}` | Bearer | Daily nutrition |
| GET | `/api/v1/diet/logs/week/{date}` | Bearer | Weekly summary |
| POST | `/api/v1/diet/water` | Bearer | Log water |
| GET | `/api/v1/diet/water/{date}` | Bearer | Daily water |
| POST | `/api/v1/ai/chat` | Bearer | AI coach chat |
| POST | `/api/v1/ai/workout-plan` | Premium | AI workout plan |
| POST | `/api/v1/ai/meal-plan` | Premium | AI meal plan |
| POST | `/api/v1/ai/analyze-workout` | Bearer | Analyse last workout |
| POST | `/api/v1/ai/form-tips` | Bearer | Exercise form tips |
| GET | `/api/v1/ai/nutrition-advice` | Bearer | Today's nutrition AI |
| GET | `/api/v1/ai/motivate` | Bearer | Motivational message |

---

## Scaling on Fly.io

```bash
# Scale to 2 app instances (zero downtime)
flyctl scale count 2 --process-group app

# Upgrade machine size
flyctl scale vm shared-cpu-2x --process-group app

# Add more Celery workers
flyctl scale count 2 --process-group worker
```

---

## Monitor in Production

```bash
# Live logs
flyctl logs --tail

# App status
flyctl status

# SSH into running container
flyctl ssh console

# Check Celery worker health
flyctl ssh console --process-group worker -C "celery -A app.tasks.worker.celery_app inspect ping"
```
