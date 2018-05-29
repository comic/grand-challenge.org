# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel


class Algorithm(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )

    challenge = models.ManyToManyField(to='challenges.Challenge')
