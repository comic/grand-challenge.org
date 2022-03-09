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
    fields = [
        field.name
        for field in Challenge._meta.fields
        if field.editable and not field.auto_created
    ] + ["task_types", "modalities", "structures"]


class ExternalChallengeAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    autocomplete_fields = ("publications",)


class ChallengeRequestAdmin(ModelAdmin):
    readonly_fields = ("creator",)
    ordering = ("-created",)
    list_display = ("short_name", "creator", "created", "status")
    fields = [
        field.name for field in ChallengeRequest._meta.fields if field.editable
    ] + ["task_types", "modalities", "structures"]


admin.site.register(Challenge, ChallengeAdmin)
admin.site.register(ExternalChallenge, ExternalChallengeAdmin)
admin.site.register(ChallengeSeries)
admin.site.register(ChallengeRequest, ChallengeRequestAdmin)
