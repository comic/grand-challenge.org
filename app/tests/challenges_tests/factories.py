from datetime import timedelta

from django.utils.timezone import now

from grandchallenge.challenges.models import ChallengeRequest
from tests.factories import ChallengeRequestFactory


def generate_type_2_challenge_request(creator):
    return ChallengeRequestFactory(
        creator=creator,
        start_date=now(),
        end_date=now() + timedelta(days=1),
        challenge_type=ChallengeRequest.ChallengeTypeChoices.T2,
        expected_number_of_teams=10,
        inference_time_limit=10,
        average_size_of_test_image=10,
        phase_1_number_of_submissions_per_team=10,
        phase_2_number_of_submissions_per_team=1,
        phase_1_number_of_test_images=100,
        phase_2_number_of_test_images=500,
        number_of_tasks=1,
    )


def generate_type_1_challenge_request(creator):
    return ChallengeRequestFactory(
        creator=creator,
        start_date=now(),
        end_date=now() + timedelta(days=1),
        challenge_type=ChallengeRequest.ChallengeTypeChoices.T1,
        expected_number_of_teams=10,
    )
