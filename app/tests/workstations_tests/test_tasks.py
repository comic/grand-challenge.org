import logging
from datetime import timedelta

import pytest
from botocore.stub import Stubber

from grandchallenge.components.backends.amazon_ecs import ECSTaskOrchestrator
from grandchallenge.components.tasks import (
    start_service,
    stop_expired_services,
    stop_service,
    update_service,
)
from grandchallenge.workstations.models import Session
from tests.factories import SessionFactory


@pytest.mark.django_db
def test_start_service_scheduled(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks() as callbacks:
        s = SessionFactory(
            workstation_image__is_manifest_valid=True,
            workstation_image__is_in_registry=True,
            workstation_image__is_desired_version=True,
        )

    assert len(callbacks) == 1
    assert repr(callbacks[0]) == (
        "<bound method Signature.apply_async of "
        "grandchallenge.components.tasks.start_service"
        f"(app_label='workstations', model_name='session', pk={s.pk!r})>"
    )


@pytest.mark.django_db
def test_workstation_ready(caplog):
    session = SessionFactory()

    with caplog.at_level(
        logging.ERROR, logger="grandchallenge.components.tasks"
    ):
        start_service(**session.task_kwargs)

    session.refresh_from_db()

    assert session.status == Session.FAILED

    assert "Workstation image was not ready to be used" in caplog.text


@pytest.mark.django_db
def test_workstation_limit(settings, django_capture_on_commit_callbacks):
    # Start service should be retried if there are too many sessions

    settings.WORKSTATIONS_MAXIMUM_SESSIONS = 1

    session = SessionFactory(
        workstation_image__is_manifest_valid=True,
        workstation_image__is_in_registry=True,
        workstation_image__is_desired_version=True,
    )

    with django_capture_on_commit_callbacks() as callbacks:
        start_service(**session.task_kwargs)

    assert len(callbacks) == 1
    assert repr(callbacks[0]) == (
        "<bound method Signature.apply_async of "
        "grandchallenge.components.tasks.start_service"
        f"(app_label='workstations', model_name='session', pk={session.pk!r}, _retries=1)>"
    )


@pytest.mark.django_db
def test_start_service(mocker, settings, django_capture_on_commit_callbacks):
    settings.COMPONENTS_SERVICE_TASK_ROLE_ARN = "test-task-role-arn"
    settings.COMPONENTS_SERVICE_LOG_GROUP_NAME = "test-log-group-name"
    settings.COMPONENTS_SERVICE_CLUSTER_NAME = "test-cluster-name"
    settings.COMPONENTS_SERVICE_INCLUDE_CREATOR_AUTH_TOKEN = False

    session = SessionFactory(
        workstation_image__is_manifest_valid=True,
        workstation_image__is_in_registry=True,
        workstation_image__is_desired_version=True,
    )

    orchestrator = ECSTaskOrchestrator(**session.orchestrator_kwargs)

    patched_service = mocker.patch(
        "grandchallenge.components.tasks.ECSTaskOrchestrator",
        return_value=orchestrator,
    )

    with (
        Stubber(orchestrator._ecs_client) as ecs_stubber,
        django_capture_on_commit_callbacks() as callbacks,
    ):
        ecs_stubber.add_response(
            method="register_task_definition",
            service_response={
                "taskDefinition": {
                    "taskDefinitionArn": "test-task-definition-arn"
                }
            },
            expected_params={
                "containerDefinitions": [
                    {
                        "dockerSecurityOptions": ["no-new-privileges"],
                        "essential": True,
                        "image": f"{settings.COMPONENTS_REGISTRY_URL}/localhost/workstations/workstationimage:{session.workstation_image.pk}",
                        "linuxParameters": {
                            "capabilities": {"drop": ["ALL"]},
                            "initProcessEnabled": True,
                        },
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": "test-log-group-name",
                                "awslogs-region": "eu-nl-1",
                                "awslogs-stream-prefix": "ecs",
                            },
                        },
                        "memoryReservation": 512,
                        "name": "workstation",
                        "portMappings": [
                            {
                                "containerPort": 8080,
                                "hostPort": 0,
                                "name": "http",
                            },
                            {
                                "containerPort": 4114,
                                "hostPort": 0,
                                "name": "websocket",
                            },
                        ],
                        "privileged": False,
                    }
                ],
                "family": f"localhost-workstations-workstationimage-{session.workstation_image.pk}",
                "requiresCompatibilities": ["EC2"],
                "taskRoleArn": "test-task-role-arn",
            },
        )
        ecs_stubber.add_response(
            method="run_task",
            service_response={"tasks": [{"taskArn": "test-task-arn"}]},
            expected_params={
                "cluster": "test-cluster-name",
                "count": 1,
                "enableECSManagedTags": True,
                "enableExecuteCommand": False,
                "overrides": {
                    "containerOverrides": [
                        {
                            "environment": [
                                {
                                    "name": "GRAND_CHALLENGE_API_ROOT",
                                    "value": "https://testserver/api/v1/",
                                },
                                {
                                    "name": "WORKSTATION_SENTRY_DSN",
                                    "value": "",
                                },
                                {
                                    "name": "WORKSTATION_SESSION_ID",
                                    "value": str(session.pk),
                                },
                                {
                                    "name": "CIRRUS_KEEP_ALIVE_METHOD",
                                    "value": "old",
                                },
                                {
                                    "name": "AWS_DEFAULT_REGION",
                                    "value": "eu-central-1",
                                },
                                {
                                    "name": "INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS",
                                    "value": "null",
                                },
                                {
                                    "name": "WORKSTATIONS_MAX_CONCURRENT_API_REQUESTS",
                                    "value": "10",
                                },
                            ],
                            "name": "workstation",
                        }
                    ]
                },
                "propagateTags": "TASK_DEFINITION",
                "taskDefinition": "test-task-definition-arn",
            },
        )

        start_service(**session.task_kwargs)

    patched_service.assert_called_once_with(**session.orchestrator_kwargs)

    session.refresh_from_db()

    assert session.status == session.STARTED
    assert session.task_arn == "test-task-arn"
    assert session.host_address is None
    assert session.http_port is None
    assert session.websocket_port is None

    assert len(callbacks) == 1
    assert repr(callbacks[0]) == (
        "<bound method Signature.apply_async of "
        "grandchallenge.components.tasks.update_service"
        f"(app_label='workstations', model_name='session', pk={session.pk!r})>"
    )


@pytest.mark.django_db
def test_update_service(mocker, settings):
    settings.COMPONENTS_SERVICE_CLUSTER_NAME = "test-cluster-name"

    session = SessionFactory(
        workstation_image__is_manifest_valid=True,
        workstation_image__is_in_registry=True,
        workstation_image__is_desired_version=True,
        task_arn="test-task-arn",
        status=Session.STARTED,
    )

    orchestrator = ECSTaskOrchestrator(**session.orchestrator_kwargs)

    patched_service = mocker.patch(
        "grandchallenge.components.tasks.ECSTaskOrchestrator",
        return_value=orchestrator,
    )

    with (
        Stubber(orchestrator._ecs_client) as ecs_stubber,
        Stubber(orchestrator._ec2_client) as ec2_stubber,
    ):
        ecs_stubber.add_response(
            method="describe_tasks",
            expected_params={
                "cluster": "test-cluster-name",
                "tasks": ["test-task-arn"],
            },
            service_response={
                "tasks": [
                    {"taskArn": "test-task-arn", "lastStatus": "RUNNING"}
                ],
                "failures": [],
            },
        )
        ecs_stubber.add_response(
            method="describe_tasks",
            expected_params={
                "cluster": "test-cluster-name",
                "tasks": ["test-task-arn"],
            },
            service_response={
                "tasks": [
                    {
                        "taskArn": "test-task-arn",
                        "containerInstanceArn": "test-container-instance-arn",
                        "containers": [
                            {
                                "name": "workstation",
                                "networkBindings": [
                                    {"containerPort": 8080, "hostPort": 32768},
                                    {"containerPort": 4114, "hostPort": 32769},
                                ],
                            }
                        ],
                    }
                ],
            },
        )
        ecs_stubber.add_response(
            method="describe_container_instances",
            expected_params={
                "cluster": "test-cluster-name",
                "containerInstances": ["test-container-instance-arn"],
            },
            service_response={
                "containerInstances": [
                    {"ec2InstanceId": "test-ec2-instance-id"}
                ],
            },
        )
        ec2_stubber.add_response(
            method="describe_instances",
            expected_params={"InstanceIds": ["test-ec2-instance-id"]},
            service_response={
                "Reservations": [
                    {"Instances": [{"PrivateIpAddress": "123.123.123.123"}]}
                ],
            },
        )

        update_service(**session.task_kwargs)

    patched_service.assert_called_once_with(**session.orchestrator_kwargs)

    session.refresh_from_db()

    assert session.status == session.RUNNING
    assert session.task_arn == "test-task-arn"
    assert session.host_address == "123.123.123.123"
    assert session.http_port == 32768
    assert session.websocket_port == 32769


@pytest.mark.django_db
def test_stop_service(mocker, settings):
    settings.COMPONENTS_SERVICE_CLUSTER_NAME = "test-cluster-name"

    session = SessionFactory(
        workstation_image__is_manifest_valid=True,
        workstation_image__is_in_registry=True,
        workstation_image__is_desired_version=True,
        task_arn="test-task-arn",
        host_address="123.123.123.123",
        http_port=32768,
        websocket_port=32769,
        status=Session.RUNNING,
    )

    orchestrator = ECSTaskOrchestrator(**session.orchestrator_kwargs)

    patched_service = mocker.patch(
        "grandchallenge.components.tasks.ECSTaskOrchestrator",
        return_value=orchestrator,
    )

    with Stubber(orchestrator._ecs_client) as ecs_stubber:
        ecs_stubber.add_response(
            method="describe_tasks",
            expected_params={
                "cluster": "test-cluster-name",
                "tasks": ["test-task-arn"],
            },
            service_response={
                "tasks": [
                    {
                        "taskArn": "test-task-arn",
                        "taskDefinitionArn": "test-task-definition-arn",
                    }
                ],
            },
        )
        ecs_stubber.add_response(
            method="stop_task",
            expected_params={
                "cluster": "test-cluster-name",
                "task": "test-task-arn",
            },
            service_response={},
        )
        ecs_stubber.add_response(
            method="deregister_task_definition",
            expected_params={
                "taskDefinition": "test-task-definition-arn",
            },
            service_response={},
        )

        stop_service(**session.task_kwargs)

    patched_service.assert_called_once_with(**session.orchestrator_kwargs)

    session.refresh_from_db()

    assert session.status == session.STOPPED


@pytest.mark.django_db
def test_session_cleanup(django_capture_on_commit_callbacks):
    SessionFactory(status=Session.RUNNING)
    session_to_stop = SessionFactory(
        status=Session.RUNNING,
        maximum_duration=timedelta(seconds=0),
    )
    SessionFactory(
        status=Session.STOPPED,
        maximum_duration=timedelta(seconds=0),
    )

    with django_capture_on_commit_callbacks() as callbacks:
        stop_expired_services(app_label="workstations", model_name="session")

    assert len(callbacks) == 1
    assert repr(callbacks[0]) == (
        "<bound method Signature.apply_async of "
        "grandchallenge.components.tasks.stop_service"
        f"(app_label='workstations', model_name='session', pk={session_to_stop.pk!r})>"
    )


@pytest.mark.django_db
def test_related_auth_token_deleted_when_stopped():
    session = SessionFactory()

    _ = session.environment  # creates the auth token

    session.refresh_from_db()

    assert session.auth_token

    stop_service(**session.task_kwargs)

    session.refresh_from_db()

    assert not session.auth_token
