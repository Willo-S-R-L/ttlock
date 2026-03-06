from django.contrib import admin

from .models import Lock

@admin.register(Lock)
class LockAdmin(admin.ModelAdmin):
    list_display = [
        "ttlock_id"
    ]
    search_fields = ["ttlock_id"]
    list_filter = ["created_at"]

    readonly_fields = [
        "ttlock_id",
        "owner",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        return super().get_actions(request)
