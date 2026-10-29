
import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from whatsapp_messages.models import ScheduledWhatsAppMessage
from whatsapp_messages.tasks import send_scheduled_whatsapp_message

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process and send due scheduled WhatsApp messages."

    def handle(self, *args, **options):
        now = timezone.now()
        processed = 0

        self.stdout.write(f"Checking scheduled messages at {now}...")

        while True:
            # Claim one due message atomically to reduce duplicate processing.
            with transaction.atomic():
                message = (
                    ScheduledWhatsAppMessage.objects
                    .select_for_update(skip_locked=True)
                    .filter(
                        status="Scheduled",
                        scheduled_at__isnull=False,
                        scheduled_at__lte=now,
                    )
                    .order_by("scheduled_at")
                    .first()
                )

                if message is None:
                    break

                updated = (
                    ScheduledWhatsAppMessage.objects
                    .filter(id=message.id, status="Scheduled")
                    .update(
                        status="Processing",
                        error_log=None,
                        updated_at=timezone.now(),
                    )
                )

                if not updated:
                    continue

                message_id = message.id

            # Run the existing Celery task locally; no broker is needed
            # for this synchronous invocation.
            try:
                result = send_scheduled_whatsapp_message.apply(
                    args=(message_id,),
                    throw=False,
                )

                if result.failed():
                    self.stderr.write(
                        self.style.ERROR(
                            f"Message {message_id} encountered an error."
                        )
                    )
                else:
                    self.stdout.write(
                        f"Processed message {message_id}."
                    )

                processed += 1

            except Exception:
                logger.exception(
                    "Failed processing scheduled message %s",
                    message_id,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. Processed {processed} message(s)."
            )
        )
