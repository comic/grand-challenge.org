import pytest

from grandchallenge.challenges.models import OnboardingTask
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_onboarding_tasks_created():
    challenge = ChallengeFactory()

    # Expected task details
    expected_tasks = [
        ("Create Phases", "ORG"),
        ("Define Inputs and Outputs", "ORG"),
        ("Create Archives", "SUP"),
        ("Upload Data", "ORG"),
        ("Example Algorithm", "ORG"),
        ("Evaluation Method", "ORG"),
        ("Scoring", "ORG"),
        ("Test Evaluation", "ORG"),
    ]

    tasks = list(
        OnboardingTask.objects.filter(challenge=challenge).order_by("deadline")
    )

    assert len(tasks) == len(
        expected_tasks
    ), "Unexpected number of onboarding tasks."

    for task, (expected_title, expected_responsible_party) in zip(
        tasks, expected_tasks, strict=True
    ):
        assert (
            task.title == expected_title
        ), f"Expected title {expected_title:!r}, got {task.title:!r}"
        assert (
            task.responsible_party == expected_responsible_party
        ), f"Expected responsible party'{expected_responsible_party:!r}, got {task.responsible_party:!r}"
