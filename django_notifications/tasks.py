"""Celery tasks for notification delivery and cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from django_notifications.conf import get_notification_settings
from django_notifications.models import NotificationDispatch
from django_notifications.services import (
    cleanup_expired_notifications,
    dispatch_notification_dispatch,
)

NOTIFICATION_CLEANUP_CACHE_KEY = "notifications:last-cleanup-at"


@shared_task(name="django_notifications.tasks.cleanup_expired_notifications")
def cleanup_notifications() -> dict[str, int]:
    settings = get_notification_settings()
    interval_hours = int(settings["cleanup_interval_hours"])
    if interval_hours > 0:
        last_run = cache.get(NOTIFICATION_CLEANUP_CACHE_KEY)
        if isinstance(last_run, str):
            parsed = datetime.fromisoformat(last_run)
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone=UTC)
            if parsed + timedelta(hours=interval_hours) > timezone.now():
                return {"deleted": 0}
    deleted = cleanup_expired_notifications()
    cache.set(NOTIFICATION_CLEANUP_CACHE_KEY, timezone.now().isoformat(), None)
    return {"deleted": deleted}


@shared_task(name="django_notifications.tasks.deliver_notification_dispatch")
def deliver_notification_dispatch(dispatch_id: str) -> dict[str, int]:
    dispatch = NotificationDispatch.objects.get(pk=dispatch_id)
    return dispatch_notification_dispatch(dispatch)
