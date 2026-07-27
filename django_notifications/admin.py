from __future__ import annotations

from typing import Any, cast

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest

from django_notifications.models import NotificationDispatch, UserNotification
from django_notifications.services import queue_notification_dispatch


class NotificationDispatchAdminForm(forms.ModelForm):
    queue_now = forms.BooleanField(
        required=False,
        help_text="Queue this dispatch for delivery after saving.",
    )

    class Meta:
        model = NotificationDispatch
        fields = (
            "created_by",
            "recipient_mode",
            "selected_users",
            "notification_type",
            "title",
            "message",
            "related_object_type",
            "related_object_id",
            "action_url",
            "metadata",
            "expires_at",
            "status",
            "queued_at",
            "started_at",
            "completed_at",
            "targeted_recipient_count",
            "delivered_recipient_count",
            "failed_recipient_count",
            "last_error",
        )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        recipient_mode = cleaned_data.get("recipient_mode")
        selected_users = cleaned_data.get("selected_users")
        if (
            recipient_mode == NotificationDispatch.RecipientMode.SELECTED_USERS
            and selected_users is not None
            and hasattr(selected_users, "exists")
            and not selected_users.exists()
        ):
            self.add_error(
                "selected_users",
                "Select at least one user when recipient mode is Selected users.",
            )
        return cleaned_data


@admin.register(NotificationDispatch)
class NotificationDispatchAdmin(admin.ModelAdmin):
    form = NotificationDispatchAdminForm
    list_display = (
        "title",
        "notification_type",
        "recipient_mode",
        "status",
        "targeted_recipient_count",
        "delivered_recipient_count",
        "failed_recipient_count",
        "created_by",
        "queued_at",
        "completed_at",
    )
    list_filter = ("recipient_mode", "notification_type", "status")
    search_fields = ("title", "message", "created_by__email", "created_by__username")
    readonly_fields = (
        "id",
        "created_by",
        "status",
        "queued_at",
        "started_at",
        "completed_at",
        "targeted_recipient_count",
        "delivered_recipient_count",
        "failed_recipient_count",
        "last_error",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("selected_users",)
    actions = ("queue_selected_dispatches",)
    fieldsets = (
        (
            "Dispatch details",
            {
                "fields": (
                    "title",
                    "notification_type",
                    "message",
                    "recipient_mode",
                    "selected_users",
                    "action_url",
                    "metadata",
                    "related_object_type",
                    "related_object_id",
                    "expires_at",
                    "queue_now",
                )
            },
        ),
        (
            "Delivery status",
            {
                "fields": (
                    "status",
                    "queued_at",
                    "started_at",
                    "completed_at",
                    "targeted_recipient_count",
                    "delivered_recipient_count",
                    "failed_recipient_count",
                    "last_error",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "id",
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def get_changeform_initial_data(self, request: HttpRequest) -> dict[str, str | list[str]]:
        initial: dict[str, str | list[str]] = super().get_changeform_initial_data(request)
        selected_users = request.GET.getlist("selected_users")
        if selected_users:
            initial["recipient_mode"] = NotificationDispatch.RecipientMode.SELECTED_USERS
            initial["selected_users"] = selected_users
        return initial

    def save_model(
        self,
        request: HttpRequest,
        obj: NotificationDispatch,
        form: NotificationDispatchAdminForm,
        change: bool,
    ) -> None:
        if not change and obj.created_by_id is None and request.user.is_authenticated:
            obj.created_by = cast(Any, request.user)
        super().save_model(request, obj, form, change)

    def save_related(
        self,
        request: HttpRequest,
        form: NotificationDispatchAdminForm,
        formsets: list[Any],
        change: bool,
    ) -> None:
        super().save_related(request, form, formsets, change)
        if not form.cleaned_data.get("queue_now"):
            return
        try:
            queue_notification_dispatch(form.instance)
        except ValidationError as exc:
            self.message_user(request, "; ".join(exc.messages), level=messages.ERROR)
            return
        self.message_user(
            request,
            "Queued notification dispatch for delivery.",
            level=messages.INFO,
        )

    @admin.action(description="Queue selected notification dispatches")
    def queue_selected_dispatches(
        self,
        request: HttpRequest,
        queryset: Any,
    ) -> None:
        queued = 0
        for dispatch in queryset:
            try:
                queue_notification_dispatch(dispatch)
            except ValidationError as exc:
                self.message_user(
                    request,
                    f"{dispatch.title}: {'; '.join(exc.messages)}",
                    level=messages.ERROR,
                )
                continue
            queued += 1
        if queued:
            self.message_user(
                request,
                f"Queued {queued} notification dispatch(es) for delivery.",
                level=messages.INFO,
            )


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "notification_type",
        "user",
        "is_read",
        "source_dispatch",
        "created_at",
        "expires_at",
    )
    list_filter = ("notification_type", "is_read")
    search_fields = ("title", "message", "user__email", "user__username")
    list_select_related = ("user", "source_dispatch")
    readonly_fields = (
        "id",
        "user",
        "source_dispatch",
        "notification_type",
        "title",
        "message",
        "is_read",
        "read_at",
        "related_object_type",
        "related_object_id",
        "action_url",
        "metadata",
        "expires_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        del request
        return False
