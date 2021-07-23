from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import mail_managers
from django.db.models import Count, Max
from requests import exceptions, get

from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.subdomains.utils import reverse


@shared_task
def update_challenge_results_cache():
    challenges = Challenge.objects.all()
    evaluation_info = (
        Evaluation.objects.filter(published=True)
        .values("submission__phase__challenge_id")
        .annotate(
            cached_num_results=Count("submission__phase__challenge_id"),
            cached_latest_result=Max("created"),
        )
    )
    evaluation_info_by_challenge = {
        str(v["submission__phase__challenge_id"]): v for v in evaluation_info
    }
    participant_counts = (
        get_user_model()
        .objects.values("groups__participants_of_challenge")
        .annotate(cached_num_participants=Count("pk"))
    )
    participant_counts_by_challenge = {
        str(v["groups__participants_of_challenge"]): v
        for v in participant_counts
    }

    for c in challenges:
        c.cached_num_results = evaluation_info_by_challenge.get(
            str(c.pk), {}
        ).get("cached_num_results", 0)
        c.cached_latest_result = evaluation_info_by_challenge.get(
            str(c.pk), {}
        ).get("cached_latest_result", None)
        c.cached_num_participants = participant_counts_by_challenge.get(
            str(c.pk), {}
        ).get("cached_num_participants", 0)

    Challenge.objects.bulk_update(
        challenges,
        [
            "cached_num_results",
            "cached_num_participants",
            "cached_latest_result",
        ],
    )


@shared_task
def check_external_challenge_urls():
    """
    Checks that all external challenge urls are reachable.

    Emails the managers if any of the challenges are not.
    """
    challenges = ExternalChallenge.objects.filter(hidden=False)
    errors = []

    for challenge in challenges:
        try:
            url = challenge.homepage
            if not url.startswith("http"):
                url = "http://" + url
            r = get(url, timeout=60)
            # raise an exception when we receive a http error (e.g., 404)
            r.raise_for_status()
        except exceptions.RequestException as err:
            update_url = reverse(
                "challenges:external-update",
                kwargs={"short_name": challenge.short_name},
            )
            errors.append(
                f"Error when trying to access '{challenge}': {err}. You can "
                f"update it here: {update_url}"
            )

    if errors:
        mail_managers(
            subject=f"Unreachable external challenges ({len(errors)})",
            message="\n\n".join(errors),
        )
