"""Celery application configuration."""

from celery import Celery
from .config import settings

# Create Celery app
celery_app = Celery(
    "orchestrator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.orchestrator.tasks.pipeline_tasks"],
)

# Configure Celery for long-running tasks
celery_app.conf.update(
    # Task execution settings
    task_time_limit=settings.task_time_limit,
    task_soft_time_limit=settings.task_soft_time_limit,
    task_acks_late=True,  # Acknowledge after task completes (for reliability)
    task_reject_on_worker_lost=True,  # Requeue if worker dies

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_concurrency=2,  # Number of concurrent workers

    # Result settings
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,  # Store additional task metadata

    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task routing (optional - for scaling)
    task_routes={
        "app.orchestrator.tasks.pipeline_tasks.*": {"queue": "pipeline"},
    },

    # Default queue
    task_default_queue="pipeline",
)


# Optional: Add task events for monitoring
celery_app.conf.worker_send_task_events = True
celery_app.conf.task_send_sent_event = True
