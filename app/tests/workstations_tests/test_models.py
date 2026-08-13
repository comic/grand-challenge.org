from datetime import datetime, timedelta, timezone

import pytest
from django.core import mail
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import ProtectedError

from grandchallenge.algorithms.models import EndpointStatusChoices
from grandchallenge.components.backends.amazon_sagemaker_endpoint import (
    AmazonSageMakerEndpointOrchestrator,
)
from grandchallenge.components.tasks import stop_service
from grandchallenge.workstations.models import Session, Workstation
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    EndpointFactory,
    ReaderStudyAlgorithmImplementationFactory,
)
from tests.evaluation_tests.test_permissions import get_users_with_set_perms
from tests.factories import SessionFactory, UserFactory, WorkstationFactory
from tests.reader_studies_tests.factories import (
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.workstations_tests.factories import FeedbackFactory


@pytest.mark.django_db
def test_session_environ():
    s = SessionFactory()
    env = s.environment

    assert env["GRAND_CHALLENGE_API_ROOT"] == "https://testserver/api/v1/"
    assert env["WORKSTATION_SESSION_ID"] == str(s.pk)
    assert "WORKSTATION_SENTRY_DSN" in env


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
def test_extra_env_vars(settings):
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
        "AWS_DEFAULT_REGION": "eu-central-1",
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


@pytest.mark.django_db
def test_session_updates_correct_endpoints():
    user = UserFactory()
    algorithm_image = AlgorithmImageFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    implementation = ReaderStudyAlgorithmImplementationFactory(
        algorithm=algorithm_image.algorithm
    )
    reader_study = ReaderStudyFactory()
    question = QuestionFactory(reader_study=reader_study)
    question.algorithms.add(implementation)

    session = SessionFactory(creator=user)
    reader_study.workstation_sessions.add(session)

    user_implementation_endpoint = EndpointFactory(
        creator=user, algorithm_image=algorithm_image
    )
    other_user_implementation_endpoint = EndpointFactory(
        algorithm_image=algorithm_image
    )
    users_other_endpoint = EndpointFactory(creator=user)
    other_endpoint = EndpointFactory()

    user_implementation_endpoint_inactive = EndpointFactory(
        creator=user,
        algorithm_image=algorithm_image,
        status=EndpointStatusChoices.STOPPED,
    )
    other_user_implementation_endpoint_inactive = EndpointFactory(
        algorithm_image=algorithm_image, status=EndpointStatusChoices.STOPPED
    )
    users_other_endpoint_inactive = EndpointFactory(
        creator=user, status=EndpointStatusChoices.STOPPED
    )
    other_endpoint_inactive = EndpointFactory(
        status=EndpointStatusChoices.STOPPED
    )

    new_duration = timedelta(minutes=1337)

    session.maximum_duration = new_duration
    session.save()

    user_implementation_endpoint.refresh_from_db()
    other_user_implementation_endpoint.refresh_from_db()
    users_other_endpoint.refresh_from_db()
    other_endpoint.refresh_from_db()
    user_implementation_endpoint_inactive.refresh_from_db()
    other_user_implementation_endpoint_inactive.refresh_from_db()
    users_other_endpoint_inactive.refresh_from_db()
    other_endpoint_inactive.refresh_from_db()

    assert user_implementation_endpoint.maximum_duration == new_duration
    assert other_user_implementation_endpoint.maximum_duration == timedelta(
        minutes=10
    )
    assert users_other_endpoint.maximum_duration == timedelta(minutes=10)
    assert other_endpoint.maximum_duration == timedelta(minutes=10)
    assert user_implementation_endpoint_inactive.maximum_duration == timedelta(
        minutes=10
    )
    assert (
        other_user_implementation_endpoint_inactive.maximum_duration
        == timedelta(minutes=10)
    )
    assert users_other_endpoint_inactive.maximum_duration == timedelta(
        minutes=10
    )
    assert other_endpoint_inactive.maximum_duration == timedelta(minutes=10)


@pytest.mark.django_db
def test_session_stopped_schedules_stop_for_correct_endpoints(
    settings, django_capture_on_commit_callbacks, mocker
):
    settings.LAMBDA_TASKS_EAGER = True

    user = UserFactory()
    algorithm_image = AlgorithmImageFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    implementation = ReaderStudyAlgorithmImplementationFactory(
        algorithm=algorithm_image.algorithm
    )
    reader_study = ReaderStudyFactory()
    question = QuestionFactory(reader_study=reader_study)
    question.algorithms.add(implementation)

    session = SessionFactory(creator=user)
    reader_study.workstation_sessions.add(session)

    user_implementation_endpoint = EndpointFactory(
        creator=user, algorithm_image=algorithm_image
    )
    other_user_implementation_endpoint = EndpointFactory(
        algorithm_image=algorithm_image
    )
    users_other_endpoint = EndpointFactory(creator=user)
    other_endpoint = EndpointFactory()

    mocker.patch.object(
        AmazonSageMakerEndpointOrchestrator,
        "deprovision",
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.status = Session.STOPPED
        session.save()

    user_implementation_endpoint.refresh_from_db()
    other_user_implementation_endpoint.refresh_from_db()
    users_other_endpoint.refresh_from_db()
    other_endpoint.refresh_from_db()

    assert user_implementation_endpoint.status == EndpointStatusChoices.STOPPED
    assert (
        other_user_implementation_endpoint.status
        != EndpointStatusChoices.STOPPED
    )
    assert users_other_endpoint.status != EndpointStatusChoices.STOPPED
    assert other_endpoint.status != EndpointStatusChoices.STOPPED


@pytest.mark.django_db
def test_session_claimed_at():
    session = SessionFactory(creator=None)

    assert session.claimed_at is None

    session.creator = UserFactory()
    session.save()

    session.refresh_from_db()
    assert session.claimed_at is not None


@pytest.mark.django_db
def test_session_perms_assigned():
    session = SessionFactory(creator=None)

    assert get_users_with_set_perms(session) == {}

    session.creator = UserFactory()
    session.save()

    assert get_users_with_set_perms(session) == {
        session.creator: {"view_session", "change_session"}
    }


@pytest.mark.django_db
def test_user_cannot_change():
    session = SessionFactory(creator=UserFactory())

    assert get_users_with_set_perms(session) == {
        session.creator: {"view_session", "change_session"}
    }

    session.creator = UserFactory()

    with pytest.raises(ValidationError, match="You cannot change the creator"):
        session.save()


@pytest.mark.django_db
def test_expires_at_takes_into_account_claimed_at(mocker):
    fixed_now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    mocker.patch(
        "grandchallenge.workstations.models.now",
        return_value=fixed_now,
    )

    yesterday = fixed_now - timedelta(days=1)

    session = SessionFactory(claimed_at=yesterday)

    assert session.expires_at == yesterday + timedelta(minutes=10)

    stop_service(**session.task_kwargs)

    assert session.session_utilization.duration == timedelta(days=1)
