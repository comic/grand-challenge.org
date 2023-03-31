from django.contrib import admin
from django.contrib.admin import ModelAdmin

from grandchallenge.credits.models import Credit


@admin.register(Credit)
class CreditAdmin(ModelAdmin):
    list_display = ("user", "credits")
    autocomplete_fields = ("user",)
    search_fields = ("user__username", "user__email")
