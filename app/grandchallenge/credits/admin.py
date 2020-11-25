from django.contrib import admin
from django.contrib.admin import ModelAdmin

from grandchallenge.credits.models import Credit


class CreditAdmin(ModelAdmin):
    autocomplete_fields = ("user",)


admin.site.register(Credit, CreditAdmin)
