import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from whatsapp_messages.services import EvolutionAPIService
from .forms import ScheduledMessageForm
from .models import ScheduledWhatsAppMessage
from .services import EvolutionAPIService
from .tasks import send_scheduled_whatsapp_message


logger = logging.getLogger(__name__)


# =============================================================
# WhatsApp Connection
# =============================================================

@login_required
def connect_whatsapp_view(request):

    try:
        qr_data = EvolutionAPIService.get_or_create_qr()

    except Exception as exc:
        logger.exception(
            "Unable to get WhatsApp QR code: %s",
            exc,
        )

        qr_data = {
            "connected": False,
            "qrcode": None,
            "base64": None,
            "error": str(exc),
        }

    return render(
        request,
        "whatsapp_messages/connect.html",
        {
            "is_connected": bool(
                qr_data.get("connected", False)
            ),
            "qr_data": qr_data,
        },
    )


# =============================================================
# WhatsApp Status
# =============================================================

@login_required
def whatsapp_status_check_view(request):

    try:
        status = EvolutionAPIService.check_connection()

        return JsonResponse(
            {
                "connected": bool(
                    status.get("connected", False)
                ),
                "state": status.get(
                    "state",
                    "disconnected",
                ),
            }
        )

    except Exception as exc:

        logger.exception(
            "WhatsApp status check failed: %s",
            exc,
        )

        return JsonResponse(
            {
                "connected": False,
                "state": "error",
                "error": str(exc),
            }
        )


@login_required
def check_connection_status_api(request):

    try:
        status = EvolutionAPIService.check_connection()

        return JsonResponse(
            {
                "connected": bool(
                    status.get("connected", False)
                ),
                "state": status.get(
                    "state",
                    "disconnected",
                ),
            }
        )

    except Exception as exc:

        logger.exception(
            "Connection status API failed: %s",
            exc,
        )

        return JsonResponse(
            {
                "connected": False,
                "state": "error",
                "error": str(exc),
            }
        )


# =============================================================
# Disconnect WhatsApp
# =============================================================

@login_required
def disconnect_whatsapp_view(request):

    if request.method != "POST":

        messages.warning(
            request,
            "Please use the disconnect button.",
        )

        return redirect(
            "whatsapp_messages:connect_whatsapp"
        )

    try:

        service = EvolutionAPIService()

        endpoint = (
            f"{service.base_url}/instance/logout/"
            f"{service.instance}"
        )

        import requests

        response = requests.delete(
            endpoint,
            headers=service.headers,
            timeout=10,
        )

        if response.status_code in [200, 201]:

            messages.success(
                request,
                "WhatsApp disconnected successfully.",
            )

        else:

            messages.warning(
                request,
                (
                    "Evolution API returned HTTP "
                    f"{response.status_code}."
                ),
            )

    except Exception as exc:

        logger.exception(
            "WhatsApp disconnect failed",
        )

        messages.error(
            request,
            f"Could not disconnect WhatsApp: {exc}",
        )

    return redirect(
        "whatsapp_messages:connect_whatsapp"
    )


# =============================================================
# Schedule WhatsApp Message
# =============================================================

@login_required
def schedule_message_view(request):

    if request.method == "POST":

        form = ScheduledMessageForm(request.POST)

        # -----------------------------------------------------
        # FORM INVALID
        # -----------------------------------------------------

        if not form.is_valid():

            logger.warning(
                "Scheduled message form invalid. "
                "User=%s Errors=%s",
                request.user.id,
                form.errors.as_json(),
            )

            messages.error(
                request,
                (
                    "Message was not saved. "
                    "Please correct the errors shown in the form."
                ),
            )

        # -----------------------------------------------------
        # FORM VALID
        # -----------------------------------------------------

        else:

            try:

                # ---------------------------------------------
                # Create object without saving
                # ---------------------------------------------

                message_obj = form.save(commit=False)

                # ---------------------------------------------
                # Attach logged-in user
                # ---------------------------------------------

                message_obj.user = request.user

                # ---------------------------------------------
                # Set status
                # ---------------------------------------------

                message_obj.status = "Scheduled"

                # ---------------------------------------------
                # Make sure schedule exists
                # ---------------------------------------------

                if message_obj.scheduled_at is None:

                    raise ValueError(
                        "Scheduled date and time is required."
                    )

                # ---------------------------------------------
                # Save to database
                # ---------------------------------------------

                message_obj.save()

                # ---------------------------------------------
                # Refresh from database
                # ---------------------------------------------

                message_obj.refresh_from_db()

                logger.info(
                    "WHATSAPP MESSAGE SCHEDULED: "
                    "id=%s user=%s phone=%s scheduled_at=%s "
                    "timezone=%s",
                    message_obj.id,
                    request.user.id,
                    message_obj.phone_number,
                    message_obj.scheduled_at,
                    timezone.get_current_timezone_name(),
                )

                # -------------------------------------------------
                # IMPORTANT:
                #
                # Do NOT call:
                #
                # send_scheduled_whatsapp_message.apply_async(
                #     eta=...
                # )
                #
                # Celery Beat will find this message automatically.
                # -------------------------------------------------

                messages.success(
                    request,
                    (
                        "WhatsApp message scheduled successfully "
                        "for "
                        f"{timezone.localtime(message_obj.scheduled_at).strftime('%b %d, %Y at %I:%M %p')}."
                    ),
                )

                return redirect(
                    "whatsapp_messages:scheduled_messages"
                )

            except Exception as exc:

                logger.exception(
                    "ERROR WHILE SAVING SCHEDULED WHATSAPP MESSAGE"
                )

                # ---------------------------------------------
                # If database object was created but something
                # failed afterwards, mark it as failed.
                # ---------------------------------------------

                if (
                    "message_obj" in locals()
                    and message_obj.pk
                ):

                    message_obj.status = "Failed"
                    message_obj.error_log = str(exc)

                    message_obj.save(
                        update_fields=[
                            "status",
                            "error_log",
                            "updated_at",
                        ]
                    )

                    messages.error(
                        request,
                        (
                            "Message was saved, but scheduling "
                            "could not be completed: "
                            f"{exc}"
                        ),
                    )

                else:

                    messages.error(
                        request,
                        (
                            "Message could not be saved: "
                            f"{exc}"
                        ),
                    )

    else:

        form = ScheduledMessageForm()

    # =========================================================
    # WhatsApp connection
    # =========================================================

    try:

        connection_status = (
            EvolutionAPIService.check_connection()
        )

        is_connected = bool(
            connection_status.get(
                "connected",
                False,
            )
        )

    except Exception as exc:

        logger.exception(
            "Unable to check WhatsApp connection",
        )

        is_connected = False

    # ---------------------------------------------------------
    # Show warning but allow scheduling
    # ---------------------------------------------------------

    if not is_connected:

        messages.warning(
            request,
            (
                "WhatsApp is currently disconnected. "
                "The message can still be scheduled, but it "
                "will not be sent until WhatsApp is connected."
            ),
        )

    return render(
        request,
        "whatsapp_messages/schedule_form.html",
        {
            "form": form,
            "title": "Schedule WhatsApp Message",
            "is_connected": is_connected,
        },
    )

    


# =============================================================
# Backward-compatible alias
# =============================================================

@login_required
def schedule_whatsapp_view(request):

    return schedule_message_view(request)


# =============================================================
# Scheduled Messages
# =============================================================

@login_required
def scheduled_messages(request):

    queryset = (
        ScheduledWhatsAppMessage.objects
        .filter(
            user=request.user
        )
        .order_by(
            "-scheduled_at"
        )
    )

    return render(
        request,
        "whatsapp_messages/scheduled_messages.html",
        {
            "scheduled_messages": queryset,
        },
    )


# =============================================================
# Send Message Now / Retry
# =============================================================

@login_required
def send_message_now_view(request, pk):

    if request.method != "POST":

        messages.warning(
            request,
            "Please use the Send Now button.",
        )

        return redirect(
            "whatsapp_messages:scheduled_messages"
        )

    # =========================================================
    # Get message belonging to logged-in user
    # =========================================================

    message_obj = get_object_or_404(
        ScheduledWhatsAppMessage,
        pk=pk,
        user=request.user,
    )

    # =========================================================
    # Already sent
    # =========================================================

    if message_obj.status == "Sent":

        messages.info(
            request,
            "This message has already been sent.",
        )

        return redirect(
            "whatsapp_messages:scheduled_messages"
        )

    # =========================================================
    # Mark as processing
    # =========================================================

    message_obj.status = "Processing"
    message_obj.error_log = None

    message_obj.save(
        update_fields=[
            "status",
            "error_log",
            "updated_at",
        ]
    )

    # =========================================================
    # Send through Evolution API
    # =========================================================

    try:

        service = EvolutionAPIService()

        # Check WhatsApp connection first
        connection_status = service.check_connection()

        if not connection_status.get(
            "connected",
            False,
        ):

            result = {
                "success": False,
                "error": (
                    "WhatsApp is not connected "
                    "to Evolution API."
                ),
            }

        else:

            result = service.send_text_message(
                number=message_obj.phone_number,
                text=message_obj.message,
            )

    except Exception as exc:

        logger.exception(
            "Unexpected error sending message %s",
            message_obj.id,
        )

        result = {
            "success": False,
            "error": str(exc),
        }

    # =========================================================
    # SUCCESS
    # =========================================================

    if result.get("success"):

        data = result.get(
            "data",
            {},
        )

        message_id = None

        # -----------------------------------------------------
        # Evolution API response
        # -----------------------------------------------------

        if isinstance(data, dict):

            key = data.get(
                "key",
                {},
            )

            if isinstance(key, dict):

                message_id = key.get(
                    "id"
                )

            if not message_id:

                message_id = data.get(
                    "id"
                )

            if not message_id:

                message_id = data.get(
                    "messageId"
                )

        # -----------------------------------------------------
        # Update database
        # -----------------------------------------------------

        message_obj.status = "Sent"
        message_obj.sent_at = timezone.now()
        message_obj.error_log = None

        if message_id:

            message_obj.evolution_message_id = str(
                message_id
            )

            message_obj.save(
                update_fields=[
                    "status",
                    "sent_at",
                    "error_log",
                    "evolution_message_id",
                    "updated_at",
                ]
            )

        else:

            message_obj.save(
                update_fields=[
                    "status",
                    "sent_at",
                    "error_log",
                    "updated_at",
                ]
            )

        logger.info(
            "WhatsApp message %s sent successfully to %s. "
            "Evolution message ID=%s",
            message_obj.id,
            message_obj.phone_number,
            message_id,
        )

        messages.success(
            request,
            (
                "WhatsApp message sent successfully "
                f"to {message_obj.phone_number}."
            ),
        )

    # =========================================================
    # FAILURE
    # =========================================================

    else:

        error = result.get(
            "error",
            "Unknown Evolution API error.",
        )

        message_obj.status = "Failed"
        message_obj.error_log = str(
            error
        )

        message_obj.save(
            update_fields=[
                "status",
                "error_log",
                "updated_at",
            ]
        )

        logger.error(
            "WhatsApp message %s failed: %s",
            message_obj.id,
            error,
        )

        messages.error(
            request,
            (
                "Failed to send WhatsApp message: "
                f"{error}"
            ),
        )

    return redirect(
        "whatsapp_messages:scheduled_messages"
    )


