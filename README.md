# django-notifications

Reusable Django app for persistent user notifications, admin-managed notification
dispatches, and a small authenticated API for in-app notification clients.

## Features

- persistent per-user notifications with read/unread tracking
- admin UI for reviewing notifications and composing bulk dispatches
- dispatch modes for all active users or explicitly selected users
- Celery tasks for bulk fan-out and expired-notification cleanup
- optional settings-provider hook so host apps can source notification config
  from their own registry/service layer
- optional DRF URL set for list, unread count, read, and delete actions

## Package settings

`DJANGO_NOTIFICATIONS` accepts a partial dict of overrides:

```python
DJANGO_NOTIFICATIONS = {
    "poll_interval_seconds": 30,
    "retention_days": 30,
    "cleanup_interval_hours": 24,
}
```

`DJANGO_NOTIFICATIONS_SETTINGS_PROVIDER` may point at a dotted-path callable
returning a dict of overrides. Host apps can use that hook to read settings from
their own registry-backed configuration instead of static Django settings.

