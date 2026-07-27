from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils.module_loading import import_string

DEFAULT_NOTIFICATION_SETTINGS: dict[str, int] = {
    "poll_interval_seconds": 30,
    "retention_days": 30,
    "cleanup_interval_hours": 24,
    "duration_threshold_seconds": 5,
    "export_records_per_second": 250,
    "export_attachments_per_second": 5,
    "import_megabytes_per_second": 2,
}


def _provider_overrides() -> dict[str, Any]:
    provider_path = getattr(settings, "DJANGO_NOTIFICATIONS_SETTINGS_PROVIDER", "")
    if not provider_path:
        return {}
    provider = import_string(provider_path)
    overrides = provider()
    if not isinstance(overrides, dict):
        msg = "DJANGO_NOTIFICATIONS_SETTINGS_PROVIDER must return a dict of overrides."
        raise TypeError(msg)
    return overrides


def get_notification_settings() -> dict[str, int]:
    configured = getattr(settings, "DJANGO_NOTIFICATIONS", {})
    if not isinstance(configured, dict):
        msg = "DJANGO_NOTIFICATIONS must be a dict of notification settings overrides."
        raise TypeError(msg)
    merged = {
        **DEFAULT_NOTIFICATION_SETTINGS,
        **_provider_overrides(),
        **configured,
    }
    return {key: int(merged[key]) for key in DEFAULT_NOTIFICATION_SETTINGS}

