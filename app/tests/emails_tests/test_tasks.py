import pytest
from django.contrib.sites.models import Site
from django.core import mail

from grandchallenge.emails.tasks import get_receivers, send_bulk_email
from grandchallenge.emails.utils import SendActionChoices
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.emails_tests.factories import EmailFactory
from tests.factories import ChallengeFactory, UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.parametrize(
    "factory,action",
    [
        (None, SendActionChoices.MAILING_LIST),
        (None, SendActionChoices.STAFF),
        (ChallengeFactory, SendActionChoices.CHALLENGE_ADMINS),
        (AlgorithmFactory, SendActionChoices.ALGORITHM_EDITORS),
        (ReaderStudyFactory, SendActionChoices.READER_STUDY_EDITORS),
    ],
)
@pytest.mark.django_db
def test_get_receivers(factory, action):
    u1, u2, u3, u4 = UserFactory.create_batch(4)
    u2.is_active = False
    u2.save()
    for user in [u1, u2]:
        user.user_profile.receive_newsletter = True
        user.user_profile.save()
        if action == SendActionChoices.STAFF:
            user.is_staff = True
            user.save()

    if factory == ChallengeFactory:
        obj = factory(creator=u1)
        obj2 = factory(creator=u2)
    elif factory in [AlgorithmFactory, ReaderStudyFactory]:
        obj = factory()
        obj2 = factory()
        obj.add_editor(u1)
        obj2.add_editor(u2)

    receivers = get_receivers(action)

    assert len(receivers) == 1
    for user in [u1]:
        assert user in receivers
    for user in [u2, u3, u4]:
        assert user not in receivers


@pytest.mark.django_db
def test_email_content(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    email = EmailFactory(subject="Test email", body="Test content")
    u1, u2 = UserFactory.create_batch(2)
    for user in [u1, u2]:
        user.user_profile.receive_newsletter = True
        user.user_profile.save()

    assert len(mail.outbox) == 0

    send_bulk_email(action=SendActionChoices.MAILING_LIST, email_pk=email.pk)

    assert len(mail.outbox) == 2
    email.refresh_from_db()
    assert email.sent

    for m in mail.outbox:
        assert (
            m.subject
            == f"[{Site.objects.get_current().domain.lower()}] Test email"
        )
        assert "Test content" in m.body
        if m.to == [u1.email]:
            assert reverse(
                "profile-update", kwargs={"username": u1.username}
            ) in str(m.alternatives)
        else:
            assert reverse(
                "profile-update", kwargs={"username": u2.username}
            ) in str(m.alternatives)

    # check that email sending task is idempotent
    mail.outbox.clear()
    send_bulk_email(action=SendActionChoices.MAILING_LIST, email_pk=email.pk)
    assert len(mail.outbox) == 0
