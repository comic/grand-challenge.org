import boto3
from django.conf import settings


class Service:
    def __init__(
        self,
        container_name: str,
        exec_image_repo_tag: str,
        region: str,
    ):
        super().__init__()
        self._container_name = container_name
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
    def container_name(self):
        return self._container_name

    @property
    def internal_workstation_container_name(self):
        return "workstation"

    def get_host_address(self, *, task_arn):
        task = self._ecs_client.describe_tasks(
            cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME, tasks=[task_arn]
        )["tasks"][0]
        container_instance = self._ecs_client.describe_container_instances(
            cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME,
            containerInstances=[task["containerInstanceArn"]],
        )["containerInstances"][0]
        ec2_instance = self._ec2_client.describe_instances(
            InstanceIds=[container_instance["ec2InstanceId"]]
        )["Reservations"][0]["Instances"][0]
        return ec2_instance["PrivateIpAddress"]

    def get_port_mapping(self, *, port, task_arn):
        task = self._ecs_client.describe_tasks(
            cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME, tasks=[task_arn]
        )["tasks"][0]
        workstation_container = [
            c
            for c in task["containers"]
            if c["name"] == self.internal_workstation_container_name
        ][0]
        binding = [
            b
            for b in workstation_container["networkBindings"]
            if b["containerPort"] == port
        ]
        return binding[0]["hostPort"]

    def start(
        self,
        environment: dict,
    ):
        # TODO there should be one task definition per workstation image
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
                        "name": self.internal_workstation_container_name,
                        "environment": [
                            {"name": k, "value": v}
                            for k, v in environment.items()
                        ],
                    }
                ]
            },
        )

        return response["tasks"][0]["taskArn"]

    def wait_for_task_running(self, *, task_arn):
        waiter = self._ecs_client.get_waiter("tasks_running")
        waiter.wait(
            cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME, tasks=[task_arn]
        )

    @property
    def _container_definitions(self):
        container_definitions = [
            {
                "name": self.internal_workstation_container_name,
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
                "memoryReservation": 256,
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
                        "softLimit": settings.COMPONENTS_SERVICE_MEMORY_LIMIT
                        * settings.GIGABYTE,
                        "hardLimit": settings.COMPONENTS_SERVICE_MEMORY_LIMIT
                        * settings.GIGABYTE,
                    },
                ],
            },
        ]

        return container_definitions

    def _register_task_definition(self):
        response = self._ecs_client.register_task_definition(
            containerDefinitions=self._container_definitions,
            family=self.container_name,  # TODO should be the workstation image id
            requiresCompatibilities=["EC2"],
            taskRoleArn=settings.COMPONENTS_SERVICE_TASK_ROLE_ARN,
        )
        return response["taskDefinition"]["taskDefinitionArn"]

    def stop(self, *, task_arn):
        self._ecs_client.stop_task(
            cluster=settings.COMPONENTS_SERVICE_CLUSTER_NAME, task=task_arn
        )
