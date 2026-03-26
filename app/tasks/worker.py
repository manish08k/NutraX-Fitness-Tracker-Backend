from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "gymbrain",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # Upstash Redis requires SSL
    
    task_routes={
        "app.tasks.tasks.send_welcome_notification": {"queue": "notifications"},
        "app.tasks.tasks.post_workout_analytics": {"queue": "analytics"},
        "app.tasks.tasks.send_push_notification": {"queue": "notifications"},
        "app.tasks.tasks.send_email_notification": {"queue": "email"},
    },
    beat_schedule={
        "daily-streak-reminder": {
            "task": "app.tasks.tasks.send_streak_reminders",
            "schedule": 60 * 60 * 18,  # 6 PM IST daily
        },
    },
)
