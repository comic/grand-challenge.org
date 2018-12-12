from requests import get, exceptions
from celery import shared_task

from django.conf import settings
from django.core.mail import send_mail
from grandchallenge.challenges.models import Challenge, ExternalChallenge


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
def validate_external_challenges():
    challenges = ExternalChallenge.objects.all()
    errors = []
    for challenge in challenges:
        try:
            url = challenge.homepage
            if not url.startswith('http'):
                url = 'http://' + url
            r = get(url)
            # this cause an exception when we received an http error codes (e.g., 404)
            r.raise_for_status()
        except exceptions.RequestException as err:
            errors.append("Error when trying to access '{}': {}".format(challenge.title, err))

    addresses = [address for _, address in settings.MANAGERS]

    send_mail(
        subject="Unreachable external challenges (%d)".format(len(errors)),
        message="\n".join(errors),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=addresses,
    )
