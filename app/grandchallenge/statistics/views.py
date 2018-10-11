from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import TemplateView

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.evaluation.models import Submission, Result


class StatisticsDetail(UserIsStaffMixin, TemplateView):
    template_name = "statistics/statistics_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        days = 30

        User = get_user_model()

        time_period = timezone.now() - timedelta(days=days)

        open_challenges = Challenge.objects.filter(hidden=False)

        extra = {
            "days": days,
            "number_of_users": User.objects.count(),
            "new_users_period": User.objects.filter(
                date_joined__gt=time_period
            ).count(),
            "logged_in_period": User.objects.filter(
                last_login__gt=time_period
            ).count(),
            "open_challenges": open_challenges.count(),
            "hidden_challenges": Challenge.objects.filter(hidden=True).count(),
            "submissions": Submission.objects.count(),
            "submissions_period": Submission.objects.filter(
                created__gt=time_period
            ).count(),
            "mp_group": Group.objects.filter(
                participants_of_challenge__in=open_challenges
            )
            .annotate(num_users=Count("user"))
            .order_by("-num_users")
            .first(),
            "mp_challenge_registrations_period": open_challenges.annotate(
                num_registrations_period=Count(
                    "registrationrequest", filter=Q(created__gt=time_period)
                )
            )
            .filter(num_registrations_period__gt=0)
            .order_by("-num_registrations_period")
            .first(),
            "mp_challenge_submissions": open_challenges.annotate(
                num_submissions=Count("submission")
            )
            .order_by("-num_submissions")
            .first(),
            "mp_challenge_submissions_period": open_challenges.annotate(
                num_submissions_period=Count(
                    "submission", filter=Q(created__gt=time_period)
                )
            )
            .filter(num_submissions_period__gt=0)
            .order_by("-num_submissions_period")
            .first(),
            "latest_result": Result.objects.filter(
                published=True, challenge__hidden=False
            )
            .order_by("-created")
            .first(),
            "using_auto_eval": Challenge.objects.filter(
                use_evaluation=True
            ).count(),
        }

        context.update(extra)

        return context
