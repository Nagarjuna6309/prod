from django.contrib import admin

from .models import ScheduledWhatsAppMessage


@admin.register(ScheduledWhatsAppMessage)
class ScheduledWhatsAppMessageAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "phone_number",
        "message_preview",
        "scheduled_at",
        "status",
        "sent_at",
        "created_at",
    )

    list_filter = (
        "status",
        "scheduled_at",
        "created_at",
    )

    search_fields = (
        "phone_number",
        "message",
        "error_log",
    )

    date_hierarchy = "scheduled_at"

    ordering = (
        "-scheduled_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "sent_at",
        "twilio_sid",
    )

    list_per_page = 25


    @admin.display(
        description="Message",
    )
    def message_preview(
        self,
        obj,
    ):
        if not obj.message:
            return ""

        if len(obj.message) > 60:
            return f"{obj.message[:60]}..."

        return obj.message
