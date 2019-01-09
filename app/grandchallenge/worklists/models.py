from django.db import models
from django.db.models import CharField

from grandchallenge.core.models import UUIDModel


class WorklistSet(UUIDModel):
    title = CharField(null=False, blank=False, max_length=255)

    def get_children(self):
        return Worklist.objects.filter(set=self.pk)

    def __str__(self):
        return "%s (%s)" % (self.title, str(self.id))


class Worklist(UUIDModel):
    title = CharField(null=False, blank=False, max_length=255)
    set = models.ForeignKey(
        "WorklistSet", null=False, blank=False, on_delete=models.CASCADE
    )

    def __str__(self):
        return "%s (%s)" % (self.title, str(self.id))
