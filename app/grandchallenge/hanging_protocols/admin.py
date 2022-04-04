from django.contrib import admin
from django.contrib.admin import ModelAdmin

from grandchallenge.hanging_protocols.models import HangingProtocol


class HangingProtocolAdmin(ModelAdmin):
    readonly_fields = ("creator",)


admin.site.register(HangingProtocol, HangingProtocolAdmin)
