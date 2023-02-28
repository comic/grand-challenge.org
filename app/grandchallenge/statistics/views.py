from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from django.views.generic import TemplateView
from django_countries import countries

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Evaluation as EvaluationJob
from grandchallenge.evaluation.models import Phase
from grandchallenge.reader_studies.models import Question
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

    @staticmethod
    def _bar_chart_spec(*, values, lookup, title):
        chart = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": "container",
            "padding": 0,
            "title": title,
            "data": {"values": values},
            "mark": "bar",
            "encoding": {
                "x": {
                    "field": "Month",
                    "type": "quantitative",
                    "timeUnit": "yearmonth",
                },
                "y": {
                    "field": lookup,
                    "type": "quantitative",
                },
                "tooltip": [
                    {
                        "field": "Month",
                        "type": "quantitative",
                        "timeUnit": "yearmonth",
                    },
                    {"field": lookup, "type": "quantitative"},
                ],
            },
        }

        totals = sum(datum[lookup] for datum in values)

        return {"chart": chart, "totals": totals}

    @staticmethod
    def _stacked_bar_chart_spec(*, values, lookup, title, facet, domain):
        domain = dict(domain)

        totals = {str(d): 0 for d in domain.values()}
        for datum in values:
            datum[facet] = domain[datum[facet]]
            totals[str(datum[facet])] += datum[lookup]

        chart = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": "container",
            "padding": 0,
            "title": title,
            "data": {"values": values},
            "mark": "bar",
            "encoding": {
                "x": {
                    "field": "Month",
                    "type": "quantitative",
                    "timeUnit": "yearmonth",
                },
                "y": {
                    "field": lookup,
                    "type": "quantitative",
                    "stack": True,
                },
                "tooltip": [
                    {
                        "field": "Month",
                        "type": "quantitative",
                        "timeUnit": "yearmonth",
                    },
                    {"field": facet, "type": "nominal"},
                    {"field": lookup, "type": "quantitative"},
                ],
                "color": {
                    "field": facet,
                    "scale": {
                        "domain": list(domain.values()),
                    },
                    "type": "nominal",
                },
            },
        }

        return {"chart": chart, "totals": totals}

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

        context.update(
            {
                "users": self._bar_chart_spec(
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
                "countries": self._world_map_chart_spec(
                    values=[
                        {
                            "id": countries.numeric(c[0], padded=True),
                            "participants": c[1],
                        }
                        for c in stats["countries"]
                    ]
                ),
                "challenges": self._stacked_bar_chart_spec(
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
                "submissions": self._stacked_bar_chart_spec(
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
                "algorithms": self._stacked_bar_chart_spec(
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
                "jobs": self._bar_chart_spec(
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
                "archives": self._stacked_bar_chart_spec(
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
                "images": self._bar_chart_spec(
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
                "reader_studies": self._stacked_bar_chart_spec(
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
                "answers": self._bar_chart_spec(
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
                "sessions": self._bar_chart_spec(
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
                "sessions_duration_total": sum(
                    datum["duration_sum"].total_seconds()
                    for datum in stats["sessions"]
                ),
                "challenge_registrations_period": self._horizontal_chart_spec(
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
                "questions": Question.objects.count(),
                "workstations": {
                    str(o["public"]): o["object_count"]
                    for o in Workstation.objects.values("public").annotate(
                        object_count=Count("public")
                    )
                },
            }
        )

        return context
