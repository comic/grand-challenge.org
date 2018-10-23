from celery import shared_task

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
