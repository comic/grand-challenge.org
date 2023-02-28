from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView
from django_countries import countries

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.algorithms.models import Job as AlgorithmJob
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Evaluation as EvaluationJob
from grandchallenge.evaluation.models import Submission
from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
from grandchallenge.statistics.tasks import update_site_statistics_cache
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Session, Workstation


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

    @staticmethod
    def _horizontal_chart_spec(*, values, lookup, title):
        url_lookup = "absolute_url"
        challenge_name_lookup = "short_name"
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": "container",
            "padding": 0,
            "data": {"values": values},
            "mark": "bar",
            "encoding": {
                "color": {
                    "field": lookup,
                    "type": "nominal",
                    "legend": None,
                    "scale": {"scheme": {"name": "viridis", "extent": [0, 1]}},
                },
                "tooltip": [
                    {
                        "field": challenge_name_lookup,
                        "type": "nominal",
                        "title": "Challenge",
                    },
                    {
                        "field": lookup,
                        "type": "quantitative",
                        "title": title,
                        "format": ".0f",
                    },
                ],
                "y": {
                    "field": challenge_name_lookup,
                    "type": "nominal",
                    "axis": {"labelAngle": 0},
                    "title": None,
                    "sort": "-x",
                },
                "x": {
                    "field": lookup,
                    "type": "quantitative",
                    "title": title,
                    "axis": {"tickMinStep": "1", "format": ".0f"},
                },
                "href": {"field": url_lookup, "type": "nominal"},
            },
        }

    @staticmethod
    def _world_map_chart_spec(*, values):
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": "container",
            "height": "container",
            "padding": 0,
            "view": {"stroke": "transparent", "fill": "#c9eeff"},
            "data": {
                "url": "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json",
                "format": {"type": "topojson", "feature": "countries"},
            },
            "transform": [
                {
                    "lookup": "id",
                    "from": {
                        "data": {"values": values},
                        "key": "id",
                        "fields": ["participants"],
                    },
                    "default": 0.01,
                }
            ],
            "projection": {"type": "equalEarth"},
            "mark": {
                "type": "geoshape",
                "stroke": "#757575",
                "strokeWidth": 0.5,
            },
            "encoding": {
                "color": {
                    "field": "participants",
                    "type": "quantitative",
                    "scale": {
                        "scheme": "viridis",
                        "domainMin": 1,
                        "type": "log",
                    },
                    "legend": None,
                    "condition": {
                        "test": "datum['participants'] === 0.01",
                        "value": "#eee",
                    },
                },
                "tooltip": [
                    {
                        "field": "properties.name",
                        "type": "nominal",
                        "title": "Country",
                    },
                    {
                        "field": "participants",
                        "type": "quantitative",
                        "title": "Participants",
                        "format": ".0f",
                    },
                ],
            },
        }

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

        extra = {
            "users_total": sum(
                datum["object_count"] for datum in stats["users"]
            ),
            "countries": self._world_map_chart_spec(
                values=[
                    {
                        "id": countries.numeric(c[0], padded=True),
                        "participants": c[1],
                    }
                    for c in stats["countries"]
                ]
            ),
            "challenge_registrations_period": self._horizontal_chart_spec(
                values=self._challenge_qs_to_list_with_url(
                    public_challenges.filter(
                        registrationrequest__created__gt=time_period
                    )
                    .annotate(
                        num_registrations_period=Count("registrationrequest")
                    )
                    .order_by("-num_registrations_period")
                    .values("short_name", "num_registrations_period")[
                        :max_num_results
                    ]
                ),
                lookup="num_registrations_period",
                title=f"Number of registrations last {days} days",
            ),
            "challenge_submissions_period": self._horizontal_chart_spec(
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
            "public_challenges": public_challenges.count(),
            "hidden_challenges": Challenge.objects.filter(hidden=True).count(),
            "submissions": Submission.objects.count(),
            "submissions_period": (
                Submission.objects.filter(created__gt=time_period).count()
            ),
            "latest_public_challenge": (
                public_challenges.order_by("-created").first()
            ),
            "mp_group": (
                Group.objects.filter(
                    participants_of_challenge__in=public_challenges
                )
                .annotate(num_users=Count("user"))
                .order_by("-num_users")
                .first()
            ),
            "mp_challenge_submissions": (
                public_challenges.annotate(
                    num_submissions=Count("phase__submission")
                )
                .order_by("-num_submissions")
                .first()
            ),
            "latest_result": (
                EvaluationJob.objects.filter(
                    published=True,
                    submission__phase__challenge__hidden=False,
                    rank__gt=0,
                    status=EvaluationJob.SUCCESS,
                )
                .select_related("submission__phase__challenge")
                .order_by("-created")
                .first()
            ),
            "public_algorithms": (
                Algorithm.objects.filter(public=True).count()
            ),
            "private_algorithms": (
                Algorithm.objects.filter(public=False).count()
            ),
            "algorithm_jobs": AlgorithmJob.objects.count(),
            "algorithm_jobs_period": AlgorithmJob.objects.filter(
                created__gt=time_period
            ).count(),
            "public_reader_studies": ReaderStudy.objects.filter(
                public=True
            ).count(),
            "private_reader_studies": ReaderStudy.objects.filter(
                public=False
            ).count(),
            "questions": Question.objects.count(),
            "answers": Answer.objects.count(),
            "public_workstations": Workstation.objects.filter(
                public=True
            ).count(),
            "private_workstations": Workstation.objects.filter(
                public=False
            ).count(),
            "workstation_sessions": Session.objects.count(),
            "total_session_duration": (
                Session.objects.aggregate(Sum("maximum_duration"))[
                    "maximum_duration__sum"
                ]
            ),
            "public_archives": Archive.objects.filter(public=True).count(),
            "private_archives": Archive.objects.filter(public=False).count(),
            "images": Image.objects.count(),
        }

        context.update(extra)

        return context
