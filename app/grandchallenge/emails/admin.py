from django.contrib import admin, messages
from django.db.transaction import on_commit
from django.utils.timezone import now
from django.utils.translation import ngettext
from markdownx.admin import MarkdownxModelAdmin

from grandchallenge.emails.models import Email
from grandchallenge.emails.tasks import send_bulk_email
from grandchallenge.emails.utils import SendActionChoices


def schedule_emails(modeladmin, queryset, request, action):
    emails = queryset.filter(sent=False)
    if emails:
        for email in emails:
            send_admin_emails = send_bulk_email.signature(
                kwargs={
                    "action": action,
                    "subject": email.subject,
                    "body": email.body,
                },
                immutable=True,
            )
            on_commit(send_admin_emails.apply_async)

        updated = emails.update(sent=True, sent_at=now())

        modeladmin.message_user(
            request,
            ngettext(
                f"%d email was successfully sent to {action.label.lower()}.",
                f"%d emails were successfully sent to {action.label.lower()}.",
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
    actions = [*SendActionChoices]

    @admin.action(description="Send to mailing list")
    def send_to_mailing_list(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.MAILING_LIST,
        )

    @admin.action(description="Send to staff")
    def send_to_staff(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.STAFF,
        )

    @admin.action(description="Send to challenge admins")
    def send_to_challenge_admins(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.CHALLENGE_ADMINS,
        )

    @admin.action(description="Send to reader study editors")
    def send_to_readerstudy_editors(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.READER_STUDY_EDITORS,
        )

    @admin.action(description="Send to algorithm editors")
    def send_to_algorithm_editors(self, request, queryset):
        schedule_emails(
            modeladmin=self,
            queryset=queryset,
            request=request,
            action=SendActionChoices.ALGORITHM_EDITORS,
        )


admin.site.register(Email, EmailAdmin)
