from __future__ import annotations


def get_notification_setting_overrides() -> dict[str, int]:
    return {
        "poll_interval_seconds": 45,
        "retention_days": 10,
        "cleanup_interval_hours": 12,
    }

