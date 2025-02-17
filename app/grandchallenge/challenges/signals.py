from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import timedelta

from grandchallenge.challenges.models import Challenge, OnboardingTask


@receiver(post_save, sender=Challenge)
def create_onboarding_tasks(sender, instance, created, **__):
    if created:  # Ensures tasks are only created on first save
        tasks = [
            OnboardingTask(
                title="Create Phases",
                description="Define, name and create the different phases of the challenge.",
                responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                deadline=instance.created + timedelta(weeks=1),
            ),
            OnboardingTask(
                title="Define Inputs and Outputs",
                description="To support, communicate the required input and output data formats for participant's algorithms.",
                responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                deadline=instance.created + timedelta(weeks=3),
            ),
            OnboardingTask(
                title="Create Archives",
                description="Create an archive per algorithm-type phase for the challenge.",
                responsible_party=OnboardingTask.ResponsiblePartyChoices.SUPPORT,
                deadline=instance.created + timedelta(weeks=3),
            ),
            OnboardingTask(
                title="Upload Data",
                description="Prepare and upload necessary datasets to archives, contact support if no archives are available.",
                responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                deadline=instance.created + timedelta(weeks=5),
            ),
            OnboardingTask(
                title="Example Algorithm",
                description="Implement and document a baseline example algorithm for participants to use as a reference.",
                responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                deadline=instance.created + timedelta(weeks=6, seconds=0),
            ),
            OnboardingTask(
                title="Evaluation Method",
                description="Implement and document the evaluation method for assessing participant submissions.",
                responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                deadline=instance.created + timedelta(weeks=6, seconds=1),
            ),
            OnboardingTask(
                title="Scoring",
                description="Configure the leaderboard scoring to accurately interpret the evaluation results.",
                responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                deadline=instance.created + timedelta(weeks=6, seconds=2),
            ),
            OnboardingTask(
                title="Test Evaluation",
                description="Run test evaluations using sample submissions to ensure the scoring system and evaluation method function correctly before launching the challenge.",
                responsible_party=OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS,
                deadline=instance.created + timedelta(weeks=6, seconds=3),
            ),
        ]

        for t in tasks:
            t.challenge = instance
            t.created = instance.created
            t.save()  # Don't use bulk creation since save() has permission setters
