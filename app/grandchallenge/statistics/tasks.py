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
    stats = {}

    stats["users"] = (
        get_user_model()
        .objects.values(
            "date_joined__year",
            "date_joined__month",
        )
        .annotate(object_count=Count("date_joined__month"))
        .order_by("date_joined__year", "date_joined__month")
    )

    stats["countries"] = (
        get_user_model()
        .objects.exclude(user_profile__country="")
        .values("user_profile__country")
        .annotate(country_count=Count("user_profile__country"))
        .order_by("-country_count")
        .values_list("user_profile__country", "country_count")
    )

    stats["challenges"] = (
        Challenge.objects.values("hidden", "created__year", "created__month")
        .annotate(object_count=Count("hidden"))
        .order_by("created__year", "created__month", "hidden")
    )

    stats["submissions"] = (
        Submission.objects.values(
            "phase__submission_kind", "created__year", "created__month"
        )
        .annotate(object_count=Count("phase__submission_kind"))
        .order_by("created__year", "created__month", "phase__submission_kind")
    )

    stats["algorithms"] = (
        Algorithm.objects.values("public", "created__year", "created__month")
        .annotate(object_count=Count("public"))
        .order_by("created__year", "created__month", "public")
    )

    stats["jobs"] = (
        Job.objects.values("created__year", "created__month")
        .annotate(object_count=Count("created__month"))
        .order_by("created__year", "created__month")
    )

    stats["archives"] = (
        Archive.objects.values("public", "created__year", "created__month")
        .annotate(object_count=Count("public"))
        .order_by("created__year", "created__month", "public")
    )

    stats["images"] = (
        Image.objects.values("created__year", "created__month")
        .annotate(object_count=Count("created__month"))
        .order_by("created__year", "created__month")
    )

    stats["reader_studies"] = (
        ReaderStudy.objects.values("public", "created__year", "created__month")
        .annotate(object_count=Count("public"))
        .order_by("created__year", "created__month", "public")
    )

    stats["answers"] = (
        Answer.objects.values("created__year", "created__month")
        .annotate(object_count=Count("created__month"))
        .order_by("created__year", "created__month")
    )

    stats["sessions"] = (
        Session.objects.values("created__year", "created__month")
        .annotate(duration_sum=Sum("maximum_duration"))
        .order_by("created__year", "created__month")
    )

    cache.set(settings.STATISTICS_SITE_CACHE_KEY, stats, timeout=None)
