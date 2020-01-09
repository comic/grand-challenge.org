from celery import shared_task
from django.core.mail import mail_managers
from requests import exceptions, get

from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.evaluation.models import Result
from grandchallenge.subdomains.utils import reverse


@shared_task
def update_filter_classes():
    lookup = (
        "creator",
        "modalities",
        "series",
        "structures__region",
        "task_types",
    )

    for obj in [Challenge, ExternalChallenge]:
        for c in obj.objects.prefetch_related(*lookup).all():
            kwargs = {"filter_classes": c.get_filter_classes()}

            if isinstance(c, Challenge):
                kwargs.update(
                    {
                        "cached_num_participants": c.participants_group.user_set.all().count()
                    }
                )

                challenge_results = Result.objects.filter(
                    job__submission__challenge=c, published=True
                ).order_by("-created")

                try:
                    kwargs.update(
                        {
                            "cached_num_results": challenge_results.count(),
                            "cached_latest_result": challenge_results.first().created,
                        }
                    )
                except AttributeError:
                    # No results for this challenge
                    kwargs.update(
                        {"cached_num_results": 0, "cached_latest_result": None}
                    )

            obj.objects.filter(pk=c.pk).update(**kwargs)


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
            r = get(url)
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
