from __future__ import annotations

from django.urls import path

from django_notifications.views import (
    NotificationClientConfigView,
    NotificationDetailView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("config/", NotificationClientConfigView.as_view(), name="config"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="unread-count"),
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="mark-all-read"),
    path(
        "<uuid:notification_id>/mark-read/",
        NotificationMarkReadView.as_view(),
        name="mark-read",
    ),
    path("<uuid:notification_id>/", NotificationDetailView.as_view(), name="detail"),
]

