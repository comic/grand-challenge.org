from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, Sum

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Submission
from grandchallenge.reader_studies.models import Answer, ReaderStudy
from grandchallenge.workstations.models import Session


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def update_site_statistics_cache():
    statistics = {}

    statistics["users"] = (
        get_user_model()
        .objects.values(
            "verification__is_verified",
            "date_joined__year",
            "date_joined__month",
        )
        .annotate(object_count=Count("verification__is_verified"))
        .order_by(
            "date_joined__year", "date_joined__month", "verification_count"
        )
    )

    statistics["countries"] = (
        get_user_model()
        .objects.exclude(user_profile__country="")
        .values("user_profile__country")
        .annotate(country_count=Count("user_profile__country"))
        .order_by("-country_count")
        .values_list("user_profile__country", "country_count")
    )

    statistics["challenges"] = (
        Challenge.objects.values("hidden", "created__year", "created__month")
        .annotate(object_count=Count("hidden"))
        .order_by("created__year", "created__month", "hidden")
    )

    statistics["submissions"] = (
        Submission.objects.values(
            "phase__submission_kind", "created__year", "created__month"
        )
        .annotate(object_count=Count("phase__submission_kind"))
        .order_by("created__year", "created__month", "phase__submission_kind")
    )

    statistics["algorithms"] = (
        Algorithm.objects.values("public", "created__year", "created__month")
        .annotate(object_count=Count("public"))
        .order_by("created__year", "created__month", "public")
    )

    statistics["jobs"] = (
        Job.objects.values("created__year", "created__month")
        .annotate(object_count=Count("created__month"))
        .order_by("created__year", "created__month")
    )

    statistics["archives"] = (
        Archive.objects.values("public", "created__year", "created__month")
        .annotate(object_count=Count("public"))
        .order_by("created__year", "created__month", "public")
    )

    statistics["images"] = (
        Image.objects.values("created__year", "created__month")
        .annotate(object_count=Count("created__month"))
        .order_by("created__year", "created__month")
    )

    statistics["reader_studies"] = (
        ReaderStudy.objects.values("public", "created__year", "created__month")
        .annotate(object_count=Count("public"))
        .order_by("created__year", "created__month", "public")
    )

    statistics["answers"] = (
        Answer.objects.values("created__year", "created__month")
        .annotate(object_count=Count("created__month"))
        .order_by("created__year", "created__month")
    )

    statistics["sessions"] = (
        Session.objects.values("created__year", "created__month")
        .annotate(duration_sum=Sum("maximum_duration"))
        .order_by("created__year", "created__month")
    )

    cache.set(settings.STATISTICS_SITE_CACHE_KEY, statistics, timeout=None)
