from __future__ import annotations

from django.apps import AppConfig


class DjangoNotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_notifications"
    label = "notifications"
    verbose_name = "Notifications"
