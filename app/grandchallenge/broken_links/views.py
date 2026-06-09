from datetime import timedelta

from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count
from django.utils import timezone
from django.views.generic import TemplateView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.broken_links.models import BrokenLink
from grandchallenge.subdomains.utils import reverse_lazy


class BrokenLinkDashboard(
    LoginRequiredMixin, UserPassesTestMixin, TemplateView
):
    template_name = "broken_links/dashboard.html"
    login_url = reverse_lazy("account_login")
    raise_exception = True

    DAYS_CHOICES = (
        1,
        7,
        30,
        90,
    )

    def test_func(self):
        return self.request.user.is_staff

    def get_days(self):
        try:
            days = int(self.request.GET.get("days", 0))
        except (ValueError, TypeError):
            days = 0

        return days if days in self.DAYS_CHOICES else 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        limit = 25
        days = self.get_days()

        queryset = BrokenLink.objects.all()
        if days:
            since = timezone.now() - timedelta(days=days)
            queryset = queryset.filter(created__gte=since)

        context["top_paths"] = (
            queryset.values("path")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )
        context["top_referers"] = (
            queryset.values("referer")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )
        context["top_internal_paths"] = (
            queryset.filter(is_internal=True)
            .values("path")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )
        context["total_count"] = queryset.count()
        context["internal_count"] = queryset.filter(is_internal=True).count()
        context["days"] = days
        context["days_choices"] = self.DAYS_CHOICES

        return context
