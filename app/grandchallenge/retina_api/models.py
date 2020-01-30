from django.contrib.postgres.fields import JSONField
from django.db import models


class ArchiveDataModel(models.Model):
    value = JSONField()
    modified = models.DateTimeField(auto_now=True)
