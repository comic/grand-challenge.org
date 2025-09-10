from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from faker import Faker

from grandchallenge.challenges.models import ChallengeRequest


def run():
    fake = Faker()
    user = get_user_model().objects.get(username="demo")
    ChallengeRequest.objects.create(
        creator=user,
        title=fake.sentence(),
        short_name=fake.word(),
        abstract=fake.paragraph(),
        contact_email=fake.email(),
        start_date=datetime.now() + timedelta(weeks=4),
        end_date=datetime.now() + timedelta(weeks=12),
        organizers=fake.company(),
        challenge_setup=fake.text(),
        data_set=fake.text(),
        submission_assessment=fake.text(),
        challenge_publication=fake.text(),
        code_availability=fake.text(),
        expected_number_of_teams=fake.random_int(10, 50, 5),
        inference_time_limit_in_minutes=fake.random_int(5, 60),
        average_size_of_test_image_in_mb=fake.random_int(1, 1024),
        phase_1_number_of_submissions_per_team=fake.random_int(1, 10),
        phase_2_number_of_submissions_per_team=fake.random_int(1, 5),
        phase_1_number_of_test_images=fake.random_int(1, 5),
        phase_2_number_of_test_images=fake.random_int(50, 1000, 50),
        data_license=True,
        algorithm_inputs=fake.text(),
        algorithm_outputs=fake.text(),
        challenge_fee_agreement=True,
    )
