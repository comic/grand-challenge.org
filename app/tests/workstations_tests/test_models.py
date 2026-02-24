from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import ProtectedError

from grandchallenge.workstations.models import Session, Workstation
from tests.factories import (
    SessionFactory,
    UserFactory,
    WorkstationFactory,
    WorkstationImageFactory,
)
from tests.workstations_tests.factories import FeedbackFactory


def stop_all_sessions():
    sessions = Session.objects.all()
    for s in sessions:
        s.stop()


@pytest.mark.django_db
def test_session_environ():
    s = SessionFactory()
    env = s.environment

    assert env["GRAND_CHALLENGE_API_ROOT"] == "https://testserver/api/v1/"
    assert "Bearer " in env["GRAND_CHALLENGE_AUTHORIZATION"]
    assert env["WORKSTATION_SESSION_ID"] == str(s.pk)
    assert "WORKSTATION_SENTRY_DSN" in env


@pytest.mark.django_db
def test_session_auth_token():
    s = SessionFactory()

    # Calling environment should generate an auth token for the creator
    assert s.auth_token is None

    _ = s.environment

    expected_duration = (
        s.created
        + timedelta(minutes=settings.WORKSTATIONS_GRACE_MINUTES)
        + timedelta(seconds=settings.WORKSTATIONS_SESSION_DURATION_LIMIT)
    )

    assert s.auth_token.user == s.creator
    assert abs(s.auth_token.expiry - expected_duration) < timedelta(seconds=10)

    # old tokens should be deleted
    old_pk = s.auth_token.pk

    _ = s.environment

    assert s.auth_token.pk != old_pk


@pytest.mark.django_db
def test_workstation_ready(
    http_image, settings, django_capture_on_commit_callbacks
):
    # Execute celery tasks in place
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # Do not execute the callbacks as the image should not be ready
    wsi = WorkstationImageFactory(image__from_path=http_image)
    assert wsi.is_manifest_valid is None
    assert wsi.can_execute is False

    with django_capture_on_commit_callbacks(execute=True):
        s = SessionFactory(workstation_image=wsi)

    s.refresh_from_db()
    assert s.status == s.FAILED


@pytest.mark.django_db
def test_group_deletion():
    ws = WorkstationFactory()
    users_group = ws.users_group
    editors_group = ws.editors_group

    assert users_group
    assert editors_group

    Workstation.objects.filter(pk__in=[ws.pk]).delete()

    with pytest.raises(ObjectDoesNotExist):
        users_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        editors_group.refresh_from_db()


@pytest.mark.django_db
@pytest.mark.parametrize("group", ["users_group", "editors_group"])
def test_group_deletion_reverse(group):
    ws = WorkstationFactory()
    users_group = ws.users_group
    editors_group = ws.editors_group

    assert users_group
    assert editors_group

    with pytest.raises(ProtectedError):
        getattr(ws, group).delete()


@pytest.mark.django_db
def test_all_regions_are_in_settings(settings):
    for region in Session.Region.values:
        assert region in settings.WORKSTATIONS_RENDERING_SUBDOMAINS
        assert region in settings.DISALLOWED_CHALLENGE_NAMES


@pytest.mark.django_db
def test_staff_email_for_new_feedback():
    staff = UserFactory(is_staff=True)
    user = UserFactory()

    assert len(mail.outbox) == 0

    _ = FeedbackFactory()

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [staff.email]
    assert mail.outbox[0].to != [user.email]
    assert "New Session Feedback" in mail.outbox[0].subject


@pytest.mark.django_db
def test_extra_env_vars():
    session = Session(
        extra_env_vars=[
            {"name": "TEST", "value": "12345"},
            {
                "name": "GRAND_CHALLENGE_API_ROOT",
                "value": "should not be overwritten",
            },
        ],
        id="9863c19d-879f-411e-91da-eb5bcdcc1e41",
    )

    assert session.environment == {
        "CIRRUS_KEEP_ALIVE_METHOD": "old",
        "GRAND_CHALLENGE_API_ROOT": "https://testserver/api/v1/",
        "TEST": "12345",
        "WORKSTATION_SENTRY_DSN": "",
        "WORKSTATION_SESSION_ID": "9863c19d-879f-411e-91da-eb5bcdcc1e41",
        "INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS": "null",
        "AWS_DEFAULT_REGION": "eu-nl-1",
        "WORKSTATIONS_MAX_CONCURRENT_API_REQUESTS": str(
            settings.WORKSTATIONS_MAX_CONCURRENT_API_REQUESTS
        ),
    }


@pytest.fixture
def running_session():
    return SessionFactory(
        status=Session.RUNNING,
        host_address="192.168.1.1",
        http_port=40000,
        websocket_port=40001,
    )


@pytest.mark.django_db
def test_clean_passes_for_valid_session(running_session):
    session = SessionFactory(
        status=Session.RUNNING,
        host_address="192.168.1.1",
        http_port=40002,
        websocket_port=40003,
    )
    session.clean()  # should not raise


@pytest.mark.django_db
def test_clean_raises_if_http_port_in_use(running_session):
    session = SessionFactory(
        status=Session.RUNNING,
        host_address="192.168.1.1",
        http_port=40000,  # conflicts with running_session.http_port
        websocket_port=40003,
    )
    with pytest.raises(ValidationError, match="http_port"):
        session.clean()


@pytest.mark.django_db
def test_clean_raises_if_websocket_port_in_use(running_session):
    session = SessionFactory(
        status=Session.RUNNING,
        host_address="192.168.1.1",
        http_port=40002,
        websocket_port=40001,  # conflicts with running_session.websocket_port
    )
    with pytest.raises(ValidationError, match="websocket_port"):
        session.clean()


@pytest.mark.django_db
def test_clean_raises_if_http_port_matches_other_websocket_port(
    running_session,
):
    session = SessionFactory(
        status=Session.RUNNING,
        host_address="192.168.1.1",
        http_port=40001,  # conflicts with running_session.websocket_port
        websocket_port=40002,
    )
    with pytest.raises(ValidationError, match="http_port"):
        session.clean()


@pytest.mark.django_db
def test_clean_raises_if_websocket_port_matches_other_http_port(
    running_session,
):
    session = SessionFactory(
        status=Session.RUNNING,
        host_address="192.168.1.1",
        http_port=40002,
        websocket_port=40000,  # conflicts with running_session.http_port
    )
    with pytest.raises(ValidationError, match="websocket_port"):
        session.clean()


@pytest.mark.django_db
def test_clean_raises_if_ports_identical():
    session = SessionFactory(
        status=Session.RUNNING,
        host_address="192.168.1.1",
        http_port=40000,
        websocket_port=40000,
    )
    with pytest.raises(ValidationError):
        session.clean()


@pytest.mark.django_db
def test_clean_skips_validation_if_not_started(running_session):
    session = SessionFactory(
        status=Session.QUEUED,
        host_address="192.168.1.1",
        http_port=40000,  # would conflict if RUNNING
        websocket_port=40001,
    )
    session.clean()  # should not raise


@pytest.mark.django_db
def test_clean_excludes_self(running_session):
    running_session.clean()  # should not conflict with itself
