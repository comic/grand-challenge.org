from django.db import models
from django.db.models import CharField


class WorklistSet(models.Model):
    title = CharField(null=False, blank=False, max_length=255)

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in WorklistSet._meta.fields]

    def get_children(self):
        return Worklist.objects.filter(set=self.pk, parent=None)


class Worklist(models.Model):
    title = CharField(null=False, blank=False, max_length=255)
    parent = models.ForeignKey("Worklist", null=True, blank=True)
    set = models.ForeignKey("WorklistSet", null=False, blank=False)

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in Worklist._meta.fields]
