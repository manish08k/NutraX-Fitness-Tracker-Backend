from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time

from app.core.config import settings
from app.core.logger import logger
from app.db.postgres import init_db
from app.db.firebase import init_firebase
from app.db.redis import close_redis
from app.api.routes import auth, user, workout, diet, ai


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    init_firebase()
    await init_db()
    logger.info("✅ All services connected")
    yield
    # ── Shutdown ──────────────────────────────────────────────────
    await close_redis()
    logger.info("👋 Shutdown complete")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version=settings.APP_VERSION,
    description="Production backend for GymBrain — fitness, AI coaching, nutrition tracking",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# ── Middleware ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 2)
    response.headers["X-Response-Time"] = f"{duration_ms}ms"
    if duration_ms > 2000:
        logger.warning(f"Slow request: {request.method} {request.url.path} took {duration_ms}ms")
    return response


# ── Global Error Handlers ─────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({"field": field, "message": error["msg"]})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation failed", "details": errors},
    )


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An unexpected error occurred. Please try again."},
    )


# ── Routers ───────────────────────────────────────────────────────
app.include_router(auth.router,    prefix="/api/v1/auth",     tags=["Auth"])
app.include_router(user.router,    prefix="/api/v1/users",    tags=["Users"])
app.include_router(workout.router, prefix="/api/v1/workouts", tags=["Workouts"])
app.include_router(diet.router,    prefix="/api/v1/diet",     tags=["Diet"])
app.include_router(ai.router,      prefix="/api/v1/ai",       tags=["AI"])


# ── Health Check ─────────────────────────────────────────────────
@app.get("/health", include_in_schema=False)
async def health():
    from app.db.redis import ping_redis
    from app.db.postgres import ping_db
    db_ok = await ping_db()
    redis_ok = await ping_redis()
    all_ok = db_ok and redis_ok
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "healthy" if all_ok else "degraded",
            "version": settings.APP_VERSION,
            "services": {"postgres": db_ok, "redis": redis_ok},
        },
    )
