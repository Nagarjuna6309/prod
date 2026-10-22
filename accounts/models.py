
import random

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):

    def create_user(self, mobile, password=None, **extra_fields):
        if not mobile:
            raise ValueError("Mobile number is required")

        user = self.model(
            mobile=mobile,
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)

        return user

    def create_superuser(self, mobile, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            mobile=mobile,
            password=password,
            **extra_fields
        )


class User(AbstractUser):
    username = None

    mobile = models.CharField(
        max_length=10,
        unique=True
    )

    user_fullname = models.CharField(
        max_length=25,
        null=True,
        blank=True
    )

    mail = models.EmailField(
        max_length=30,
        null=True,
        blank=True
    )

    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.mobile


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otps"
    )

    otp = models.CharField(max_length=6)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_used = models.BooleanField(
        default=False
    )

    @classmethod
    def generate_otp(cls, user):
        cls.objects.filter(
            user=user,
            is_used=False
        ).update(is_used=True)

        code = f"{random.randint(100000, 999999)}"

        return cls.objects.create(
            user=user,
            otp=code
        )

    def is_valid(self):
        now = timezone.now()
        delta = (now - self.created_at).total_seconds()

        return (
            not self.is_used
            and delta <= 600
        )


class MobileRegistrationOTP(models.Model):
    mobile = models.CharField(max_length=10)

    user_fullname = models.CharField(
        max_length=25
    )

    mail = models.EmailField(
        max_length=30
    )

    password_hash = models.CharField(
        max_length=128
    )

    otp_hash = models.CharField(
        max_length=128
    )

    otp_expires_at = models.DateTimeField()

    otp_attempts = models.PositiveIntegerField(
        default=0
    )

    last_sent_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.mobile} - {self.mail}"
