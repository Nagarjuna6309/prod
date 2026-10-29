from django.shortcuts import render

# Create your views here.
from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from .models import *
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from django.contrib.auth import authenticate, login,logout,get_user_model
from django.contrib.auth.decorators import login_required
from rest_framework import status
#from accounts.serializers import RegisterSerializer,MobileRegisterSerializer





from .models import PasswordResetOTP
#from .utils import send_otp_via_sms  
from .utils import send_otp_via_email
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from django.contrib import messages
from django.db import IntegrityError

import secrets
import time
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import render, redirect
from django.db import IntegrityError

'''
@login_required
def dashboard_page(request):
    # Retrieve only pending reminders (is_completed is False)
    pending_reminders = Reminder.objects.filter(
        user=request.user, 
        is_completed=False
    ).order_by('reminder_date', 'reminder_time')

    context = {
        'pending_reminders': pending_reminders,
        'pending_count': pending_reminders.count(),
    }
    return render(request, 'accounts/dashboard.html', context)"""





#API 
"""
class RegisterAPIView(generics.CreateAPIView):
    
    serializer_class = RegisterSerializer

    permission_classes = [AllowAny]

    authentication_classes = []

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            {
                "success": True,
                "message": "User registered successfully"
            },
            status=status.HTTP_201_CREATED
        )
        
    
    
class LoginAPIView(APIView):
    
    permission_classes = [AllowAny]

    authentication_classes = []

    def post(self, request):

        mobile = request.data.get("mobile")

        password = request.data.get("password")

        if not mobile or not password:

            return Response(
                {
                    "success": False,
                    "message": "Mobile and password are required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(
            request,
            mobile=mobile,
            password=password
        )

        if user is None:

            return Response(
                {
                    "success": False,
                    "message": "Invalid mobile number or password"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "user_fullname": user.user_fullname,
                    "mobile": user.mobile,
                }
            },
            status=status.HTTP_200_OK
        )
        
        
        
        
        
#web 
'''
def landing_page(request):
    if request.user.is_authenticated:
        return redirect("home")

    return render(request, "accounts/landing.html")



    
def login_page(request):
    
    if request.method == "POST":

        mobile = request.POST.get("mobile")
        password = request.POST.get("password")

        user = authenticate(
            request,
            mobile=mobile,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("home")

        return render(
            request,
            "accounts/login.html",
            {
                "error": "Invalid mobile number or password"
            }
        )

    return render(request, "accounts/login.html") 
        
        



def logout_page(request):
    logout(request)
    return redirect("login")



   
   


User = get_user_model()

REGISTRATION_OTP_KEY = "pending_registration"
OTP_EXPIRY_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_WAIT_SECONDS = 30


def _send_registration_otp(request, pending):
    """Send an email OTP before creating the user account."""
    code = f"{secrets.randbelow(900000) + 100000}"

    try:
        send_mail(
            subject="Your Noti5me verification code",
            message=(
                f"Hello {pending['user_fullname']},\n\n"
                f"Your Noti5me email verification code is: {code}\n\n"
                "This code expires in 5 minutes. "
                "Do not share it with anyone."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[pending["email"]],
            fail_silently=False,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Registration OTP email delivery failed"
        )
        return False

    # Save registration data in the session ONLY after email succeeds.
    pending["otp_hash"] = make_password(code)
    pending["otp_expires_at"] = int(time.time()) + OTP_EXPIRY_SECONDS
    pending["otp_attempts"] = 0
    pending["last_sent_at"] = int(time.time())

    request.session[REGISTRATION_OTP_KEY] = pending
    request.session.modified = True
    return True



def register_page(request):
    if request.method == "POST":
        user_fullname = request.POST.get("user_fullname", "").strip()
        mobile = request.POST.get("mobile", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        context = {
            "user_fullname": user_fullname,
            "mobile": mobile,
            "email": email,
        }

        # Validate name
        if not user_fullname or len(user_fullname) > 25:
            messages.error(
                request,
                "Enter a name of 1 to 25 characters."
            )
            return render(
                request,
                "accounts/register.html",
                context
            )

        # Validate mobile number
        if not mobile.isdigit() or len(mobile) != 10:
            messages.error(
                request,
                "Enter a valid 10-digit mobile number."
            )
            return render(
                request,
                "accounts/register.html",
                context
            )

        # Validate email
        try:
            validate_email(email)
        except ValidationError:
            messages.error(
                request,
                "Enter a valid email address."
            )
            return render(
                request,
                "accounts/register.html",
                context
            )

        # Validate email length
        if len(email) > 30:
            messages.error(
                request,
                "Email address must be 30 characters or fewer."
            )
            return render(
                request,
                "accounts/register.html",
                context
            )

        # Validate password
        if len(password) < 6:
            messages.error(
                request,
                "Password must contain at least 6 characters."
            )
            return render(
                request,
                "accounts/register.html",
                context
            )

        # Check duplicate mobile
        if User.objects.filter(mobile=mobile).exists():
            messages.error(
                request,
                "This mobile number is already registered."
            )
            return render(
                request,
                "accounts/register.html",
                context
            )

        # Check duplicate email
        if User.objects.filter(mail__iexact=email).exists():
            messages.error(
                request,
                "This email is already registered."
            )
            return render(
                request,
                "accounts/register.html",
                context
            )

        # Store a password hash, not the plain-text password.
        pending = {
            "user_fullname": user_fullname,
            "mobile": mobile,
            "email": email,
            "password_hash": make_password(password),
        }

        # Remove any previous registration OTP session.
        request.session.pop(REGISTRATION_OTP_KEY, None)

        # Send registration OTP.
        if not _send_registration_otp(request, pending):
            messages.error(
                request,
                "Unable to send the verification email. "
                "Check your Gmail SMTP settings and try again.",
            )
            return render(
                request,
                "accounts/register.html",
                context
            )

        messages.success(
            request,
            "A verification code has been sent to your email."
        )

        return redirect("otp")

    return render(request, "accounts/register.html")

"""
def otp(request):
    pending = request.session.get(REGISTRATION_OTP_KEY)

    if not pending:
        messages.error(request, "Please register first to receive an OTP.")
        return redirect("register")

    if request.method == "POST":
        action = request.POST.get("action", "verify")

        if action == "resend":
            now = int(time.time())
            last_sent = pending.get("last_sent_at", 0)

            if now - last_sent < OTP_RESEND_WAIT_SECONDS:
                messages.error(request, "Please wait 30 seconds before requesting another OTP.")
                return render(request, "accounts/otp.html", {
                    "email": pending["email"],
                })

            if not _send_registration_otp(request, pending):
                messages.error(request, "Unable to send the OTP. Check your email settings.")
            else:
                messages.success(request, "A new verification code has been sent.")

            return render(request, "accounts/otp.html", {
                "email": pending["email"],
            })

        received_otp = request.POST.get("otp", "").strip()

        if int(time.time()) > pending.get("otp_expires_at", 0):
            messages.error(request, "OTP expired. Request a new code.")
            return render(request, "accounts/otp.html", {
                "email": pending["email"],
            })

        attempts = pending.get("otp_attempts", 0)

        if attempts >= OTP_MAX_ATTEMPTS:
            messages.error(request, "Too many incorrect attempts. Request a new OTP.")
            return render(request, "accounts/otp.html", {
                "email": pending["email"],
            })

        if (
            len(received_otp) != 6
            or not received_otp.isdigit()
            or not check_password(received_otp, pending["otp_hash"])
        ):
            pending["otp_attempts"] = attempts + 1
            request.session[REGISTRATION_OTP_KEY] = pending
            request.session.modified = True

            messages.error(request, "Invalid OTP. Please check your email and try again.")
            return render(request, "accounts/otp.html", {
                "email": pending["email"],
            })

        # Check uniqueness again before creating the account.
        if (
            User.objects.filter(mobile=pending["mobile"]).exists()
            or User.objects.filter(mail__iexact=pending["email"]).exists()
        ):
            request.session.pop(REGISTRATION_OTP_KEY, None)
            messages.error(request, "This mobile number or email is already registered.")
            return redirect("register")

        try:
            user = User(
        mobile=pending["mobile"],
        user_fullname=pending["user_fullname"],
        mail=pending["email"],
        is_active=True,
    )
            user.password = pending["password_hash"]
            user.save()
        except IntegrityError:
            messages.error(
        request,
        "This mobile number or email may already be registered."
    )
            return redirect("register")

        request.session.pop("pending_registration", None)
        messages.success(request,"Email verified and account created. You can now log in."
)
        return redirect("login")

    return render(request, "accounts/otp.html", {
        "email": pending["email"],
    })
"""
        





def otp(request):
    pending = request.session.get(REGISTRATION_OTP_KEY)

    # Registration must be completed before OTP verification.
    if not pending:
        messages.error(
            request,
            "Please register first to receive an OTP."
        )
        return redirect("register")

    if request.method == "POST":
        action = request.POST.get("action", "verify")

        # Resend OTP
        if action == "resend":
            now = int(time.time())
            last_sent = pending.get("last_sent_at", 0)

            if now - last_sent < OTP_RESEND_WAIT_SECONDS:
                messages.error(
                    request,
                    "Please wait 30 seconds before requesting another OTP."
                )
                return render(
                    request,
                    "accounts/otp.html",
                    {"email": pending["email"]}
                )

            if not _send_registration_otp(request, pending):
                messages.error(
                    request,
                    "Unable to send the OTP. Please check your email settings."
                )
            else:
                messages.success(
                    request,
                    "A new verification code has been sent to your email."
                )

            return render(
                request,
                "accounts/otp.html",
                {"email": pending["email"]}
            )

        # Verify OTP
        received_otp = request.POST.get("otp", "").strip()

        # Check expiry
        if int(time.time()) > pending.get("otp_expires_at", 0):
            messages.error(
                request,
                "OTP expired. Please request a new code."
            )
            return render(
                request,
                "accounts/otp.html",
                {"email": pending["email"]}
            )

        # Limit incorrect attempts
        attempts = pending.get("otp_attempts", 0)

        if attempts >= OTP_MAX_ATTEMPTS:
            messages.error(
                request,
                "Too many incorrect attempts. Please request a new OTP."
            )
            return render(
                request,
                "accounts/otp.html",
                {"email": pending["email"]}
            )

        # Validate OTP
        if (
            len(received_otp) != 6
            or not received_otp.isdigit()
            or not check_password(
                received_otp,
                pending.get("otp_hash", "")
            )
        ):
            pending["otp_attempts"] = attempts + 1
            request.session[REGISTRATION_OTP_KEY] = pending
            request.session.modified = True

            messages.error(
                request,
                "Invalid OTP. Please check your email and try again."
            )
            return render(
                request,
                "accounts/otp.html",
                {"email": pending["email"]}
            )

        # OTP is correct. Check for existing accounts again.
        if (
            User.objects.filter(mobile=pending["mobile"]).exists()
            or User.objects.filter(
                mail__iexact=pending["email"]
            ).exists()
        ):
            request.session.pop(REGISTRATION_OTP_KEY, None)
            messages.error(
                request,
                "This mobile number or email is already registered."
            )
            return redirect("register")

        # IMPORTANT: Create the account ONLY after OTP verification.
        try:
            user = User(
                mobile=pending["mobile"],
                user_fullname=pending["user_fullname"],
                mail=pending["email"],
                is_active=True,
            )

            # Password was hashed when registration was submitted.
            user.password = pending["password_hash"]
            user.save()

        except IntegrityError:
            request.session.pop(REGISTRATION_OTP_KEY, None)
            messages.error(
                request,
                "This mobile number or email may already be registered."
            )
            return redirect("register")

        # Clear registration data only after successful creation.
        request.session.pop(REGISTRATION_OTP_KEY, None)
        request.session.modified = True

        messages.success(
            request,
            "Email verified and account created successfully. You can now log in."
        )
        return redirect("login")

    # Display OTP page
    return render(
        request,
        "accounts/otp.html",
        {"email": pending["email"]}
    )
  
    
    
 
 
 
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render
from .models import PasswordResetOTP


User = get_user_model()


# 1. Request OTP using registered mobile

def forgot_password_otp_request(request):
    if request.method == "POST":
        mobile = request.POST.get("mobile", "").strip()
        clean_mobile = mobile[-10:]

        user = User.objects.filter(mobile__icontains=clean_mobile).first()

        if not user:
            messages.error(
                request,
                "No user found with this registered mobile number."
            )
            return render(request, "accounts/otp_request.html")

        # Generate OTP
        otp_obj = PasswordResetOTP.generate_otp(user)

        # Send OTP to registered email
        ok, response = send_otp_via_email(
            user.mail,
            otp_obj.otp
        )

        # Store user ID in session
        request.session["reset_user_id"] = user.id

        if ok:
            messages.success(
                request,
                f"Verification OTP has been sent to your registered email ({user.mail})."
            )
        else:
            messages.warning(
                request,
                f"OTP generated, but email could not be sent. ({response})"
            )

        return redirect("forgot_password_otp_verify")

    return render(request, "accounts/otp_request.html")



# 2. Verify OTP & set new password
def forgot_password_otp_verify(request):
  user_id = request.session.get('reset_user_id')
  if not user_id:
    messages.error(request, 'Session expired. Please request a new OTP.')
    return redirect('forgot_password_otp_request')

  user = User.objects.filter(id=user_id).first()

  if request.method == 'POST':
    entered_otp = request.POST.get('otp', '').strip()
    new_password = request.POST.get('new_password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()

    otp_record = (
        PasswordResetOTP.objects.filter(user=user, otp=entered_otp)
        .order_by('-created_at')
        .first()
    )

    if not otp_record or not otp_record.is_valid():
      messages.error(request, 'Invalid or expired OTP code.')
      return render(
          request, 'accounts/otp_verify.html', {'mobile': user.mobile}
      )

    if len(new_password) < 6:
      messages.error(request, 'Password must be at least 6 characters long.')
      return render(
          request, 'accounts/otp_verify.html', {'mobile': user.mobile}
      )

    if new_password != confirm_password:
      messages.error(request, 'Passwords do not match.')
      return render(
          request, 'accounts/otp_verify.html', {'mobile': user.mobile}
      )

    # Success: set password and mark OTP as consumed
    user.set_password(new_password)
    user.save()

    otp_record.is_used = True
    otp_record.save()

    del request.session['reset_user_id']
    messages.success(
        request, 'Password updated successfully! Please log in now.'
    )
    return redirect('login')

  return render(request, 'accounts/otp_verify.html', {'mobile': user.mobile})







from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import PasswordResetOTP
from .utils import send_otp_via_email

User = get_user_model()

def forgot_password_email_request(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        # The custom User model stores email addresses in `mail`.
        user = User.objects.filter(mail__iexact=email).first()

        if not user or not user.mail:
            messages.error(
                request,
                'No registered account found with that email address.'
            )
            return render(request, 'accounts/email_otp_request.html')

        # Generate an OTP for this user.
        otp_obj = PasswordResetOTP.generate_otp(user)

        # Send the OTP to the registered email address.
        ok, result = send_otp_via_email(user.mail, otp_obj.otp)

        if not ok:
            # Invalidate the OTP if delivery fails.
            otp_obj.is_used = True
            otp_obj.save(update_fields=['is_used'])

            messages.error(
                request,
                'We could not send the verification email. '
                'Please check the email configuration and try again.'
            )
            return render(request, 'accounts/email_otp_request.html')

        # Save reset session only after successful email delivery.
        request.session['reset_user_id'] = user.id
        request.session['reset_email'] = user.mail

        messages.success(
            request,
            f'A verification code has been sent to {user.mail}.'
        )
        return redirect('forgot_password_email_verify')

    return render(request, 'accounts/email_otp_request.html')


def forgot_password_email_verify(request):
    user_id = request.session.get('reset_user_id')
    user_email = request.session.get('reset_email', '')

    if not user_id:
        messages.error(request, 'Session expired. Please request a new OTP.')
        return redirect('forgot_password_email_request')

    user = User.objects.filter(id=user_id).first()

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        otp_record = PasswordResetOTP.objects.filter(
            user=user,
            otp=entered_otp
        ).order_by('-created_at').first()

        if not otp_record or not otp_record.is_valid():
            messages.error(request, 'Invalid or expired OTP code.')
            return render(request, 'accounts/email_otp_verify.html', {'email': user_email})

        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return render(request, 'accounts/email_otp_verify.html', {'email': user_email})

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/email_otp_verify.html', {'email': user_email})

        # Set new password and invalidate OTP
        user.set_password(new_password)
        user.save()

        otp_record.is_used = True
        otp_record.save()

        # Clear session
        request.session.pop('reset_user_id', None)
        request.session.pop('reset_email', None)

        messages.success(request, 'Password updated successfully! Please sign in with your new password.')
        return redirect('login')

    return render(request, 'accounts/email_otp_verify.html', {'email': user_email})





from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    return render(request, "instagram_scheduler/dashboard.html")

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    return render(request, "accounts/home.html")











