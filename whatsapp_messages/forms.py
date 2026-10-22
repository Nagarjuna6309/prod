from django import forms
from django.utils import timezone

from .models import ScheduledWhatsAppMessage


class ScheduledMessageForm(forms.ModelForm):

    class Meta:
        model = ScheduledWhatsAppMessage

        fields = [
            "phone_number",
            "message",
            "scheduled_at",
        ]

        widgets = {
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter WhatsApp number",
                    "autocomplete": "tel",
                }
            ),

            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your WhatsApp message...",
                    "rows": 6,
                }
            ),

            "scheduled_at": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                }
            ),
        }

        labels = {
            "phone_number": "WhatsApp Number",
            "message": "Message",
            "scheduled_at": "Schedule Date & Time",
        }

    # =========================================================
    # PHONE NUMBER
    # =========================================================

    def clean_phone_number(self):

        phone_number = self.cleaned_data.get(
            "phone_number"
        )

        if not phone_number:

            raise forms.ValidationError(
                "WhatsApp phone number is required."
            )

        phone_number = phone_number.strip()

        # Remove common formatting characters
        phone_number = (
            phone_number
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )

        # Convert +91XXXXXXXXXX
        # to 91XXXXXXXXXX
        if phone_number.startswith("+"):

            phone_number = phone_number[1:]

        # Convert 10-digit Indian number
        # to 91XXXXXXXXXX
        if len(phone_number) == 10:

            phone_number = (
                "91" + phone_number
            )

        # Must contain digits only
        if not phone_number.isdigit():

            raise forms.ValidationError(
                "Phone number must contain only digits."
            )

        # Indian international number should be
        # 12 digits: 91 + 10 digits
        if (
            phone_number.startswith("91")
            and len(phone_number) != 12
        ):

            raise forms.ValidationError(
                "Please enter a valid Indian WhatsApp number."
            )

        # General validation for other countries
        if len(phone_number) < 10:

            raise forms.ValidationError(
                "Please enter a valid WhatsApp phone number."
            )

        return phone_number

    # =========================================================
    # MESSAGE
    # =========================================================

    def clean_message(self):

        message = self.cleaned_data.get(
            "message"
        )

        if not message or not message.strip():

            raise forms.ValidationError(
                "Message cannot be empty."
            )

        return message.strip()

    # =========================================================
    # SCHEDULED DATE/TIME
    # =========================================================

    def clean_scheduled_at(self):

        scheduled_at = self.cleaned_data.get(
            "scheduled_at"
        )

        if scheduled_at is None:

            raise forms.ValidationError(
                "Please select a date and time."
            )

        if scheduled_at <= timezone.now():

            raise forms.ValidationError(
                "Please select a future date and time."
            )

        return scheduled_at
