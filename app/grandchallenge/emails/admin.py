from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.db.transaction import on_commit
from django.forms import ModelForm

from grandchallenge.core.widgets import MarkdownEditorAdminWidget
from grandchallenge.emails.models import Email, RawEmail
from grandchallenge.emails.tasks import send_bulk_email
from grandchallenge.emails.utils import SendActionChoices


def schedule_emails(modeladmin, queryset, request, action):
    emails = queryset.filter(sent=False)
    if emails:
        for email in emails:
            send_admin_emails = send_bulk_email.signature(
                kwargs={"action": action, "email_pk": email.pk}, immutable=True
            )
            on_commit(send_admin_emails.apply_async)
    else:
        modeladmin.message_user(
            request,
            "The emails you selected have already been sent.",
            messages.WARNING,
        )


class EmailAdminForm(ModelForm):
    class Meta:
        model = Email
        widgets = {"body": MarkdownEditorAdminWidget}
        exclude = ()


@admin.register(Email)
class EmailAdmin(ModelAdmin):
    list_display = ("subject", "sent", "sent_at")
    actions = [*SendActionChoices]
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
    list_display = ("pk", "created", "sent_at", "errored")
    list_filter = ("errored",)
    readonly_fields = ("created", "message")
    search_fields = ("message",)
