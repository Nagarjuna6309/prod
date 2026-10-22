import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import ScheduledWhatsAppMessage
from .services import EvolutionAPIService


logger = logging.getLogger(__name__)


# =========================================================
# PROCESS SCHEDULED MESSAGES
# =========================================================

@shared_task
def process_scheduled_whatsapp_messages():

    now = timezone.now()

    scheduled_messages = (
        ScheduledWhatsAppMessage.objects
        .filter(
            status="Scheduled",
            scheduled_at__isnull=False,
            scheduled_at__lte=now,
        )
        .order_by("scheduled_at")
    )

    count = 0

    for message in scheduled_messages:

        try:

            # Change status before creating the sending task.
            # This prevents Beat from scheduling the same message
            # repeatedly on every 10-second/60-second cycle.

            updated = (
                ScheduledWhatsAppMessage.objects
                .filter(
                    id=message.id,
                    status="Scheduled",
                )
                .update(
                    status="Processing",
                    error_log=None,
                    updated_at=timezone.now(),
                )
            )

            if not updated:
                continue

            send_scheduled_whatsapp_message.delay(
                message.id
            )

            count += 1

            logger.info(
                "Scheduled WhatsApp message %s "
                "queued for sending.",
                message.id,
            )

        except Exception as exc:

            logger.exception(
                "Failed to queue scheduled WhatsApp "
                "message %s",
                message.id,
            )

            ScheduledWhatsAppMessage.objects.filter(
                id=message.id
            ).update(
                status="Failed",
                error_log=str(exc),
                updated_at=timezone.now(),
            )

    logger.info(
        "Scheduled WhatsApp processor completed. "
        "Queued=%s",
        count,
    )

    return {
        "queued": count,
    }


# =========================================================
# SEND ONE SCHEDULED MESSAGE
# =========================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_scheduled_whatsapp_message(
    self,
    message_id,
):
    """
    Send one scheduled WhatsApp message.
    """

    # ---------------------------------------------------------
    # Get message
    # ---------------------------------------------------------

    try:

        scheduled_message = (
            ScheduledWhatsAppMessage.objects.get(
                id=message_id
            )
        )

    except ScheduledWhatsAppMessage.DoesNotExist:

        logger.error(
            "Scheduled WhatsApp message %s does not exist.",
            message_id,
        )

        return {
            "success": False,
            "error": "Scheduled message does not exist.",
        }

    # ---------------------------------------------------------
    # Prevent duplicate sending
    # ---------------------------------------------------------

    if scheduled_message.status == "Sent":

        logger.info(
            "Message %s has already been sent.",
            message_id,
        )

        return {
            "success": True,
            "message": "Message was already sent.",
        }

    # ---------------------------------------------------------
    # Only Processing messages should reach this point
    # ---------------------------------------------------------

    if scheduled_message.status != "Processing":

        logger.warning(
            "Message %s has unexpected status: %s",
            message_id,
            scheduled_message.status,
        )

        scheduled_message.status = "Processing"
        scheduled_message.error_log = None

        scheduled_message.save(
            update_fields=[
                "status",
                "error_log",
                "updated_at",
            ]
        )

    # ---------------------------------------------------------
    # Send message
    # ---------------------------------------------------------

    try:

        service = EvolutionAPIService()

        # -----------------------------------------------------
        # Check WhatsApp connection
        # -----------------------------------------------------

        connection_status = (
            service.check_connection()
        )

        if not connection_status.get(
            "connected",
            False,
        ):

            error_message = (
                "WhatsApp is not connected "
                "to Evolution API."
            )

            scheduled_message.status = "Failed"
            scheduled_message.error_log = error_message

            scheduled_message.save(
                update_fields=[
                    "status",
                    "error_log",
                    "updated_at",
                ]
            )

            logger.error(
                "Message %s failed: %s",
                message_id,
                error_message,
            )

            return {
                "success": False,
                "error": error_message,
            }

        # -----------------------------------------------------
        # Send through Evolution API
        # -----------------------------------------------------

        result = service.send_text_message(
            number=scheduled_message.phone_number,
            text=scheduled_message.message,
        )

        # -----------------------------------------------------
        # SUCCESS
        # -----------------------------------------------------

        if result.get("success"):

            data = result.get(
                "data",
                {},
            )

            evolution_message_id = None

            if isinstance(data, dict):

                key = data.get(
                    "key",
                    {},
                )

                if isinstance(key, dict):

                    evolution_message_id = key.get(
                        "id"
                    )

                if not evolution_message_id:

                    evolution_message_id = data.get(
                        "id"
                    )

                if not evolution_message_id:

                    evolution_message_id = data.get(
                        "messageId"
                    )

            scheduled_message.status = "Sent"
            scheduled_message.sent_at = timezone.now()
            scheduled_message.error_log = None

            if evolution_message_id:

                scheduled_message.evolution_message_id = str(
                    evolution_message_id
                )

                scheduled_message.save(
                    update_fields=[
                        "status",
                        "sent_at",
                        "error_log",
                        "evolution_message_id",
                        "updated_at",
                    ]
                )

            else:

                scheduled_message.save(
                    update_fields=[
                        "status",
                        "sent_at",
                        "error_log",
                        "updated_at",
                    ]
                )

            logger.info(
                "Scheduled WhatsApp message %s "
                "sent successfully to %s. "
                "Evolution ID=%s",
                message_id,
                scheduled_message.phone_number,
                evolution_message_id,
            )

            return {
                "success": True,
                "message_id": message_id,
                "evolution_message_id": (
                    evolution_message_id
                ),
            }

        # -----------------------------------------------------
        # EVOLUTION API FAILURE
        # -----------------------------------------------------

        error_message = result.get(
            "error",
            "Evolution API failed to send the message.",
        )

        scheduled_message.status = "Failed"
        scheduled_message.error_log = str(
            error_message
        )

        scheduled_message.save(
            update_fields=[
                "status",
                "error_log",
                "updated_at",
            ]
        )

        logger.error(
            "Scheduled WhatsApp message %s failed: %s",
            message_id,
            error_message,
        )

        return {
            "success": False,
            "error": error_message,
        }

    except Exception as exc:

        logger.exception(
            "Unexpected error while sending "
            "scheduled WhatsApp message %s.",
            message_id,
        )

        scheduled_message.status = "Failed"
        scheduled_message.error_log = str(exc)

        scheduled_message.save(
            update_fields=[
                "status",
                "error_log",
                "updated_at",
            ]
        )

        raise
