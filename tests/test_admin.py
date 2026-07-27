from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from django_notifications.models import NotificationDispatch

User = get_user_model()


@pytest.mark.django_db
def test_notification_dispatch_admin_add_view_can_queue_dispatch() -> None:
    admin_user = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="pw-correct-horse-battery",
    )
    first = User.objects.create_user(username="first", email="first@example.com")
    second = User.objects.create_user(username="second", email="second@example.com")
    client = Client()
    client.force_login(admin_user)

    with patch("django_notifications.admin.queue_notification_dispatch") as queue_mock:
        response = client.post(
            reverse("admin:notifications_notificationdispatch_add"),
            data={
                "title": "Send notice",
                "notification_type": NotificationDispatch._meta.get_field(
                    "notification_type"
                ).default,
                "message": "Testing admin dispatch",
                "recipient_mode": NotificationDispatch.RecipientMode.SELECTED_USERS,
                "selected_users": [str(first.pk), str(second.pk)],
                "action_url": "/dashboard",
                "metadata": "{}",
                "related_object_type": "",
                "related_object_id": "",
                "expires_at": "",
                "queue_now": "on",
                "_save": "Save",
            },
        )

    assert response.status_code == 302
    dispatch = NotificationDispatch.objects.get(title="Send notice")
    assert dispatch.created_by == admin_user
    assert set(dispatch.selected_users.values_list("pk", flat=True)) == {first.pk, second.pk}
    queue_mock.assert_called_once_with(dispatch)

