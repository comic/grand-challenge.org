from datetime import timedelta

import pytest
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ProtectedError
from django_capture_on_commit_callbacks import capture_on_commit_callbacks
from docker.errors import NotFound
from knox.models import AuthToken

from grandchallenge.components.tasks import stop_expired_services
from grandchallenge.workstations.models import Session, Workstation
from tests.factories import (
    SessionFactory,
    WorkstationFactory,
    WorkstationImageFactory,
)


def stop_all_sessions():
    sessions = Session.objects.all()
    for s in sessions:
        s.stop()


@pytest.mark.django_db
@pytest.mark.parametrize("debug", [True, False])
def test_session_environ(settings, debug):
    settings.DEBUG = debug

    s = SessionFactory()
    env = s.environment

    assert env["GRAND_CHALLENGE_API_ROOT"] == "https://testserver/api/v1/"
    assert "Bearer " in env["GRAND_CHALLENGE_AUTHORIZATION"]
    assert env["WORKSTATION_SESSION_ID"] == str(s.pk)
    assert "WORKSTATION_SENTRY_DSN" in env

    if debug:
        assert "GRAND_CHALLENGE_UNSAFE" in env
    else:
        assert "GRAND_CHALLENGE_UNSAFE" not in env


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
def test_session_start(http_image, docker_client, settings):
    path, sha256 = http_image

    wsi = WorkstationImageFactory(
        image__from_path=path, image_sha256=sha256, ready=True
    )

    # Execute the celery in place
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with capture_on_commit_callbacks(execute=True):
        s = SessionFactory(workstation_image=wsi)

    try:
        assert s.service.container

        s.refresh_from_db()
        assert s.status == s.STARTED

        container = s.service.container

        assert container.labels["traefik.enable"] == "true"
        assert container.labels[
            f"traefik.http.services.{s.hostname}-http.loadbalancer.server.port"
        ] == str(s.workstation_image.http_port)
        assert container.labels[
            f"traefik.http.services.{s.hostname}-websocket.loadbalancer.server.port"
        ] == str(s.workstation_image.websocket_port)

        networks = container.attrs.get("NetworkSettings")["Networks"]
        assert len(networks) == 1
        assert settings.WORKSTATIONS_NETWORK_NAME in networks

        with capture_on_commit_callbacks(execute=True):
            s.user_finished = True
            s.save()

        with pytest.raises(NotFound):
            # noinspection PyStatementEffect
            s.service.container
    finally:
        stop_all_sessions()


@pytest.mark.django_db
def test_correct_session_stopped(http_image, docker_client, settings):
    path, sha256 = http_image

    wsi = WorkstationImageFactory(
        image__from_path=path, image_sha256=sha256, ready=True
    )

    # Execute the celery in place
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    try:
        with capture_on_commit_callbacks(execute=True):
            s1, s2 = (
                SessionFactory(workstation_image=wsi),
                SessionFactory(workstation_image=wsi),
            )

        assert s1.service.container
        assert s2.service.container

        s2.refresh_from_db()
        auth_token_pk = s2.auth_token.pk

        with capture_on_commit_callbacks(execute=True):
            s2.user_finished = True
            s2.save()

        assert s1.service.container
        with pytest.raises(NotFound):
            # noinspection PyStatementEffect
            s2.service.container

        with pytest.raises(ObjectDoesNotExist):
            # auth token should be deleted when the service is stopped
            AuthToken.objects.get(pk=auth_token_pk)

    finally:
        stop_all_sessions()


@pytest.mark.django_db
def test_session_cleanup(http_image, docker_client, settings):
    path, sha256 = http_image

    wsi = WorkstationImageFactory(
        image__from_path=path, image_sha256=sha256, ready=True
    )

    # Execute the celery in place
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    default_region = "eu-nl-1"

    try:
        with capture_on_commit_callbacks(execute=True):
            s1, s2, s3 = (
                SessionFactory(workstation_image=wsi, region=default_region),
                SessionFactory(
                    workstation_image=wsi,
                    maximum_duration=timedelta(seconds=0),
                    region=default_region,
                ),
                # An expired service in a different region
                SessionFactory(
                    workstation_image=wsi,
                    maximum_duration=timedelta(seconds=0),
                    region="us-east-1",
                ),
            )

        assert s1.service.container
        assert s2.service.container
        assert s3.service.container

        # Stop expired services in the default region
        stop_expired_services(
            app_label="workstations",
            model_name="session",
            region=default_region,
        )

        assert s1.service.container
        with pytest.raises(NotFound):
            # noinspection PyStatementEffect
            s2.service.container
        assert s3.service.container

    finally:
        stop_all_sessions()


@pytest.mark.django_db
def test_workstation_ready(http_image, docker_client, settings):
    path, sha256 = http_image

    wsi = WorkstationImageFactory(
        image__from_path=path, image_sha256=sha256, ready=False
    )

    # Execute the celery in place
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with capture_on_commit_callbacks(execute=True):
        s = SessionFactory(workstation_image=wsi)

    s.refresh_from_db()

    assert s.status == s.FAILED


@pytest.mark.django_db
def test_session_limit(http_image, docker_client, settings):
    path, sha256 = http_image

    wsi = WorkstationImageFactory(
        image__from_path=path, image_sha256=sha256, ready=True
    )

    # Execute the celery in place
    settings.WORKSTATIONS_MAXIMUM_SESSIONS = 1
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    try:
        with capture_on_commit_callbacks(execute=True):
            s1 = SessionFactory(workstation_image=wsi)
        s1.refresh_from_db()
        assert s1.status == s1.STARTED

        with capture_on_commit_callbacks(execute=True):
            s2 = SessionFactory(workstation_image=wsi)
        s2.refresh_from_db()
        assert s2.status == s2.FAILED

        s1.stop()

        with capture_on_commit_callbacks(execute=True):
            s3 = SessionFactory(workstation_image=wsi)
        s3.refresh_from_db()
        assert s3.status == s3.STARTED
    finally:
        stop_all_sessions()


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
