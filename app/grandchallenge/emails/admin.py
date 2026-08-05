from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.forms import ModelForm

from grandchallenge.core.widgets import MarkdownEditorAdminWidget
from grandchallenge.emails.models import Email, RawEmail
from grandchallenge.emails.tasks import send_bulk_email
from grandchallenge.emails.utils import SendActionChoices


def schedule_emails(modeladmin, queryset, request, action):
    emails = queryset.filter(status=Email.EmailStatusChoices.INITIALIZED)

    if emails:
        for email in emails:
            send_bulk_email.execute_on_commit(action=action, email_pk=email.pk)
            email.status = Email.EmailStatusChoices.QUEUED
            email.save()
    else:
        modeladmin.message_user(
            request,
            "The emails you selected have already been sent.",
            messages.WARNING,
        )


@admin.action(
    description="Initialize Succeeded Emails",
    permissions=("change",),
)
def initialize_succeeded_emails(modeladmin, request, queryset):
    queryset.filter(status=Email.EmailStatusChoices.SUCCEEDED).update(
        status=Email.EmailStatusChoices.INITIALIZED, sent_at=None
    )


class EmailAdminForm(ModelForm):
    class Meta:
        widgets = {"body": MarkdownEditorAdminWidget}


@admin.register(Email)
class EmailAdmin(ModelAdmin):
    list_display = ("subject", "status", "sent_at")
    readonly_fields = (
        "status",
        "sent_at",
    )
    actions = (*SendActionChoices, initialize_succeeded_emails)
    form = EmailAdminForm

    @admin.action(description="Send to mailing list", permissions=["change"])
    def send_to_mailing_list(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.MAILING_LIST,
        )

    @admin.action(description="Send to staff", permissions=["change"])
    def send_to_staff(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.STAFF,
        )

    @admin.action(
        description="Send to challenge admins", permissions=["change"]
    )
    def send_to_challenge_admins(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.CHALLENGE_ADMINS,
        )

    @admin.action(
        description="Send to reader study editors", permissions=["change"]
    )
    def send_to_readerstudy_editors(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.READER_STUDY_EDITORS,
        )

    @admin.action(
        description="Send to algorithm editors", permissions=["change"]
    )
    def send_to_algorithm_editors(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.ALGORITHM_EDITORS,
        )


@admin.register(RawEmail)
class RawEmailAdmin(ModelAdmin):
    list_display = ("pk", "created", "modified", "status")
    list_filter = ("status",)
    readonly_fields = ("created", "message", "status")
    search_fields = ("message",)
