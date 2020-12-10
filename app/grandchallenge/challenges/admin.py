from django.contrib import admin
from django.contrib.admin import ModelAdmin

from grandchallenge.challenges.models import (
    Challenge,
    ChallengeSeries,
    ExternalChallenge,
)


class ChallengeAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    autocomplete_fields = ("publications",)


class ExternalChallengeAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    autocomplete_fields = ("publications",)


admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(ExternalChallenge, ExternalChallengeAdmin)
admin.site.register(ChallengeSeries)
