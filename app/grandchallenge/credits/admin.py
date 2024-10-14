from dateutil.relativedelta import relativedelta
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.db.models import Sum
from django.utils.timezone import now

from grandchallenge.algorithms.models import Job
from grandchallenge.core.templatetags.costs import millicents_to_euro
from grandchallenge.credits.models import Credit


@admin.register(Credit)
class CreditAdmin(ModelAdmin):
    list_display = ("user", "credits")
    autocomplete_fields = ("user",)
    search_fields = ("user__username", "user__email")
    fields = (
        "user",
        "credits",
        "credits_consumed_past_month",
        "compute_costs_past_month",
    )
    readonly_fields = (
        "user",
        "credits_consumed_past_month",
        "compute_costs_past_month",
    )

    def credits_consumed_past_month(self, obj):
        return Job.objects.credits_consumed_past_month(user=obj.user)["total"]

    def compute_costs_past_month(self, obj):
        return millicents_to_euro(
            Job.objects.filter(
                creator=obj.user,
                created__gt=now() - relativedelta(months=1),
            ).aggregate(
                total=Sum("compute_cost_euro_millicents", default=0),
            )[
                "total"
            ]
        )
