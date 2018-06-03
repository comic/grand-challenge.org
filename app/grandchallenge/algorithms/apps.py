# -*- coding: utf-8 -*-
from django.apps import AppConfig


class AlgorithmsConfig(AppConfig):
    name = "grandchallenge.algorithms"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.algorithms.signals
