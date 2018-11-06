from django.db import models
from django.db.models import CharField
from django.utils.translation import ugettext_lazy as _


class WorklistSet(models.Model):
    title = CharField(null=False, blank=False, max_length=255)

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in WorklistSet._meta.fields]

    def get_children(self):
        return WorklistTree.objects.filter(set=self.pk)


class WorklistTree(models.Model):
    set = models.ForeignKey('WorklistSet', null=False, blank=False, on_delete=models.CASCADE)


class Worklist(models.Model):
    title = CharField(null=False, blank=False, max_length=255)
    tree = models.ForeignKey('WorklistTree', null=False, blank=False, on_delete=models.CASCADE)
    parent = models.ForeignKey('Worklist', null=True, blank=True, on_delete=models.CASCADE)

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in Worklist._meta.fields]
