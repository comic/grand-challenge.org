from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class ArchiveDataModel(models.Model):
    value = models.JSONField(encoder=DjangoJSONEncoder)
    modified = models.DateTimeField(auto_now=True)
