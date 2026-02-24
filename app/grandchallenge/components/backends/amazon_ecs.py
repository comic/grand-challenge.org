from typing import NamedTuple

import boto3
from django.conf import settings

from grandchallenge.evaluation.utils import get


class ConnectionInformation(NamedTuple):
    host_address: str
    http_port: int
    websocket_port: int


class ECSService:
    def __init__(
        self,
        exec_image_repo_tag: str,
        region: str,
    ):
        super().__init__()

        self._exec_image_repo_tag = exec_image_repo_tag
        self._region = region

        self.__ecs_client = None
        self.__ec2_client = None

    @property
    def _ecs_client(self):
        if self.__ecs_client is None:
            self.__ecs_client = boto3.client("ecs", region_name=self._region)
        return self.__ecs_client

    @property
    def _ec2_client(self):
        if self.__ec2_client is None:
            self.__ec2_client = boto3.client("ec2", region_name=self._region)
        return self.__ec2_client

    @property
    def _internal_workstation_container_name(self):
        return "workstation"

    def start(
        self,
        environment: dict,
    ):
        task_definition_arn = self._register_task_definition()

        response = self._ecs_client.run_task(
            cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME,
            count=1,
            enableExecuteCommand=False,
            enableECSManagedTags=True,
            propagateTags="TASK_DEFINITION",
            taskDefinition=task_definition_arn,
            overrides={
                "containerOverrides": [
                    {
                        "name": self._internal_workstation_container_name,
                        "environment": [
                            {"name": k, "value": v}
                            for k, v in environment.items()
                        ],
                    }
                ]
            },
        )

        return response["tasks"][0]["taskArn"]

    def get_connection_information(self, *, task_arn):
        """Get the host and ports for this service"""

        # The host and ports cannot be determined until the task is running
        self._wait_for_task_running(task_arn=task_arn)

        task_description = self._get_task_description(task_arn=task_arn)

        host_address = self._get_host_private_ip_address(
            task_description=task_description
        )
        port_mappings = self._get_port_mappings(
            task_description=task_description
        )

        return ConnectionInformation(
            host_address=host_address,
            http_port=port_mappings[
                settings.COMPONENTS_SERVICE_CONTAINER_HTTP_PORT
            ],
            websocket_port=port_mappings[
                settings.COMPONENTS_SERVICE_CONTAINER_WEBSOCKET_PORT
            ],
        )

    def _wait_for_task_running(self, *, task_arn):
        waiter = self._ecs_client.get_waiter("tasks_running")
        waiter.wait(
            cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME, tasks=[task_arn]
        )

    def _get_task_description(self, *, task_arn):
        return get(
            self._ecs_client.describe_tasks(
                cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME,
                tasks=[task_arn],
            )["tasks"]
        )

    def _get_host_private_ip_address(self, *, task_description):
        """
        Gets the private IP address of the container instance (host)

        Assumes running ECS on EC2 instances. The task must be running
        for this to work.
        """
        container_instance = get(
            self._ecs_client.describe_container_instances(
                cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME,
                containerInstances=[task_description["containerInstanceArn"]],
            )["containerInstances"]
        )

        reservation = get(
            self._ec2_client.describe_instances(
                InstanceIds=[container_instance["ec2InstanceId"]]
            )["Reservations"]
        )

        ec2_instance = get(reservation["Instances"])

        return ec2_instance["PrivateIpAddress"]

    def _get_port_mappings(self, *, task_description):
        """
        Gets the container ports to host ports

        The task must be running for this to work.
        """
        workstation_container = get(
            [
                container
                for container in task_description["containers"]
                if container["name"]
                == self._internal_workstation_container_name
            ]
        )

        return {
            int(binding["containerPort"]): int(binding["hostPort"])
            for binding in workstation_container["networkBindings"]
        }

    def _register_task_definition(self):
        response = self._ecs_client.register_task_definition(
            containerDefinitions=self._container_definitions,
            family=self._task_definition_family,
            requiresCompatibilities=["EC2"],
            taskRoleArn=settings.COMPONENTS_SERVICE_TASK_ROLE_ARN,
        )
        return response["taskDefinition"]["taskDefinitionArn"]

    @property
    def _task_definition_family(self):
        # The task family is based on the exec image repo and tag for grouping.
        # We do not create one task definition per exec image as we may need
        # to modify the runtime settings (CPU limits for instance).
        #
        # There is a limit of 1,000,000 versions per family,
        # it is unlikely that we would have that many sessions for a single
        # container image version.

        repo_tag_without_domain = self._exec_image_repo_tag.split("/")[1:]
        task_definition_safe_repo_tag = "-".join(repo_tag_without_domain)

        # the task definition cannot contain ":"
        return task_definition_safe_repo_tag.replace(":", "-")

    @property
    def _container_definitions(self):
        container_definitions = [
            {
                "name": self._internal_workstation_container_name,
                "image": self._exec_image_repo_tag,
                "portMappings": [
                    {
                        "containerPort": settings.COMPONENTS_SERVICE_CONTAINER_HTTP_PORT,
                        "hostPort": 0,
                        "name": "http",
                    },
                    {
                        "containerPort": settings.COMPONENTS_SERVICE_CONTAINER_WEBSOCKET_PORT,
                        "hostPort": 0,
                        "name": "websocket",
                    },
                ],
                "memoryReservation": settings.COMPONENTS_SERVICE_MEMORY_RESERVATION_MB,
                "dockerSecurityOptions": ["no-new-privileges"],
                "essential": True,
                "linuxParameters": {
                    "capabilities": {"drop": ["ALL"]},
                    "initProcessEnabled": True,
                },
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": settings.COMPONENTS_SERVICE_LOG_GROUP_NAME,
                        "awslogs-region": self._region,
                        "awslogs-stream-prefix": "ecs",
                    },
                },
                "privileged": False,
                "ulimits": [
                    {
                        "name": "nproc",
                        "hardLimit": settings.COMPONENTS_SERVICE_PIDS_LIMIT,
                        "softLimit": settings.COMPONENTS_SERVICE_PIDS_LIMIT,
                    },
                    {
                        "name": "data",
                        "softLimit": settings.COMPONENTS_SERVICE_MEMORY_LIMIT_MB
                        * settings.MEGABYTE,
                        "hardLimit": settings.COMPONENTS_SERVICE_MEMORY_LIMIT_MB
                        * settings.MEGABYTE,
                    },
                ],
            },
        ]

        return container_definitions

    def stop(self, *, task_arn):
        # Fetch the task description before stopping so that we have
        # the task definition info as this gets deleted after some time
        task_description = self._get_task_description(task_arn=task_arn)

        self._ecs_client.stop_task(
            cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME, task=task_arn
        )
        self._ecs_client.deregister_task_definition(
            taskDefinition=task_description["taskDefinitionArn"]
        )
