from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from django.views.generic import TemplateView
from django_countries import countries

from grandchallenge.challenges.models import Challenge
from grandchallenge.charts.specs import (
    bar,
    horizontal_bar,
    stacked_bar,
    world_map,
)
from grandchallenge.evaluation.models import Phase
from grandchallenge.statistics.tasks import update_site_statistics_cache
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Workstation


class StatisticsDetail(TemplateView):
    template_name = "statistics/statistics_detail.html"

    @staticmethod
    def _challenge_qs_to_list_with_url(challenge_list):
        return [
            {
                **c,
                "absolute_url": reverse(
                    "pages:home",
                    kwargs={"challenge_short_name": c["short_name"]},
                ),
            }
            for c in challenge_list
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        days = 30
        max_num_results = 10

        time_period = timezone.now() - timedelta(days=days)

        public_challenges = Challenge.objects.filter(hidden=False)

        stats = cache.get(settings.STATISTICS_SITE_CACHE_KEY)

        if stats is None:
            update_site_statistics_cache()
            stats = cache.get(settings.STATISTICS_SITE_CACHE_KEY)

        storage_data = {}

        for key, value in stats.get("storage", {}).items():
            storage_size = value.get("size_in_storage__sum", 0) or 0
            registry_size = value.get("size_in_registry__sum", 0) or 0

            storage_data[key.replace("_", " ")] = {
                "storage_size": storage_size,
                "registry_size": registry_size,
            }

        context.update(
            {
                "users": bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["date_joined__year"],
                                datum["date_joined__month"],
                                1,
                            ).isoformat(),
                            "New Users": datum["object_count"],
                        }
                        for datum in stats["users"]
                    ],
                    lookup="New Users",
                    title="New Users per Month",
                ),
                "countries": world_map(
                    values=[
                        {
                            "id": countries.numeric(c[0], padded=True),
                            "participants": c[1],
                        }
                        for c in stats["countries"]
                    ]
                ),
                "challenges": stacked_bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "New Challenges": datum["object_count"],
                            "Visibility": not datum["hidden"],
                        }
                        for datum in stats["challenges"]
                    ],
                    lookup="New Challenges",
                    title="New Challenges per Month",
                    facet="Visibility",
                    domain=[(True, "Public"), (False, "Private")],
                ),
                "submissions": stacked_bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "New Submissions": datum["object_count"],
                            "Challenge Type": datum["phase__submission_kind"],
                        }
                        for datum in stats["submissions"]
                    ],
                    lookup="New Submissions",
                    title="New Submissions per Month",
                    facet="Challenge Type",
                    domain=[
                        (Phase.SubmissionKindChoices.CSV, "Predictions"),
                        (Phase.SubmissionKindChoices.ALGORITHM, "Algorithm"),
                    ],
                ),
                "algorithms": stacked_bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "New Algorithms": datum["object_count"],
                            "Visibility": datum["public"],
                        }
                        for datum in stats["algorithms"]
                    ],
                    lookup="New Algorithms",
                    title="New Algorithms per Month",
                    facet="Visibility",
                    domain=[(True, "Public"), (False, "Private")],
                ),
                "jobs": bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "Inference Jobs": datum["object_count"],
                        }
                        for datum in stats["jobs"]
                    ],
                    lookup="Inference Jobs",
                    title="Inference Jobs per Month",
                ),
                "job_durations": bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "Inference Hours": (
                                datum["duration_sum"].total_seconds()
                                // (60 * 60)
                                if datum["duration_sum"]
                                else 0
                            ),
                        }
                        for datum in stats["jobs"]
                    ],
                    lookup="Inference Hours",
                    title="Inference Hours per Month",
                ),
                "archives": stacked_bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "New Archives": datum["object_count"],
                            "Visibility": datum["public"],
                        }
                        for datum in stats["archives"]
                    ],
                    lookup="New Archives",
                    title="New Archives per Month",
                    facet="Visibility",
                    domain=[(True, "Public"), (False, "Private")],
                ),
                "images": bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "New Images": datum["object_count"],
                        }
                        for datum in stats["images"]
                    ],
                    lookup="New Images",
                    title="New Images per Month",
                ),
                "reader_studies": stacked_bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "New Reader Studies": datum["object_count"],
                            "Visibility": datum["public"],
                        }
                        for datum in stats["reader_studies"]
                    ],
                    lookup="New Reader Studies",
                    title="New Reader Studies per Month",
                    facet="Visibility",
                    domain=[(True, "Public"), (False, "Private")],
                ),
                "answers": bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "New Answers": datum["object_count"],
                        }
                        for datum in stats["answers"]
                    ],
                    lookup="New Answers",
                    title="New Answers per Month",
                ),
                "sessions": bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "Total Hours": datum[
                                "duration_sum"
                            ].total_seconds()
                            // (60 * 60),
                        }
                        for datum in stats["sessions"]
                    ],
                    lookup="Total Hours",
                    title="Total Session Hours per Month",
                ),
                "sessions_total": sum(
                    datum["object_count"] for datum in stats["sessions"]
                ),
                "most_popular_challenge_group": stats.get(
                    "most_popular_challenge_group"
                ),
                "most_popular_challenge_submissions": stats.get(
                    "most_popular_challenge_submissions"
                ),
                "challenge_registrations_period": horizontal_bar(
                    values=self._challenge_qs_to_list_with_url(
                        public_challenges.filter(
                            registrationrequest__created__gt=time_period
                        )
                        .annotate(
                            num_registrations_period=Count(
                                "registrationrequest"
                            )
                        )
                        .order_by("-num_registrations_period")
                        .values("short_name", "num_registrations_period")[
                            :max_num_results
                        ]
                    ),
                    lookup="num_registrations_period",
                    title=f"Number of registrations last {days} days",
                ),
                "challenge_submissions_period": horizontal_bar(
                    values=self._challenge_qs_to_list_with_url(
                        public_challenges.filter(
                            phase__submission__created__gt=time_period
                        )
                        .annotate(
                            num_submissions_period=Count("phase__submission")
                        )
                        .order_by("-num_submissions_period")
                        .values("short_name", "num_submissions_period")[
                            :max_num_results
                        ]
                    ),
                    lookup="num_submissions_period",
                    title=f"Number of submissions last {days} days",
                ),
                "days": days,
                "max_num_results": max_num_results,
                "logged_in_period": (
                    get_user_model()
                    .objects.filter(last_login__gt=time_period)
                    .count()
                ),
                "workstations": {
                    str(o["public"]): o["object_count"]
                    for o in Workstation.objects.values("public")
                    .annotate(object_count=Count("public"))
                    .order_by("public")
                },
                "storage_data": storage_data,
                "storage_total": sum(
                    v["storage_size"] for v in storage_data.values()
                ),
                "registry_total": sum(
                    v["registry_size"] for v in storage_data.values()
                ),
                "this_month_jobs": stats.get("this_month_jobs"),
            }
        )

        return context
