from django.core.management import BaseCommand

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.utils.access_request_utils import (
    AccessRequestHandlingOptions,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        challenges = Challenge.objects.all()
        for challenge in challenges:
            if not challenge.require_participant_review:
                challenge.access_request_handling = (
                    AccessRequestHandlingOptions.ACCEPT_ALL
                )

        Challenge.objects.bulk_update(challenges, ["access_request_handling"])
        print(f"Done! Updated {len(challenges)} challenges.")
