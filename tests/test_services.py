from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from django_notifications.conf import DEFAULT_NOTIFICATION_SETTINGS, get_notification_settings
from django_notifications.models import NotificationDispatch, UserNotification
from django_notifications.services import (
    cleanup_expired_notifications,
    create_user_notification,
    dispatch_notification_dispatch,
    list_notifications_for_user,
    queue_notification_dispatch,
    unread_count_for_user,
)

User = get_user_model()


@pytest.mark.django_db
@override_settings(
    DJANGO_NOTIFICATIONS_SETTINGS_PROVIDER="tests.helpers.get_notification_setting_overrides",
)
def test_get_notification_settings_merges_provider_overrides() -> None:
    settings = get_notification_settings()

    assert settings["poll_interval_seconds"] == 45
    assert settings["retention_days"] == 10
    assert settings["cleanup_interval_hours"] == 12
    assert settings["duration_threshold_seconds"] == DEFAULT_NOTIFICATION_SETTINGS[
        "duration_threshold_seconds"
    ]


@pytest.mark.django_db
def test_queue_notification_dispatch_updates_status_and_enqueues_task() -> None:
    user = User.objects.create_user(username="selected-user", email="selected@example.com")
    dispatch = NotificationDispatch.objects.create(
        title="Planned maintenance",
        notification_type=UserNotification.Type.INFO,
        message="The service will restart tonight.",
        recipient_mode=NotificationDispatch.RecipientMode.SELECTED_USERS,
    )
    dispatch.selected_users.add(user)

    with patch("django_notifications.tasks.deliver_notification_dispatch.delay") as delay_mock:
        queue_notification_dispatch(dispatch)

    dispatch.refresh_from_db()
    assert dispatch.status == NotificationDispatch.Status.QUEUED
    assert dispatch.queued_at is not None
    delay_mock.assert_called_once_with(str(dispatch.pk))


@pytest.mark.django_db
def test_dispatch_notification_dispatch_creates_rows_and_updates_counts() -> None:
    first = User.objects.create_user(username="first", email="first@example.com")
    second = User.objects.create_user(username="second", email="second@example.com")
    dispatch = NotificationDispatch.objects.create(
        title="Release ready",
        notification_type=UserNotification.Type.SUCCESS,
        message="A new release is available.",
        recipient_mode=NotificationDispatch.RecipientMode.ALL_USERS,
        action_url="/releases",
        metadata={"action": "open_route", "label": "Open releases"},
    )

    result = dispatch_notification_dispatch(dispatch)

    dispatch.refresh_from_db()
    assert result == {"targeted": 2, "delivered": 2, "failed": 0}
    assert dispatch.status == NotificationDispatch.Status.COMPLETED
    assert dispatch.targeted_recipient_count == 2
    assert dispatch.delivered_recipient_count == 2
    assert dispatch.failed_recipient_count == 0
    assert UserNotification.objects.filter(source_dispatch=dispatch).count() == 2
    assert {
        notification.user_id
        for notification in UserNotification.objects.filter(source_dispatch=dispatch)
    } == {first.id, second.id}


@pytest.mark.django_db
def test_cleanup_and_notification_queries_ignore_expired_rows() -> None:
    user = User.objects.create_user(username="active", email="active@example.com")
    other_user = User.objects.create_user(username="other", email="other@example.com")
    now = timezone.now()
    create_user_notification(
        user=user,
        notification_type=UserNotification.Type.INFO,
        title="Expired",
        message="Old notification",
        metadata={},
    )
    expired = UserNotification.objects.get(title="Expired")
    expired.expires_at = now - timedelta(minutes=1)
    expired.save(update_fields=["expires_at", "updated_at"])
    active_unread = create_user_notification(
        user=user,
        notification_type=UserNotification.Type.INFO,
        title="Active unread",
        message="Still visible",
        metadata={},
    )
    active_read = create_user_notification(
        user=user,
        notification_type=UserNotification.Type.INFO,
        title="Active read",
        message="Already read",
        metadata={},
    )
    active_read.is_read = True
    active_read.save(update_fields=["is_read", "updated_at"])
    create_user_notification(
        user=other_user,
        notification_type=UserNotification.Type.INFO,
        title="Other user",
        message="Other user visible",
        metadata={},
    )

    unread_before_cleanup = unread_count_for_user(user)
    visible_titles = {notification.title for notification in list_notifications_for_user(user)}
    deleted_count = cleanup_expired_notifications()

    assert unread_before_cleanup == 1
    assert visible_titles == {"Active unread", "Active read"}
    assert deleted_count == 1
    assert UserNotification.objects.filter(id=expired.id).exists() is False
    assert UserNotification.objects.filter(id=active_unread.id).exists() is True

