from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class ArchiveDataModel(models.Model):
    value = JSONField(encoder=DjangoJSONEncoder)
    modified = models.DateTimeField(auto_now=True)
