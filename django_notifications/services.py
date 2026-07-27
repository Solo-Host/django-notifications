"""Core services for persistent notifications and admin dispatches."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from django_notifications.conf import get_notification_settings
from django_notifications.models import NotificationDispatch, NotificationType, UserNotification


def notification_expiration(*, expires_at: datetime | None = None) -> datetime | None:
    if expires_at is not None:
        return expires_at
    settings = get_notification_settings()
    return timezone.now() + timedelta(days=settings["retention_days"])


def create_user_notification(
    *,
    user: Any | None = None,
    user_id: Any | None = None,
    notification_type: NotificationType | str,
    title: str,
    message: str,
    related_object_type: str = "",
    related_object_id: str = "",
    action_url: str = "",
    metadata: dict[str, Any] | None = None,
    expires_at: datetime | None = None,
    source_dispatch: NotificationDispatch | None = None,
) -> UserNotification:
    if user is None and user_id is None:
        msg = "Either user or user_id must be provided when creating a notification."
        raise ValidationError(msg)
    create_kwargs: dict[str, Any] = {
        "notification_type": str(notification_type),
        "title": title,
        "message": message,
        "related_object_type": related_object_type,
        "related_object_id": related_object_id,
        "action_url": action_url,
        "metadata": metadata or {},
        "expires_at": notification_expiration(expires_at=expires_at),
        "source_dispatch": source_dispatch,
    }
    if user is not None:
        create_kwargs["user"] = user
    else:
        create_kwargs["user_id"] = user_id
    return UserNotification.objects.create(**create_kwargs)


def cleanup_expired_notifications() -> int:
    queryset = UserNotification.objects.filter(expires_at__lt=timezone.now())
    deleted_count = queryset.count()
    queryset.delete()
    return deleted_count


def unread_count_for_user(user: Any) -> int:
    return (
        UserNotification.objects.filter(user=user, is_read=False)
        .exclude(expires_at__lt=timezone.now())
        .count()
    )


def list_notifications_for_user(user: Any) -> QuerySet[UserNotification]:
    return UserNotification.objects.filter(user=user).exclude(expires_at__lt=timezone.now())


def dispatch_recipient_queryset(dispatch: NotificationDispatch) -> QuerySet[Any]:
    user_model = get_user_model()
    queryset = user_model._default_manager.filter(is_active=True)
    if dispatch.recipient_mode == NotificationDispatch.RecipientMode.SELECTED_USERS:
        queryset = queryset.filter(
            pk__in=dispatch.selected_users.values_list("pk", flat=True),
        )
    return queryset.order_by("pk")


def queue_notification_dispatch(dispatch: NotificationDispatch) -> NotificationDispatch:
    if not dispatch.is_dispatchable:
        msg = "Only draft or failed notification dispatches can be queued."
        raise ValidationError(msg)
    if (
        dispatch.recipient_mode == NotificationDispatch.RecipientMode.SELECTED_USERS
        and not dispatch.selected_users.exists()
    ):
        msg = "Select at least one user before queueing a selected-users dispatch."
        raise ValidationError(msg)
    now = timezone.now()
    dispatch.status = NotificationDispatch.Status.QUEUED
    dispatch.queued_at = now
    dispatch.started_at = None
    dispatch.completed_at = None
    dispatch.targeted_recipient_count = 0
    dispatch.delivered_recipient_count = 0
    dispatch.failed_recipient_count = 0
    dispatch.last_error = ""
    dispatch.save(
        update_fields=[
            "status",
            "queued_at",
            "started_at",
            "completed_at",
            "targeted_recipient_count",
            "delivered_recipient_count",
            "failed_recipient_count",
            "last_error",
            "updated_at",
        ]
    )
    from django_notifications.tasks import deliver_notification_dispatch

    dispatch_id = str(dispatch.pk)
    transaction.on_commit(lambda: deliver_notification_dispatch.delay(dispatch_id))
    return dispatch


def dispatch_notification_dispatch(dispatch: NotificationDispatch) -> dict[str, int]:
    recipient_ids = list(dispatch_recipient_queryset(dispatch).values_list("pk", flat=True))
    targeted_count = len(recipient_ids)
    dispatch.status = NotificationDispatch.Status.PROCESSING
    dispatch.started_at = timezone.now()
    dispatch.completed_at = None
    dispatch.targeted_recipient_count = targeted_count
    dispatch.delivered_recipient_count = 0
    dispatch.failed_recipient_count = 0
    dispatch.last_error = ""
    dispatch.save(
        update_fields=[
            "status",
            "started_at",
            "completed_at",
            "targeted_recipient_count",
            "delivered_recipient_count",
            "failed_recipient_count",
            "last_error",
            "updated_at",
        ]
    )
    delivered_count = 0
    try:
        for user_id in recipient_ids:
            create_user_notification(
                user_id=user_id,
                source_dispatch=dispatch,
                notification_type=dispatch.notification_type,
                title=dispatch.title,
                message=dispatch.message,
                related_object_type=dispatch.related_object_type,
                related_object_id=dispatch.related_object_id,
                action_url=dispatch.action_url,
                metadata=dispatch.metadata,
                expires_at=dispatch.expires_at,
            )
            delivered_count += 1
    except Exception as exc:
        dispatch.status = NotificationDispatch.Status.FAILED
        dispatch.completed_at = timezone.now()
        dispatch.delivered_recipient_count = delivered_count
        dispatch.failed_recipient_count = max(targeted_count - delivered_count, 0)
        dispatch.last_error = str(exc)
        dispatch.save(
            update_fields=[
                "status",
                "completed_at",
                "delivered_recipient_count",
                "failed_recipient_count",
                "last_error",
                "updated_at",
            ]
        )
        raise

    dispatch.status = NotificationDispatch.Status.COMPLETED
    dispatch.completed_at = timezone.now()
    dispatch.delivered_recipient_count = delivered_count
    dispatch.failed_recipient_count = max(targeted_count - delivered_count, 0)
    dispatch.last_error = ""
    dispatch.save(
        update_fields=[
            "status",
            "completed_at",
            "delivered_recipient_count",
            "failed_recipient_count",
            "last_error",
            "updated_at",
        ]
    )
    return {
        "targeted": targeted_count,
        "delivered": delivered_count,
        "failed": max(targeted_count - delivered_count, 0),
    }
