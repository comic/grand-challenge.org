from django.db import models


class InteractiveAlgorithmLambdaChoices(models.TextChoices):
    ULS23_BASELINE = "uls23-baseline", "ULS23 Baseline"


class InteractiveAlgorithmChoices(models.TextChoices):
    TEMPORARY = "temp", "Temporary choice for development"
