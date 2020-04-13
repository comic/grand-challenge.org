import json
from datetime import timedelta

import prometheus_client
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import (
    Job as EvaluationJob,
    Result,
    Submission,
)
from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
from grandchallenge.statistics.renderers import PrometheusRenderer
from grandchallenge.workstations.models import Session, Workstation


class StatisticsDetail(TemplateView):
    template_name = "statistics/statistics_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        days = 30
        max_num_results = 10

        User = get_user_model()  # noqa: N806

        time_period = timezone.now() - timedelta(days=days)

        public_challenges = Challenge.objects.filter(hidden=False)

        country_data = (
            User.objects.exclude(user_profile__country="")
            .values("user_profile__country")
            .annotate(country_count=Count("user_profile__country"))
            .order_by("-country_count")
            .values_list("user_profile__country", "country_count")
        )

        extra = {
            "days": days,
            "max_num_results": max_num_results,
            "number_of_users": User.objects.count(),
            "country_data": json.dumps(
                [["Country", "#Participants"]] + list(country_data)
            ),
            "new_users_period": (
                User.objects.filter(date_joined__gt=time_period).count()
            ),
            "logged_in_period": (
                User.objects.filter(last_login__gt=time_period).count()
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
            "challenge_registrations_period": (
                public_challenges.filter(
                    registrationrequest__created__gt=time_period
                )
                .annotate(
                    num_registrations_period=Count("registrationrequest")
                )
                .order_by("-num_registrations_period")[:max_num_results]
            ),
            "mp_challenge_submissions": (
                public_challenges.annotate(num_submissions=Count("submission"))
                .order_by("-num_submissions")
                .first()
            ),
            "challenge_submissions_period": (
                public_challenges.filter(submission__created__gt=time_period)
                .annotate(num_submissions_period=Count("submission"))
                .order_by("-num_submissions_period")[:max_num_results]
            ),
            "latest_result": (
                Result.objects.filter(
                    published=True, job__submission__challenge__hidden=False
                )
                .order_by("-created")
                .first()
            ),
            "using_auto_eval": (
                Challenge.objects.filter(use_evaluation=True).count()
            ),
            "public_algorithms": (
                Algorithm.objects.filter(public=True).count()
            ),
            "hidden_algorithms": (
                Algorithm.objects.filter(public=False).count()
            ),
            "algorithm_jobs": Job.objects.count(),
            "reader_studies": ReaderStudy.objects.count(),
            "questions": Question.objects.count(),
            "answers": Answer.objects.count(),
            "workstations": Workstation.objects.count(),
            "workstation_sessions": Session.objects.count(),
            "total_session_duration": (
                Session.objects.aggregate(Sum("maximum_duration"))[
                    "maximum_duration__sum"
                ]
            ),
        }

        context.update(extra)

        return context


workstation_sessions_active = prometheus_client.Gauge(
    "grandchallenge_workstation_sessions_active_total",
    "The number of active workstation sessions",
)
algorithm_jobs_pending = prometheus_client.Gauge(
    "grandchallenge_algorithm_jobs_pending_total",
    "The number of pending algorithm jobs",
)
algorithm_jobs_active = prometheus_client.Gauge(
    "grandchallenge_algorithm_jobs_active_total",
    "The number of active algorithm jobs",
)
evaluation_jobs_pending = prometheus_client.Gauge(
    "grandchallenge_evaluation_jobs_pending_total",
    "The number of pending evaluation jobs",
)
evaluation_jobs_active = prometheus_client.Gauge(
    "grandchallenge_evaluation_jobs_active_total",
    "The number of active evaluation jobs",
)

build_version = prometheus_client.Info(
    "grandchallenge_build_version", "The build version"
)
build_version.info({"grandchallenge_commit_id": settings.COMMIT_ID})


class MetricsAPIView(APIView):
    renderer_classes = [PrometheusRenderer]
    permission_classes = [IsAdminUser]

    def get(self, request, format=None):
        workstation_sessions_active.set(
            Session.objects.filter(status=Session.STARTED).count()
        )
        algorithm_jobs_pending.set(
            Job.objects.filter(status=Job.PENDING).count()
        )
        algorithm_jobs_active.set(
            Job.objects.filter(status=Job.STARTED).count()
        )
        evaluation_jobs_pending.set(
            EvaluationJob.objects.filter(status=Job.PENDING).count()
        )
        evaluation_jobs_active.set(
            EvaluationJob.objects.filter(status=Job.STARTED).count()
        )

        registry = prometheus_client.REGISTRY
        metrics = prometheus_client.generate_latest(registry)
        return Response(
            metrics, content_type=prometheus_client.CONTENT_TYPE_LATEST
        )
