import pytest
from dateutil.utils import today
from django.core import mail

from grandchallenge.pages.models import Page
from tests.factories import PageFactory


@pytest.mark.django_db
def test_email_generated_on_change(settings):
    settings.MANAGERS = [("Manager", "manager@example.org")]

    page = PageFactory(content_markdown="hello world!")

    def update_content_markdown(content_markdown):
        p = Page.objects.get(pk=page.pk)
        p.content_markdown = content_markdown
        p.save()
        return p

    page = update_content_markdown(
        page.content_markdown + "Challenge still active."
    )

    # No emails should be generated if the challenge is active
    assert len(mail.outbox) == 0

    page.challenge.is_active_until = today().date()
    page.challenge.save()

    page = update_content_markdown(page.content_markdown + "New Stuff!")

    assert len(mail.outbox) == 1

    report_email = mail.outbox.pop()
    assert (
        "-hello world!Challenge still active.\n+hello world!Challenge still active.New Stuff!"
        in report_email.body
    )

    page = update_content_markdown(f"**{page.content_markdown}**")

    # No emails should be generated without content change
    assert len(mail.outbox) == 0
