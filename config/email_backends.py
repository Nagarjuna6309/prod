
import logging
import os

import requests
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    api_url = "https://api.resend.com/emails"

    def send_messages(self, email_messages):
        api_key = os.environ.get("RESEND_API_KEY")
        default_from = os.environ.get("DEFAULT_FROM_EMAIL")

        if not api_key or not default_from:
            raise ValueError(
                "RESEND_API_KEY and DEFAULT_FROM_EMAIL must be configured."
            )

        sent_count = 0

        for message in email_messages:
            payload = {
                "from": message.from_email or default_from,
                "to": list(message.to),
                "subject": message.subject,
                "text": message.body or "",
            }

            for content, mimetype in getattr(
                message, "alternatives", []
            ):
                if mimetype == "text/html":
                    payload["html"] = content
                    break

            try:
                response = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=(3, 8),
                )
                response.raise_for_status()
                sent_count += 1

            except requests.RequestException:
                logger.exception("Resend email API request failed.")
                if not self.fail_silently:
                    raise

        return sent_count
