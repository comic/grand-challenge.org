from django.core.exceptions import ValidationError
from django.db import models


class TermsOfService(models.Model):
    body = models.TextField()

    def save(self, *args, **kwrags):
        if not self.pk and TermsOfService.objects.exists():
            raise ValidationError("Only one terms of service instance allowed")
        return super().save(*args, **kwrags)
