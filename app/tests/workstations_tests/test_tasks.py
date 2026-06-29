import logging
from datetime import timedelta

import pytest
from botocore.stub import Stubber
from django.utils.timezone import now

from grandchallenge.components.backends.amazon_ecs import ECSTaskOrchestrator
from grandchallenge.components.backends.exceptions import RetryStep
from grandchallenge.components.tasks import (
    start_service,
    stop_expired_services,
    stop_service,
    update_service,
)
from grandchallenge.workstations.models import Session, Workstation
from grandchallenge.workstations.tasks import consolidate_unclaimed_sessions
from tests.factories import SessionFactory, WorkstationImageFactory


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
        f"<bound method SQSLambdaTask._execute of SQSLambdaTask(message=SQSLambdaTaskMessage(task_name='grandchallenge.components.tasks.start_service', kwargs={{'app_label': 'workstations', 'model_name': 'session', 'pk': UUID('{s.pk}')}}, n_retries=0), delay=0, queue='default')>"
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

    with pytest.raises(RetryStep, match="Too many sessions are running"):
        start_service(**session.task_kwargs)


@pytest.mark.django_db
def test_start_service(mocker, settings, django_capture_on_commit_callbacks):
    settings.COMPONENTS_SERVICE_TASK_ROLE_ARN = "test-task-role-arn"
    settings.COMPONENTS_SERVICE_LOG_GROUP_NAME = "test-log-group-name"
    settings.COMPONENTS_SERVICE_CLUSTER_NAME = "test-cluster-name"

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
                        "memory": 8192,
                        "memoryReservation": 1024,
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
                "clientToken": f"workstations-session-{session.pk}",
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
        f"<bound method SQSLambdaTask._execute of SQSLambdaTask(message=SQSLambdaTaskMessage(task_name='grandchallenge.components.tasks.update_service', kwargs={{'app_label': 'workstations', 'model_name': 'session', 'pk': UUID('{session.pk}')}}, n_retries=0), delay=0, queue='default')>"
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
                    {
                        "taskArn": "test-task-arn",
                        "lastStatus": "RUNNING",
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
        # Unclaimed sessions should be left running
        creator=None,
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
        f"<bound method SQSLambdaTask._execute of SQSLambdaTask(message=SQSLambdaTaskMessage(task_name='grandchallenge.components.tasks.stop_service', kwargs={{'app_label': 'workstations', 'model_name': 'session', 'pk': UUID('{session_to_stop.pk}')}}, n_retries=0), delay=0, queue='default')>"
    )


@pytest.fixture
def default_workstation_image(settings):
    settings.WORKSTATIONS_ACTIVE_REGIONS = ["eu-central-1"]
    settings.WORKSTATIONS_NUMBER_UNCLAIMED_SESSIONS = 3
    settings.WORKSTATIONS_MAXIMUM_SESSIONS = 10
    settings.COMPONENTS_SERVICE_MAXIMUM_UNCLAIMED_HOURS = 8

    workstation = Workstation.objects.get(
        slug=settings.DEFAULT_WORKSTATION_SLUG
    )
    image = WorkstationImageFactory(
        workstation=workstation,
        image=None,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    return image


def _stop_task_repr(*, pk):
    return (
        f"<bound method SQSLambdaTask._execute of SQSLambdaTask("
        f"message=SQSLambdaTaskMessage("
        f"task_name='grandchallenge.components.tasks.stop_service', "
        f"kwargs={{'app_label': 'workstations', 'model_name': 'session', 'pk': UUID('{pk}')}}, "
        f"n_retries=0), delay=0, queue='default')>"
    )


def _start_task_repr(*, pk):
    return (
        f"<bound method SQSLambdaTask._execute of SQSLambdaTask("
        f"message=SQSLambdaTaskMessage("
        f"task_name='grandchallenge.components.tasks.start_service', "
        f"kwargs={{'app_label': 'workstations', 'model_name': 'session', 'pk': UUID('{pk}')}}, "
        f"n_retries=0), delay=0, queue='default')>"
    )


@pytest.mark.django_db
class TestConsolidateUnclaimedSessions:
    def test_no_active_image(self, settings):
        settings.WORKSTATIONS_ACTIVE_REGIONS = ["eu-central-1"]

        result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 0, "n_sessions_started": 0}
        assert Session.objects.count() == 0

    def test_starts_sessions_to_fill_unclaimed_target(
        self,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks() as callbacks:
            result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 0, "n_sessions_started": 3}

        sessions = Session.objects.active().filter(
            claimed_at=None,
            region="eu-central-1",
            workstation_image=default_workstation_image,
        )
        assert sessions.count() == 3

        # Each new session triggers a start_service task
        assert len(callbacks) == 3
        for session, callback in zip(sessions, callbacks, strict=True):
            assert repr(callback) == _start_task_repr(pk=session.pk)

    def test_does_not_start_sessions_when_target_met(
        self,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks():
            for _ in range(3):
                Session.objects.create(
                    workstation_image=default_workstation_image,
                    region="eu-central-1",
                )

        with django_capture_on_commit_callbacks() as callbacks:
            result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 0, "n_sessions_started": 0}
        assert len(callbacks) == 0
        assert Session.objects.active().filter(claimed_at=None).count() == 3

    def test_respects_maximum_sessions_cap(
        self,
        settings,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        settings.WORKSTATIONS_MAXIMUM_SESSIONS = 2

        with django_capture_on_commit_callbacks() as callbacks:
            result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 0, "n_sessions_started": 2}
        assert Session.objects.active().filter(claimed_at=None).count() == 2
        assert len(callbacks) == 2

    def test_session_stopping(
        self,
        settings,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        settings.LAMBDA_TASKS_EAGER = True
        settings.WORKSTATIONS_NUMBER_UNCLAIMED_SESSIONS = 0

        with django_capture_on_commit_callbacks():
            old_session = Session.objects.create(
                workstation_image=default_workstation_image,
                region="eu-central-1",
            )

        Session.objects.filter(pk=old_session.pk).update(
            created=now() - timedelta(hours=9),
        )

        with django_capture_on_commit_callbacks(execute=True):
            result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 1, "n_sessions_started": 0}

        old_session.refresh_from_db()
        assert old_session.status == Session.STOPPED
        assert old_session.session_utilization.duration.total_seconds() == 0

    def test_stops_expired_unclaimed_sessions(
        self,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks():
            old_session = Session.objects.create(
                workstation_image=default_workstation_image,
                region="eu-central-1",
            )

        Session.objects.filter(pk=old_session.pk).update(
            created=now() - timedelta(hours=9)
        )

        with django_capture_on_commit_callbacks() as callbacks:
            result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 1, "n_sessions_started": 3}

        old_session.refresh_from_db()
        # The service should immediately be set to expired so that
        # it is not claimed later
        assert old_session.status == Session.EXPIRED

        # 1 stop + 3 starts
        callback_reprs = [repr(c) for c in callbacks]
        assert _stop_task_repr(pk=old_session.pk) in callback_reprs

        new_sessions = (
            Session.objects.active()
            .filter(
                claimed_at=None, workstation_image=default_workstation_image
            )
            .exclude(pk=old_session.pk)
        )
        assert new_sessions.count() == 3
        for session in new_sessions:
            assert _start_task_repr(pk=session.pk) in callback_reprs

    def test_stops_unclaimed_sessions_with_wrong_image(
        self,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        other_image = WorkstationImageFactory(
            image=None,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=False,
        )

        with django_capture_on_commit_callbacks():
            wrong_session = Session.objects.create(
                workstation_image=other_image,
                region="eu-central-1",
            )

        with django_capture_on_commit_callbacks() as callbacks:
            result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 1, "n_sessions_started": 3}

        callback_reprs = [repr(c) for c in callbacks]
        assert _stop_task_repr(pk=wrong_session.pk) in callback_reprs

        new_sessions = Session.objects.active().filter(
            claimed_at=None, workstation_image=default_workstation_image
        )
        assert new_sessions.count() == 3

    def test_does_not_stop_claimed_sessions(
        self,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks():
            claimed_session = SessionFactory(
                workstation_image=default_workstation_image,
                status=Session.RUNNING,
            )

        with django_capture_on_commit_callbacks() as callbacks:
            result = consolidate_unclaimed_sessions()

        assert result["n_sessions_stopped"] == 0

        callback_reprs = [repr(c) for c in callbacks]
        assert _stop_task_repr(pk=claimed_session.pk) not in callback_reprs

        # Claimed session still active
        claimed_session.refresh_from_db()
        assert claimed_session.status == Session.RUNNING

    def test_multiple_regions(
        self,
        settings,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        settings.WORKSTATIONS_ACTIVE_REGIONS = ["eu-central-1", "us-east-1"]

        with django_capture_on_commit_callbacks() as callbacks:
            result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 0, "n_sessions_started": 6}
        assert len(callbacks) == 6
        assert (
            Session.objects.active()
            .filter(claimed_at=None, region="eu-central-1")
            .count()
            == 3
        )
        assert (
            Session.objects.active()
            .filter(claimed_at=None, region="us-east-1")
            .count()
            == 3
        )

    def test_maximum_sessions_is_per_region(
        self,
        settings,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        settings.WORKSTATIONS_ACTIVE_REGIONS = ["eu-central-1", "us-east-1"]
        settings.WORKSTATIONS_MAXIMUM_SESSIONS = 2

        with django_capture_on_commit_callbacks() as callbacks:
            result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 0, "n_sessions_started": 4}
        assert len(callbacks) == 4
        assert (
            Session.objects.active()
            .filter(claimed_at=None, region="eu-central-1")
            .count()
            == 2
        )
        assert (
            Session.objects.active()
            .filter(claimed_at=None, region="us-east-1")
            .count()
            == 2
        )

    def test_claimed_sessions_count_toward_maximum(
        self,
        settings,
        default_workstation_image,
        django_capture_on_commit_callbacks,
    ):
        settings.WORKSTATIONS_MAXIMUM_SESSIONS = 4

        with django_capture_on_commit_callbacks():
            SessionFactory(
                workstation_image=default_workstation_image,
                status=Session.RUNNING,
                region="eu-central-1",
            )
            SessionFactory(
                workstation_image=default_workstation_image,
                status=Session.RUNNING,
                region="eu-central-1",
            )

        with django_capture_on_commit_callbacks() as callbacks:
            result = consolidate_unclaimed_sessions()

        assert result == {"n_sessions_stopped": 0, "n_sessions_started": 2}
        assert len(callbacks) == 2
        # 2 claimed + 2 new unclaimed = 4 total active
        assert (
            Session.objects.active().filter(region="eu-central-1").count() == 4
        )
        assert (
            Session.objects.active()
            .filter(claimed_at=None, region="eu-central-1")
            .count()
            == 2
        )
