from django.core.management import BaseCommand

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        challenges = Challenge.objects.filter(require_participant_review=False)
        for challenge in challenges:
            challenge.access_request_handling = (
                AccessRequestHandlingOptions.ACCEPT_ALL
            )

        Challenge.objects.bulk_update(challenges, ["access_request_handling"])
        print(f"Done! Updated {len(challenges)} challenges.")
