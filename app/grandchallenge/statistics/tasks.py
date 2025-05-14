from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db.models import Count, Sum
from django.utils.timezone import now

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmModel,
    JobUtilization,
)
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.evaluation.models import (
    EvaluationGroundTruth,
    EvaluationUtilization,
    Method,
    Submission,
)
from grandchallenge.reader_studies.models import Answer, ReaderStudy
from grandchallenge.workstations.models import Session, WorkstationImage


@acks_late_micro_short_task
def update_site_statistics_cache():
    public_challenges = Challenge.objects.filter(hidden=False)

    stats = {
        "users": (
            get_user_model()
            .objects.filter(is_active=True, last_login__isnull=False)
            .values(
                "date_joined__year",
                "date_joined__month",
            )
            .annotate(object_count=Count("date_joined__month"))
            .order_by("date_joined__year", "date_joined__month")
        ),
        "countries": (
            get_user_model()
            .objects.exclude(user_profile__country="")
            .values("user_profile__country")
            .annotate(country_count=Count("user_profile__country"))
            .order_by("-country_count")
            .values_list("user_profile__country", "country_count")
        ),
        "challenges": (
            Challenge.objects.values(
                "hidden", "created__year", "created__month"
            )
            .annotate(object_count=Count("hidden"))
            .order_by("created__year", "created__month", "hidden")
        ),
        "submissions": (
            Submission.objects.values(
                "phase__submission_kind", "created__year", "created__month"
            )
            .annotate(object_count=Count("phase__submission_kind"))
            .order_by(
                "created__year", "created__month", "phase__submission_kind"
            )
        ),
        "algorithms": (
            Algorithm.objects.values(
                "public", "created__year", "created__month"
            )
            .annotate(object_count=Count("public"))
            .order_by("created__year", "created__month", "public")
        ),
        "jobs": (
            JobUtilization.objects.values("created__year", "created__month")
            .annotate(
                object_count=Count("created__month"),
                duration_sum=Sum("duration"),
            )
            .order_by("created__year", "created__month", "duration_sum")
        ),
        "archives": (
            Archive.objects.values("public", "created__year", "created__month")
            .annotate(object_count=Count("public"))
            .order_by("created__year", "created__month", "public")
        ),
        "images": (
            Image.objects.values("created__year", "created__month")
            .annotate(object_count=Count("created__month"))
            .order_by("created__year", "created__month")
        ),
        "reader_studies": (
            ReaderStudy.objects.values(
                "public", "created__year", "created__month"
            )
            .annotate(object_count=Count("public"))
            .order_by("created__year", "created__month", "public")
        ),
        "answers": (
            Answer.objects.values("created__year", "created__month")
            .annotate(object_count=Count("created__month"))
            .order_by("created__year", "created__month")
        ),
        "sessions": (
            Session.objects.values("created__year", "created__month")
            .annotate(
                duration_sum=Sum("maximum_duration"),
                object_count=Count("created__month"),
            )
            .order_by("created__year", "created__month")
        ),
        "most_popular_challenge_group": (
            Group.objects.filter(
                participants_of_challenge__in=public_challenges
            )
            .annotate(num_users=Count("user"))
            .order_by("-num_users")
            .first()
        ),
        "most_popular_challenge_submissions": (
            public_challenges.annotate(
                num_submissions=Count("phase__submission")
            )
            .order_by("-num_submissions")
            .only("pk")
            .first()
        ),
        "storage": {
            "algorithm_images": AlgorithmImage.objects.aggregate(
                Sum("size_in_storage"), Sum("size_in_registry")
            ),
            "algorithm_models": AlgorithmModel.objects.aggregate(
                Sum("size_in_storage")
            ),
            "methods": Method.objects.aggregate(
                Sum("size_in_storage"), Sum("size_in_registry")
            ),
            "ground_truths": EvaluationGroundTruth.objects.aggregate(
                Sum("size_in_storage")
            ),
            "workstation_images": WorkstationImage.objects.aggregate(
                Sum("size_in_storage"), Sum("size_in_registry")
            ),
            "image_files": ImageFile.objects.aggregate(Sum("size_in_storage")),
            "socket_values": ComponentInterfaceValue.objects.aggregate(
                Sum("size_in_storage")
            ),
        },
        "this_month_jobs": {
            "algorithm_jobs": JobUtilization.objects.filter(
                created__month=now().month, created__year=now().year
            ).aggregate(Sum("compute_cost_euro_millicents")),
            "evaluations": EvaluationUtilization.objects.filter(
                created__month=now().month, created__year=now().year
            ).aggregate(Sum("compute_cost_euro_millicents")),
        },
    }

    cache.set(settings.STATISTICS_SITE_CACHE_KEY, stats, timeout=None)
