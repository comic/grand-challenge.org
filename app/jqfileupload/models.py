from django.db import models

class StagedFile(models.Model):
    """
    Files uploaded but not committed to other forms.
    """
    csrf = models.CharField(max_length=128)
    client_id = models.CharField(max_length=128, null=True)
    client_filename = models.CharField(max_length=128, blank=False)

    file_id = models.UUIDField(blank=False)
    timeout = models.DateTimeField(blank=False)

    file = models.FileField(blank=False)
    start_byte = models.BigIntegerField(blank=False)
    end_byte = models.BigIntegerField(blank=False)
    total_size = models.BigIntegerField(null=True)