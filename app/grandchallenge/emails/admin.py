from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.utils.translation import ngettext
from markdownx.admin import MarkdownxModelAdmin

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.challenges.models import Challenge
from grandchallenge.emails.models import Email
from grandchallenge.emails.tasks import send_bulk_email
from grandchallenge.reader_studies.models import ReaderStudy


def schedule_emails(modeladmin, queryset, request, receivers, action_string):
    emails = queryset.filter(sent=False)
    if emails:
        for email in emails:
            send_bulk_email(receivers, email.subject, email.body)

        updated = emails.update(sent=True, sent_at=now())
        modeladmin.message_user(
            request,
            ngettext(
                f"%d email was successfully sent to {action_string}.",
                f"%d emails were successfully sent to {action_string}.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )
    else:
        modeladmin.message_user(
            request,
            "The emails you selected have already been sent.",
            messages.WARNING,
        )


class EmailAdmin(MarkdownxModelAdmin):
    list_display = ("subject", "sent", "sent_at")
    actions = [
        "send_to_mailing_list",
        "send_to_staff",
        "send_to_challenge_admins",
        "send_to_readerstudy_editors",
        "send_to_algorithm_editors",
    ]

    @admin.action(description="Send to mailing list")
    def send_to_mailing_list(self, request, queryset):
        receivers = [
            user
            for user in get_user_model().objects.filter(
                user_profile__receive_newsletter=True
            )
        ]
        schedule_emails(self, queryset, request, receivers, "mailing list")

    @admin.action(description="Send to staff")
    def send_to_staff(self, request, queryset):
        receivers = [
            user for user in get_user_model().objects.filter(is_staff=True)
        ]
        schedule_emails(self, queryset, request, receivers, "staff")

    @admin.action(description="Send to challenge admins")
    def send_to_challenge_admins(self, request, queryset):
        receivers = (
            user
            for challenge in Challenge.objects.all()
            for user in challenge.admins_group.user_set.all()
        )
        schedule_emails(self, queryset, request, receivers, "challenge admins")

    @admin.action(description="Send to reader study editors")
    def send_to_readerstudy_editors(self, request, queryset):
        receivers = (
            user
            for rs in ReaderStudy.objects.all()
            for user in rs.editors_group.user_set.all()
        )
        schedule_emails(
            self, queryset, request, receivers, "reader study editors"
        )

    @admin.action(description="Send to algorithm editors")
    def send_to_algorithm_editors(self, request, queryset):
        receivers = (
            user
            for algorithm in Algorithm.objects.all()
            for user in algorithm.editors_group.user_set.all()
        )
        schedule_emails(
            self, queryset, request, receivers, "algorithm editors"
        )


admin.site.register(Email, EmailAdmin)
