from django.db import models


class ChallengeTypeChoices(models.IntegerChoices):
    """Challenge type choices."""

    T1 = 1, "Type 1 - prediction submission"
    T2 = 2, "Type 2 - algorithm submission"
