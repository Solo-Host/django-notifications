"""Notification API endpoints."""

from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django_notifications.conf import get_notification_settings
from django_notifications.models import UserNotification
from django_notifications.serializers import UserNotificationSerializer
from django_notifications.services import list_notifications_for_user, unread_count_for_user


class NotificationCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField(min_value=0)


class NotificationConfigSerializer(serializers.Serializer):
    poll_interval_seconds = serializers.IntegerField(min_value=1)


class NotificationListView(generics.ListAPIView[UserNotification]):
    serializer_class = UserNotificationSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None

    def get_queryset(self) -> QuerySet[UserNotification]:
        user = cast(Any, self.request.user)
        queryset = list_notifications_for_user(user)
        unread_only = self.request.query_params.get("unread_only", "").lower() in {
            "1",
            "true",
            "yes",
        }
        if unread_only:
            queryset = queryset.filter(is_read=False)
        notification_type = self.request.query_params.get("notification_type", "").strip()
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        return queryset.order_by("-created_at")


class NotificationUnreadCountView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        return Response(
            NotificationCountSerializer(
                {"unread_count": unread_count_for_user(cast(Any, request.user))}
            ).data
        )


class NotificationMarkReadView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request, notification_id: str) -> Response:
        notification = get_object_or_404(
            list_notifications_for_user(cast(Any, request.user)),
            pk=notification_id,
        )
        notification.mark_as_read()
        return Response(UserNotificationSerializer(notification).data, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        queryset = list_notifications_for_user(cast(Any, request.user)).filter(is_read=False)
        now = timezone.now()
        marked_count = queryset.update(is_read=True, read_at=now, updated_at=now)
        return Response({"marked_count": marked_count}, status=status.HTTP_200_OK)


class NotificationDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request: Request, notification_id: str) -> Response:
        notification = get_object_or_404(
            list_notifications_for_user(cast(Any, request.user)),
            pk=notification_id,
        )
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationClientConfigView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        del request
        settings = get_notification_settings()
        return Response({"poll_interval_seconds": settings["poll_interval_seconds"]})
