from django.db import models
from django.db.models import CharField
from mptt.models import MPTTModel, TreeForeignKey


class WorklistSet(models.Model):
    title = CharField(null=False, blank=False, max_length=255)

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in WorklistSet._meta.fields]

    def get_children(self):
        return WorklistSetNodes.objects.filter(set=self.pk)


class Worklist(MPTTModel):
    title = CharField(null=False, blank=False, max_length=255)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in Worklist._meta.fields]


class WorklistSetNode(models.Model):
    set = models.ForeignKey('WorklistSet', null=False, blank=False, on_delete=models.CASCADE)
    worklist = models.ForeignKey('Worklist', null=False, blank=False, on_delete=models.CASCADE)
