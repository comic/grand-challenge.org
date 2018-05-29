# -*- coding: utf-8 -*-
from django.db import models

from grandchallenge.core.urlresolvers import reverse
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
        to='challenges.Challenge',
        on_delete=models.CASCADE,
        editable=False,
        blank=True, # A case can exist without belonging to a challenge
    )
    stage = models.CharField(
        max_length=5, choices=STAGE_CHOICES, default=NONE,
    )

    @property
    def _default_bucket_name(self):
        return self.challenge.pk

    def get_absolute_url(self):
        return reverse(
            'cases:detail',
            kwargs={
                'challenge_short_name': self.challenge,
                'pk': self.pk,
            }
        )
