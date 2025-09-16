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
        task_ids=[1, 2],
        algorithm_maximum_settable_memory_gb_for_tasks=[32, 32],
        algorithm_selectable_gpu_type_choices_for_tasks=[
            ["", "T4"],
            ["", "T4", "A10G"],
        ],
        average_size_test_image_mb_for_tasks=[
            fake.random_int(1, 1000),
            fake.random_int(1, 1000),
        ],
        inference_time_average_minutes_for_tasks=[
            fake.random_int(5, 60),
            fake.random_int(5, 60),
        ],
        task_id_for_phases=[1, 1, 1, 2, 2, 2],
        number_of_teams_for_phases=(
            [
                fake.random_int(10, 50, 5),
            ]
            * 2
            + [fake.random_int(3, 10)]
            + [
                fake.random_int(10, 50, 5),
            ]
            * 2
            + [fake.random_int(3, 10)]
        ),
        number_of_submissions_per_team_for_phases=2
        * [
            fake.random_int(5, 10),
            fake.random_int(2, 3),
            1,
        ],
        number_of_test_images_for_phases=[
            fake.random_int(1, 5),
            fake.random_int(10, 30, 5),
            fake.random_int(50, 500, 50),
            fake.random_int(1, 5),
            fake.random_int(10, 30, 5),
            fake.random_int(50, 500, 50),
        ],
        data_license=True,
        algorithm_inputs=fake.text(),
        algorithm_outputs=fake.text(),
        challenge_fee_agreement=True,
    )
