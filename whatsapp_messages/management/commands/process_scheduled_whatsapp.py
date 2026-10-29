
import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from whatsapp_messages.models import ScheduledWhatsAppMessage
from whatsapp_messages.tasks import send_scheduled_whatsapp_message

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process due scheduled WhatsApp messages without a Celery worker."

    def handle(self, *args, **options):
        now = timezone.now()
        processed = 0

        self.stdout.write(f"Checking scheduled messages at {now}...")

        while True:
            with transaction.atomic():
                queryset = ScheduledWhatsAppMessage.objects.filter(
                    status="Scheduled",
                    scheduled_at__isnull=False,
                    scheduled_at__lte=now,
                ).order_by("scheduled_at")

                # Claim one message at a time to prevent duplicate processing.
                if (
                    transaction.get_connection().vendor == "postgresql"
                ):
                    queryset = queryset.select_for_update(skip_locked=True)

                message = queryset.first()

                if message is None:
                    break

                updated = (
                    ScheduledWhatsAppMessage.objects
                    .filter(pk=message.pk, status="Scheduled")
                    .update(
                        status="Processing",
                        error_log=None,
                    )
                )

                if not updated:
                    continue

                message_id = message.pk

            self.stdout.write(f"Processing message ID {message_id}...")

            try:
                result = send_scheduled_whatsapp_message.apply(
                    args=(message_id,),
                    throw=False,
                )

                if result.failed():
                    self.stderr.write(
                        self.style.ERROR(
                            f"Message {message_id} failed. Check error_log "
                            "and Render logs."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Message {message_id} processed."
                        )
                    )

                processed += 1

            except Exception:
                logger.exception(
                    "Error processing scheduled message %s",
                    message_id,
                )
                self.stderr.write(
                    self.style.ERROR(
                        f"Error processing message {message_id}."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. Processed {processed} message(s)."
            )
        )
