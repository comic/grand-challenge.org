from django.contrib import admin

from grandchallenge.challenges.models import (
    BodyRegion,
    BodyStructure,
    Challenge,
    ExternalChallenge,
    ImagingModality,
    TaskType,
)

admin.site.register(Challenge)
admin.site.register(ExternalChallenge)
admin.site.register(BodyRegion)
admin.site.register(BodyStructure)
admin.site.register(ImagingModality)
admin.site.register(TaskType)
