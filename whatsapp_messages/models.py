from django.conf import settings
from django.db import models
from django.utils import timezone


class ScheduledWhatsAppMessage(models.Model):

    STATUS_CHOICES = [
        ("Scheduled", "Scheduled"),
        ("Processing", "Processing"),
        ("Sent", "Sent"),
        ("Failed", "Failed"),
        ("Cancelled", "Cancelled"),
    ]

    # =========================================================
    # User
    # =========================================================

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheduled_whatsapp_messages",
    )

    # =========================================================
    # WhatsApp recipient
    # =========================================================

    phone_number = models.CharField(
        max_length=30,
        default="",
    )

    # =========================================================
    # Message
    # =========================================================

    message = models.TextField(
        default="",
    )

    # =========================================================
    # Scheduled date/time
    # =========================================================

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the WhatsApp message should be sent.",
    )

    # =========================================================
    # Status
    # =========================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Scheduled",
    )

    # =========================================================
    # Sending information
    # =========================================================

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =========================================================
    # Evolution API message ID
    # =========================================================

    evolution_message_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # =========================================================
    # Old field kept for compatibility
    # =========================================================

    twilio_sid = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # =========================================================
    # Error information
    # =========================================================

    error_log = models.TextField(
        null=True,
        blank=True,
    )

    # =========================================================
    # Timestamps
    # =========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =========================================================
    # Meta
    # =========================================================

    class Meta:
        ordering = [
            "-scheduled_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "status",
                    "scheduled_at",
                ]
            ),
            models.Index(
                fields=[
                    "user",
                    "-scheduled_at",
                ]
            ),
        ]

        verbose_name = "Scheduled WhatsApp Message"
        verbose_name_plural = "Scheduled WhatsApp Messages"

    # =========================================================
    # String representation
    # =========================================================

    def __str__(self):

        phone = self.phone_number or "No phone number"

        if self.scheduled_at:
            scheduled = self.scheduled_at.strftime(
                "%Y-%m-%d %H:%M"
            )
        else:
            scheduled = "Not scheduled"

        return (
            f"{phone} - "
            f"{scheduled} - "
            f"{self.status}"
        )

    # =========================================================
    # Convenience properties
    # =========================================================

    @property
    def is_sent(self):
        return self.status == "Sent"

    @property
    def is_failed(self):
        return self.status == "Failed"

    @property
    def is_scheduled(self):
        return self.status == "Scheduled"

    @property
    def is_processing(self):
        return self.status == "Processing"

    @property
    def is_cancelled(self):
        return self.status == "Cancelled"

    @property
    def is_due(self):
        return (
            self.status == "Scheduled"
            and self.scheduled_at is not None
            and self.scheduled_at <= timezone.now()
        )
