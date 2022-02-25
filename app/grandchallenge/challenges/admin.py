from django.contrib import admin
from django.contrib.admin import ModelAdmin

from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    ChallengeSeries,
    ExternalChallenge,
)


class ChallengeAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    autocomplete_fields = ("publications",)
    ordering = ("-created",)
    list_display = ("short_name", "created")
    search_fields = ("short_name",)


class ExternalChallengeAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    autocomplete_fields = ("publications",)


class ChallengeRequestAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    ordering = ("-created",)
    list_display = ("short_name", "creator", "created", "approved")


admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(ExternalChallenge, ExternalChallengeAdmin)
admin.site.register(ChallengeSeries)
admin.site.register(ChallengeRequest)
