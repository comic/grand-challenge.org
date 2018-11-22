from django.db import models
from django.db.models import CharField

from grandchallenge.core.models import UUIDModel


class WorklistSet(UUIDModel):
    title = CharField(null=False, blank=False, max_length=255)

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in WorklistSet._meta.fields]

    def get_children(self):
        return Worklist.objects.filter(set=self.pk)


class Worklist(UUIDModel):
    title = CharField(null=False, blank=False, max_length=255)
    set = models.ForeignKey("WorklistSet", null=False, blank=False, on_delete=models.CASCADE)

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in Worklist._meta.fields]
