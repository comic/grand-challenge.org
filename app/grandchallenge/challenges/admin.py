from django.contrib import admin
from django.contrib.admin import ModelAdmin

from grandchallenge.challenges.models import (
    BodyStructure,
    Challenge,
    ChallengeSeries,
    ExternalChallenge,
    ImagingModality,
    TaskType,
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
admin.site.register(BodyStructure)
admin.site.register(ImagingModality)
admin.site.register(TaskType)
