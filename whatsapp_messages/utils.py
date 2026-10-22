import requests
from django.conf import settings
from django.utils import timezone
from .models import ScheduledWhatsAppMessage

def send_pending_whatsapp_messages():
    now = timezone.now()
    # Find messages that are pending and whose scheduled time has passed
    pending_messages = ScheduledWhatsAppMessage.objects.filter(
        status="pending",
        scheduled_date__lte=now
    )

    for msg in pending_messages:
        try:
            # Example using Evolution API (adjust endpoint/payload to match your exact provider specs)
            api_url = f"{settings.EVOLUTION_API_URL}/message/sendText/{settings.EVOLUTION_INSTANCE_NAME}"
            headers = {
                "apikey": settings.EVOLUTION_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "number": msg.recipient_mobile,
                "text": msg.message
            }

            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                res_data = response.json()
                msg.status = "sent"
                msg.sent_at = timezone.now()
                msg.twilio_sid = res_data.get("key", {}).get("id") or res_data.get("messageId")
                msg.save()
            else:
                msg.status = "failed"
                msg.error_log = response.text
                msg.save()

        except Exception as e:
            msg.status = "failed"
            msg.error_log = str(e)
            msg.save()