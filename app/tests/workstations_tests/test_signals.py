import pytest
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from tests.factories import SessionFactory, UserFactory


@pytest.mark.django_db
def test_session_stopped_on_user_logout(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    u1, u2 = UserFactory.create_batch(2)

    s1, s2 = SessionFactory(creator=u1), SessionFactory(creator=u2)

    s1.status = s1.STARTED
    s1.save()

    s2.status = s2.STARTED
    s2.save()

    client.force_login(u1)

    with capture_on_commit_callbacks(execute=True):
        client.post("/accounts/logout/", data={"next": "/"})

    s1.refresh_from_db()
    s2.refresh_from_db()

    assert s1.status == s1.STOPPED
    assert s2.status == s2.STARTED
