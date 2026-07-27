from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone


class UUIDTimestampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class NotificationType(models.TextChoices):
    INFO = "info", "Info"
    SUCCESS = "success", "Success"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"
    REPORT_READY = "report_ready", "Report ready"
    REPORT_FAILED = "report_failed", "Report failed"
    DATA_EXPORT_READY = "data_export_ready", "Data export ready"
    DATA_EXPORT_FAILED = "data_export_failed", "Data export failed"
    DATA_IMPORT_READY = "data_import_ready", "Data import ready"
    DATA_IMPORT_FAILED = "data_import_failed", "Data import failed"


class NotificationDispatch(UUIDTimestampedModel):
    class RecipientMode(models.TextChoices):
        ALL_USERS = "all_users", "All active users"
        SELECTED_USERS = "selected_users", "Selected users"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notification_dispatches",
    )
    recipient_mode = models.CharField(
        max_length=32,
        choices=RecipientMode.choices,
        default=RecipientMode.SELECTED_USERS,
    )
    selected_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="notification_dispatches",
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_object_type = models.CharField(max_length=50, blank=True, default="")
    related_object_id = models.CharField(max_length=64, blank=True, default="")
    action_url = models.CharField(max_length=500, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    targeted_recipient_count = models.PositiveIntegerField(default=0)
    delivered_recipient_count = models.PositiveIntegerField(default=0)
    failed_recipient_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        db_table = "notifications_notification_dispatch"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="notifications_dispatch_status_idx"),
            models.Index(fields=["recipient_mode"], name="notifications_dispatch_mode_idx"),
            models.Index(fields=["-created_at"], name="notifications_dispatch_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_dispatchable(self) -> bool:
        return self.status in {self.Status.DRAFT, self.Status.FAILED}


class UserNotification(UUIDTimestampedModel):
    Type = NotificationType

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    source_dispatch = models.ForeignKey(
        NotificationDispatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True, default="")
    related_object_id = models.CharField(max_length=64, blank=True, default="")
    action_url = models.CharField(max_length=500, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "notifications_user_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="notifications_user_created_idx"),
            models.Index(fields=["user", "is_read"], name="notifications_user_read_idx"),
            models.Index(fields=["user", "notification_type"], name="notifications_user_type_idx"),
            models.Index(
                fields=["source_dispatch"],
                name="notifications_user_dispatch_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.notification_type}:{self.title}"

    def mark_as_read(self) -> None:
        if self.is_read:
            return
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at", "updated_at"])

    @property
    def has_action(self) -> bool:
        metadata = self.metadata if isinstance(self.metadata, dict) else {}
        return bool(self.action_url or metadata.get("action"))

    @property
    def metadata_dict(self) -> dict[str, Any]:
        return self.metadata if isinstance(self.metadata, dict) else {}

