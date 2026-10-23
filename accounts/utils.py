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


from django.core.mail import send_mail
from django.conf import settings

def send_otp_via_email(user_email, otp_code):
    subject = "Noti5me - Password Reset Verification Code"
    message = (
        f"Hello,\n\n"
        f"You requested a password reset for your Noti5me account.\n\n"
        f"Your 6-digit OTP code is: {otp_code}\n\n"
        f"This code will expire in 10 minutes. If you did not make this request, please ignore this email.\n\n"
        f"— Team Noti5me"
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@noti5me.com')

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user_email],
            fail_silently=False,
        )
        return True, "Email sent successfully."
    except Exception as exc:
        print(f"[EMAIL ERROR] Failed to send to {user_email}: {exc}")
        print(f"[CONSOLE FALLBACK OTP] Code is: {otp_code}")
        return False, str(exc)