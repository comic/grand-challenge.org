from django.contrib import admin
from knox import models


@admin.register(models.AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
    list_display = (
        "token_key",
        "user",
        "created",
        "expiry",
    )
    fields = ()
    readonly_fields = (
        "user",
        "token_key",
        "key",
    )
    search_fields = ("user__username",)
