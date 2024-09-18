import pytest
from dateutil.utils import today
from django.core import mail

from grandchallenge.pages.models import Page
from tests.factories import PageFactory


@pytest.mark.django_db
def test_email_generated_on_change(settings):
    settings.MANAGERS = [("Manager", "manager@example.org")]

    page = PageFactory(html="hello world!")

    def update_html(html):
        p = Page.objects.get(pk=page.pk)
        p.html = html
        p.save()
        return p

    page = update_html(page.html + "Challenge still active.")

    # No emails should be generated if the challenge is active
    assert len(mail.outbox) == 0

    page.challenge.is_active_until = today().date()
    page.challenge.save()

    page = update_html(page.html + "New Stuff!")

    assert len(mail.outbox) == 1

    report_email = mail.outbox.pop()
    assert (
        "-hello world!Challenge still active.\n+hello world!Challenge still active.New Stuff!"
        in report_email.body
    )

    page = update_html(f"<b>{page.html}</b>")

    # No emails should be generated without content change
    assert len(mail.outbox) == 0
