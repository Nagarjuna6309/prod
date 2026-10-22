from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
import requests
from whatsapp_messages.models import ScheduledWhatsAppMessage

class Command(BaseCommand):
    help = 'Sends pending scheduled WhatsApp messages'

    def handle(self, *args, **options):
        current_date = timezone.now()
        self.stdout.write(f"Checking messages for: {current_date.strftime('%Y-%m-%d %H:%M:%S')}")

        # Fetch messages that are pending and whose scheduled time has arrived/passed
        pending_messages = ScheduledWhatsAppMessage.objects.filter(
            status="pending",
            scheduled_date__lte=current_date,
        )

        count = pending_messages.count()
        self.stdout.write(f"Found {count} pending message(s) to send.")

        for msg in pending_messages:
            try:
                # Example Evolution API integration (adjust if your endpoint differs)
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
                    self.stdout.write(self.style.SUCCESS(f"Successfully sent message ID {msg.id} to {msg.recipient_mobile}"))
                else:
                    msg.status = "failed"
                    msg.error_log = response.text
                    msg.save()
                    self.stdout.write(self.style.ERROR(f"Failed to send message ID {msg.id}: {response.text}"))

            except Exception as e:
                msg.status = "failed"
                msg.error_log = str(e)
                msg.save()
                self.stdout.write(self.style.ERROR(f"Exception occurred for message ID {msg.id}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS('Finished processing scheduled WhatsApp messages.'))