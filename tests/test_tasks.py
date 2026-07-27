from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from django_notifications import tasks as notification_tasks
from django_notifications.models import NotificationDispatch, UserNotification

User = get_user_model()


@pytest.mark.django_db
def test_cleanup_notifications_runs_cleanup_and_updates_cache() -> None:
    cache.delete(notification_tasks.NOTIFICATION_CLEANUP_CACHE_KEY)

    with (
        patch("django_notifications.tasks.get_notification_settings") as settings_mock,
        patch("django_notifications.tasks.cleanup_expired_notifications") as cleanup_mock,
    ):
        settings_mock.return_value = {"cleanup_interval_hours": 24}
        cleanup_mock.return_value = 3

        result = notification_tasks.cleanup_notifications()

    assert result == {"deleted": 3}
    assert isinstance(cache.get(notification_tasks.NOTIFICATION_CLEANUP_CACHE_KEY), str)


@pytest.mark.django_db
def test_cleanup_notifications_skips_when_recent_run_is_cached() -> None:
    cache.set(notification_tasks.NOTIFICATION_CLEANUP_CACHE_KEY, datetime.now().isoformat(), None)

    with (
        patch("django_notifications.tasks.get_notification_settings") as settings_mock,
        patch("django_notifications.tasks.cleanup_expired_notifications") as cleanup_mock,
    ):
        settings_mock.return_value = {"cleanup_interval_hours": 24}

        result = notification_tasks.cleanup_notifications()

    assert result == {"deleted": 0}
    cleanup_mock.assert_not_called()


@pytest.mark.django_db
def test_deliver_notification_dispatch_task_runs_service() -> None:
    user = User.objects.create_user(username="task-user", email="task-user@example.com")
    dispatch = NotificationDispatch.objects.create(
        title="Queued send",
        notification_type=UserNotification.Type.INFO,
        message="Background fan-out test.",
        recipient_mode=NotificationDispatch.RecipientMode.SELECTED_USERS,
    )
    dispatch.selected_users.add(user)

    result = notification_tasks.deliver_notification_dispatch(str(dispatch.pk))

    dispatch.refresh_from_db()
    assert result == {"targeted": 1, "delivered": 1, "failed": 0}
    assert dispatch.status == NotificationDispatch.Status.COMPLETED
    assert UserNotification.objects.filter(source_dispatch=dispatch).count() == 1
