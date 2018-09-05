# -*- coding: utf-8 -*-
from django.core.management import BaseCommand

from grandchallenge.challenges.models import Challenge
from grandchallenge.datasets.models import ImageSet


class Command(BaseCommand):
    def handle(self, *args, **options):
        challenges = Challenge.objects.all()

        for challenge in challenges:
            _, train_created = ImageSet.objects.get_or_create(
                challenge=challenge, phase=ImageSet.TRAINING
            )
            _, test_created = ImageSet.objects.get_or_create(
                challenge=challenge, phase=ImageSet.TESTING
            )

            print(
                f"Updated {challenge.short_name:>32}: "
                f"{train_created}, {test_created}"
            )
