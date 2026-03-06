from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = [
        "username",
        "is_active",
        "is_superuser",
        "last_login",
        "date_joined",
    ]
    list_filter = ["is_active", "is_superuser", "last_login"]

    fieldsets = [
        (None, {"fields": ["username", "password"]}),
        ("Authorization", {"fields": ["is_active", "is_staff", "is_superuser"]}),
    ]

    add_fieldsets = [
        (
            None,
            {
                "classes": [
                    "wide",
                ],
                "fields": ["username", "password1", "password2", "is_staff"],
            },
        ),
    ]
