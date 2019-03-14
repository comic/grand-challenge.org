from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count
from django.utils import timezone
from django.views.generic import TemplateView

from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Submission, Result


class StatisticsDetail(TemplateView):
    template_name = "statistics/statistics_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        days = 30
        max_num_results = 10

        User = get_user_model()

        time_period = timezone.now() - timedelta(days=days)

        public_challenges = Challenge.objects.filter(hidden=False)

        extra = {
            "days": days,
            "max_num_results": max_num_results,
            "number_of_users": User.objects.count(),
            "new_users_period": User.objects.filter(
                date_joined__gt=time_period
            ).count(),
            "logged_in_period": User.objects.filter(
                last_login__gt=time_period
            ).count(),
            "public_challenges": public_challenges.count(),
            "hidden_challenges": Challenge.objects.filter(hidden=True).count(),
            "submissions": Submission.objects.count(),
            "submissions_period": Submission.objects.filter(
                created__gt=time_period
            ).count(),
            "latest_public_challenge": public_challenges.order_by(
                "-created"
            ).first(),
            "mp_group": Group.objects.filter(
                participants_of_challenge__in=public_challenges
            )
            .annotate(num_users=Count("user"))
            .order_by("-num_users")
            .first(),
            "challenge_registrations_period": public_challenges.filter(
                registrationrequest__created__gt=time_period
            )
            .annotate(num_registrations_period=Count("registrationrequest"))
            .order_by("-num_registrations_period")[:max_num_results],
            "mp_challenge_submissions": public_challenges.annotate(
                num_submissions=Count("submission")
            )
            .order_by("-num_submissions")
            .first(),
            "challenge_submissions_period": public_challenges.filter(
                submission__created__gt=time_period
            )
            .annotate(num_submissions_period=Count("submission"))
            .order_by("-num_submissions_period")[:max_num_results],
            "latest_result": Result.objects.filter(
                published=True, job__submission__challenge__hidden=False
            )
            .order_by("-created")
            .first(),
            "using_auto_eval": Challenge.objects.filter(
                use_evaluation=True
            ).count(),
        }

        context.update(extra)

        return context
