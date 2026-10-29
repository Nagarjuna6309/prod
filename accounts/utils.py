import re
from django.conf import settings
#from twilio.rest import Client


'''def send_otp_via_sms(mobile, otp_code):
  sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
  token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
  from_sms = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

  if not (sid and token and from_sms):
    print(f'[DEV BACKUP] OTP for {mobile} is: {otp_code}')
    return False, 'Twilio SMS credentials or phone number missing.'

  # Format mobile into standard E.164 format (+91 for 10-digit Indian numbers)
  digits = re.sub(r'\D', '', str(mobile))
  if len(digits) == 10:
    target = f'+91{digits}'
  elif digits.startswith('91') and len(digits) == 12:
    target = f'+{digits}'
  else:
    target = f'+{digits}'

  body = (
      f'Noti5me Security: Your password reset OTP is {otp_code}. Valid for 10'
      ' minutes. Do not share this code.'
  )

  client = Client(sid, token)

  try:
    # Standard SMS dispatch (NO whatsapp: prefix anywhere)
    msg = client.messages.create(
        from_=from_sms,  # Twilio SMS Phone Number (+1...)
        to=target,  # Recipient mobile (+91...)
        body=body,
    )
    return True, msg.sid
  except Exception as exc:
    print(f'[SMS Delivery Error] {exc}')
    print(f'[DEV BACKUP] OTP for {target} is: {otp_code}')
    return False, str(exc)'''





import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_otp_via_email(user_email, otp_code):
    """
    Send a password-reset OTP to the user's email.
    Returns (success, message).
    """

    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.error("Email SMTP credentials are not configured.")
        return False, "Email SMTP credentials are not configured."

    if not user_email:
        return False, "Recipient email address is missing."

    subject = "Noti5me - Password Reset Verification Code"

    message = (
        "Hello,\n\n"
        "You requested a password reset for your Noti5me account.\n\n"
        f"Your 6-digit OTP code is: {otp_code}\n\n"
        "This code expires in 10 minutes. "
        "If you did not request this, please ignore this email.\n\n"
        "-- Team Noti5me"
    )

    try:
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )

        if sent_count == 1:
            return True, "Email sent successfully."

        logger.warning("Email backend did not confirm sending the OTP email.")
        return False, "The email backend did not confirm sending."

    except Exception:
        # Log technical details, but never log the OTP or email message.
        logger.exception("Could not send password-reset OTP email.")
        return False, "Email sending failed. Please try again later."
