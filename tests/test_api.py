from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from django_notifications.models import UserNotification
from django_notifications.services import create_user_notification

User = get_user_model()


@pytest.mark.django_db
def test_notifications_api_lists_marks_and_deletes_notifications() -> None:
    user = User.objects.create_user(username="notify", email="notify@example.com")
    api_client = APIClient()
    create_user_notification(
        user=user,
        notification_type=UserNotification.Type.DATA_EXPORT_READY,
        title="Export ready",
        message="Your export is ready to download.",
        related_object_type="data_export",
        related_object_id="export-1",
        action_url="/profile",
        metadata={"action": "download_export", "label": "Download"},
    )
    other = create_user_notification(
        user=user,
        notification_type=UserNotification.Type.REPORT_FAILED,
        title="Report failed",
        message="April report could not be generated.",
        related_object_type="report",
        related_object_id="report-1",
        action_url="/reports",
        metadata={"action": "open_route", "label": "View reports"},
    )
    api_client.force_authenticate(user=user)

    list_response = api_client.get("/api/notifications/")
    count_response = api_client.get("/api/notifications/unread-count/")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 2
    assert count_response.status_code == 200
    assert count_response.json()["unread_count"] == 2

    mark_read_response = api_client.post(f"/api/notifications/{other.id}/mark-read/")

    assert mark_read_response.status_code == 200
    assert mark_read_response.json()["is_read"] is True

    mark_all_response = api_client.post("/api/notifications/mark-all-read/")

    assert mark_all_response.status_code == 200
    assert mark_all_response.json()["marked_count"] == 1

    delete_response = api_client.delete(f"/api/notifications/{other.id}/")

    assert delete_response.status_code == 204
    assert UserNotification.objects.filter(user=user).count() == 1


@pytest.mark.django_db
@override_settings(
    DJANGO_NOTIFICATIONS_SETTINGS_PROVIDER="tests.helpers.get_notification_setting_overrides",
)
def test_notifications_api_returns_client_config_from_provider() -> None:
    user = User.objects.create_user(username="config", email="config@example.com")
    api_client = APIClient()
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/notifications/config/")

    assert response.status_code == 200
    assert response.json() == {"poll_interval_seconds": 45}

