from app.tasks.worker import celery_app
from app.core.logger import logger


@celery_app.task(
    name="app.tasks.tasks.send_welcome_notification",
    bind=True, max_retries=3, default_retry_delay=60
)
def send_welcome_notification(self, user_id: str, full_name: str, email: str):
    """Send welcome email via Resend after user registers."""
    try:
        from app.core.config import settings
        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not set — skipping welcome email")
            return

        import resend
        resend.api_key = settings.RESEND_API_KEY

        first_name = full_name.split()[0]
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": email,
            "subject": f"Welcome to GymBrain, {first_name}! 💪",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
              <h1 style="color: #6366f1;">Welcome to GymBrain! 💪</h1>
              <p>Hey {first_name},</p>
              <p>You've just taken the first step toward your fitness goals. We're stoked to have you!</p>
              <h3>What you can do right now:</h3>
              <ul>
                <li>🏋️ Log your first workout</li>
                <li>🥗 Track your nutrition</li>
                <li>🤖 Chat with your AI fitness coach</li>
                <li>📊 Check your stats and streaks</li>
              </ul>
              <p>Your journey starts today. Let's get it!</p>
              <p><strong>— The GymBrain Team</strong></p>
            </div>
            """,
        })
        logger.info(f"Welcome email sent to {email}")
    except Exception as exc:
        logger.error(f"Welcome email failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.tasks.send_push_notification",
    bind=True, max_retries=3, default_retry_delay=30
)
def send_push_notification(self, fcm_token: str, title: str, body: str, data: dict = None):
    """Send FCM push notification to a device."""
    try:
        from firebase_admin import messaging
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={str(k): str(v) for k, v in (data or {}).items()},
            token=fcm_token,
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default")
                )
            ),
        )
        response = messaging.send(msg)
        logger.info(f"Push sent: {response}")
    except Exception as exc:
        logger.error(f"Push notification failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(name="app.tasks.tasks.post_workout_analytics")
def post_workout_analytics(user_id: str, session_id: str, pr_exercise_ids: list):
    """
    Post-workout background processing:
    - Send PR achievement notifications
    - Update leaderboards
    - Log analytics event
    """
    try:
        from app.core.config import settings
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        # Use sync engine for Celery (not async)
        sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_url, pool_pre_ping=True)

        with Session(engine) as db:
            from app.models.user import User
            from app.models.workout import Exercise
            user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()

            if user and pr_exercise_ids and user.fcm_token:
                # Get exercise names for PRs
                exercises = db.execute(
                    select(Exercise.name).where(Exercise.id.in_(pr_exercise_ids))
                ).scalars().all()

                if exercises:
                    ex_names = ", ".join(list(exercises)[:2])
                    suffix = f" and {len(exercises) - 2} more" if len(exercises) > 2 else ""
                    send_push_notification.delay(
                        fcm_token=user.fcm_token,
                        title="🏆 New Personal Record!",
                        body=f"You crushed it! New PR on {ex_names}{suffix}!",
                        data={"type": "pr", "session_id": session_id},
                    )

        logger.info(f"Post-workout analytics done for session {session_id}")
    except Exception as e:
        logger.error(f"Analytics task failed: {e}")


@celery_app.task(name="app.tasks.tasks.send_streak_reminders")
def send_streak_reminders():
    """
    Daily task: remind users who haven't worked out today to protect their streak.
    Runs at 6 PM IST via Celery Beat.
    """
    try:
        from sqlalchemy import create_engine, select, func
        from sqlalchemy.orm import Session
        from app.core.config import settings
        from app.models.user import User
        from app.models.workout import WorkoutSession
        from datetime import date, datetime, timezone

        sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        engine = create_engine(sync_url, pool_pre_ping=True)
        today = date.today()

        with Session(engine) as db:
            # Users with streak > 0 who haven't logged today
            worked_out_today = db.execute(
                select(WorkoutSession.user_id)
                .where(func.date(WorkoutSession.started_at) == today)
                .distinct()
            ).scalars().all()

            at_risk = db.execute(
                select(User).where(
                    User.current_streak > 0,
                    User.fcm_token.isnot(None),
                    User.is_active == True,
                    User.id.not_in(worked_out_today),
                ).limit(1000)
            ).scalars().all()

            for user in at_risk:
                send_push_notification.delay(
                    fcm_token=user.fcm_token,
                    title=f"🔥 {user.current_streak}-Day Streak at Risk!",
                    body="Log a workout today to keep your streak alive. Even 15 minutes counts!",
                    data={"type": "streak_reminder"},
                )

        logger.info(f"Streak reminders sent to {len(at_risk)} users")
    except Exception as e:
        logger.error(f"Streak reminder task failed: {e}")
