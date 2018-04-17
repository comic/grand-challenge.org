# -*- coding: utf-8 -*-
from django.db import models

from grandchallenge.minioupload.models import MinioFile


class Case(MinioFile):
    TRAINING = 'TRAIN'
    TESTING = 'TEST'
    NONE = 'NONE'

    STAGE_CHOICES = (
        (TRAINING, 'Training'),
        (TESTING, 'Testing'),
        (NONE, 'None'),
    )

    challenge = models.ForeignKey(
        to='challenges.Challenge', on_delete=models.CASCADE, editable=False,
    )
    stage = models.CharField(
        max_length=5, choices=STAGE_CHOICES, default=NONE,
    )
