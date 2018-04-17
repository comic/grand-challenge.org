# -*- coding: utf-8 -*-
from django.apps import AppConfig


class MiniouploadConfig(AppConfig):
    name = 'grandchallenge.minioupload'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.minioupload.signals
