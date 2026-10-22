from django.urls import path

from . import views


app_name = "whatsapp_messages"


urlpatterns = [

    # =========================================================
    # WhatsApp connection
    # =========================================================

    path(
        "connect/",
        views.connect_whatsapp_view,
        name="connect_whatsapp",
    ),

    path(
        "status/",
        views.whatsapp_status_check_view,
        name="whatsapp_status",
    ),

    path(
        "api/status/",
        views.check_connection_status_api,
        name="connection_status_api",
    ),

    path(
        "disconnect/",
        views.disconnect_whatsapp_view,
        name="disconnect_whatsapp",
    ),


    # =========================================================
    # Schedule WhatsApp message
    # =========================================================

    path(
        "schedule/",
        views.schedule_message_view,
        name="schedule_message",
    ),

    # Backward-compatible URL name if another part of the
    # project uses "schedule_whatsapp".
    path(
        "schedule-whatsapp/",
        views.schedule_whatsapp_view,
        name="schedule_whatsapp",
    ),


    # =========================================================
    # Scheduled messages list
    # =========================================================

    path(
        "scheduled/",
        views.scheduled_messages,
        name="scheduled_messages",
    ),


    # =========================================================
    # Send scheduled message immediately
    # =========================================================

    path(
        "scheduled/<int:pk>/send/",
        views.send_message_now_view,
        name="send_message_now",
    ),
]
