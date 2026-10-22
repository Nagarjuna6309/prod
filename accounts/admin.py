
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordResetOTP, MobileRegistrationOTP


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("mobile",)
    list_display = ("mobile", "user_fullname", "mail", "is_staff", "is_active")
    search_fields = ("mobile", "user_fullname", "mail")
    list_filter = ("is_staff", "is_active", "is_superuser")

    fieldsets = (
        (None, {"fields": ("mobile", "password")}),
        ("Personal info", {"fields": ("user_fullname", "mail")}),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("mobile", "password1", "password2"),
        }),
    )

    filter_horizontal = ("groups", "user_permissions")


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "otp", "created_at", "is_used")
    list_filter = ("is_used", "created_at")
    search_fields = ("user__mobile",)


@admin.register(MobileRegistrationOTP)
class MobileRegistrationOTPAdmin(admin.ModelAdmin):
    list_display = ("mobile", "mail", "otp_expires_at", "otp_attempts")
    search_fields = ("mobile", "mail")
