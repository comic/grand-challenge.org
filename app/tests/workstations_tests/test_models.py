from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from docker.errors import NotFound
from rest_framework.authtoken.models import Token

from grandchallenge.container_exec.tasks import stop_expired_services
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
    assert (
        Token.objects.get(user=s.creator).key
        in env["GRAND_CHALLENGE_AUTHORIZATION"]
    )

    if debug:
        assert "GRAND_CHALLENGE_UNSAFE" in env
    else:
        assert "GRAND_CHALLENGE_UNSAFE" not in env


@pytest.mark.django_db
def test_session_start(http_image, docker_client, settings):
    path, sha256 = http_image

    wsi = WorkstationImageFactory(
        image__from_path=path, image_sha256=sha256, ready=True
    )

    # Execute the celery in place
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    s = SessionFactory(workstation_image=wsi)

    try:
        assert s.service.container

        s.refresh_from_db()
        assert s.status == s.STARTED

        container = s.service.container

        assert container.labels["traefik.enable"] == "true"
        assert container.labels["traefik.http.port"] == str(
            s.workstation_image.http_port
        )
        assert container.labels["traefik.websocket.port"] == str(
            s.workstation_image.websocket_port
        )

        networks = container.attrs.get("NetworkSettings")["Networks"]
        assert len(networks) == 1
        assert settings.WORKSTATIONS_NETWORK_NAME in networks

        s.user_finished = True
        s.save()

        with pytest.raises(NotFound):
            # noinspection PyStatementEffect
            s.service.container
    finally:
        s.stop()


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
        s1, s2 = (
            SessionFactory(workstation_image=wsi),
            SessionFactory(workstation_image=wsi),
        )

        assert s1.service.container
        assert s2.service.container

        s2.user_finished = True
        s2.save()

        assert s1.service.container
        with pytest.raises(NotFound):
            # noinspection PyStatementEffect
            s2.service.container
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

    try:
        s1, s2 = (
            SessionFactory(workstation_image=wsi),
            SessionFactory(
                workstation_image=wsi, maximum_duration=timedelta(seconds=0)
            ),
        )

        assert s1.service.container
        assert s2.service.container

        stop_expired_services(app_label="workstations", model_name="session")

        assert s1.service.container
        with pytest.raises(NotFound):
            # noinspection PyStatementEffect
            s2.service.container
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
        s1 = SessionFactory(workstation_image=wsi)
        s1.refresh_from_db()
        assert s1.status == s1.STARTED

        s2 = SessionFactory(workstation_image=wsi)
        s2.refresh_from_db()
        assert s2.status == s2.FAILED

        s1.stop()

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

    getattr(ws, group).delete()

    with pytest.raises(ObjectDoesNotExist):
        users_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        editors_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        ws.refresh_from_db()
