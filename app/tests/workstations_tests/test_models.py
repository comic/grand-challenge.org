from datetime import timedelta

import pytest
from docker.errors import NotFound
from rest_framework.authtoken.models import Token

from grandchallenge.container_exec.tasks import stop_expired_services
from tests.factories import SessionFactory, WorkstationImageFactory


@pytest.mark.django_db
@pytest.mark.parametrize("debug", [True, False])
def test_session_environ(settings, debug):
    settings.DEBUG = debug

    s = SessionFactory()
    env = s.environment

    assert env["GRAND_CHALLENGE_PROXY_URL_MAPPINGS"] == ""
    assert "{key}" in env["GRAND_CHALLENGE_QUERY_IMAGE_URL"]
    assert env["GRAND_CHALLENGE_QUERY_IMAGE_URL"].startswith(
        "https://testserver"
    )
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

    s1, s2 = (
        SessionFactory(workstation_image=wsi),
        SessionFactory(workstation_image=wsi),
    )

    try:
        assert s1.service.container
        assert s2.service.container

        s2.user_finished = True
        s2.save()

        assert s1.service.container
        with pytest.raises(NotFound):
            # noinspection PyStatementEffect
            s2.service.container
    finally:
        s1.stop()
        s2.stop()


@pytest.mark.django_db
def test_session_cleanup(http_image, docker_client, settings):
    path, sha256 = http_image

    wsi = WorkstationImageFactory(
        image__from_path=path, image_sha256=sha256, ready=True
    )

    # Execute the celery in place
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    s1, s2 = (
        SessionFactory(workstation_image=wsi),
        SessionFactory(
            workstation_image=wsi, maximum_duration=timedelta(seconds=0)
        ),
    )

    try:
        assert s1.service.container
        assert s2.service.container

        stop_expired_services(app_label="workstations", model_name="session")

        assert s1.service.container
        with pytest.raises(NotFound):
            # noinspection PyStatementEffect
            s2.service.container
    finally:
        s1.stop()
        s2.stop()


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
