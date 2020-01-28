import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Result, Submission
from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy
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
                Algorithm.objects.filter(visible_to_public=True).count()
            ),
            "hidden_algorithms": (
                Algorithm.objects.filter(visible_to_public=False).count()
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
