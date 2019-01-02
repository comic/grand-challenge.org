from celery import shared_task
from django.core.mail import mail_managers
from requests import get, exceptions

from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.subdomains.utils import reverse


@shared_task
def update_filter_classes():
    lookup = ("task_types", "modalities", "structures__region", "creator")

    for obj in [Challenge, ExternalChallenge]:
        for c in obj.objects.prefetch_related(*lookup).all():
            classes = c.get_filter_classes()
            kwargs = {"filter_classes": classes}

            if isinstance(c, Challenge):
                kwargs.update(
                    {
                        "cached_num_participants": c.participants_group.user_set.all().count()
                    }
                )

                try:
                    kwargs.update(
                        {
                            "cached_num_results": c.result_set.filter(
                                published=True
                            ).count(),
                            "cached_latest_result": c.result_set.filter(
                                published=True
                            )
                            .order_by("-created")
                            .first()
                            .created,
                        }
                    )
                except AttributeError:
                    # This will fail if there are no results
                    pass

            obj.objects.filter(pk=c.pk).update(**kwargs)


@shared_task
def check_external_challenge_urls():
    """
    Checks that all external challenge urls are reachable, and emails the
    managers if not.
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
