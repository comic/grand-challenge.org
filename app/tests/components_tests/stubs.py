import json
import shutil
from datetime import datetime

from dateutil.tz import tzlocal

from grandchallenge.components.backends.amazon_ecs import AmazonECSExecutor


class AmazonECSExecutorStub(AmazonECSExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _ecs_client(self):
        return ECSClientStub()

    @property
    def _logs_client(self):
        return LogsClientStub()

    def execute(self):
        ret = super().execute()
        self._copy_to_output()
        return ret

    def _copy_to_output(self):
        res = {}
        files = {x for x in self._input_directory.rglob("*") if x.is_file()}

        for file in files:
            try:
                with open(file) as f:
                    val = json.loads(f.read())
            except Exception:
                val = "file"

            res[str(file.absolute())] = val

            new_file = self._output_directory / file.relative_to(
                self._input_directory
            )
            new_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(file, new_file)

        for output_filename in ["results", "metrics"]:
            with open(
                self._output_directory / f"{output_filename}.json", "w"
            ) as f:
                f.write(json.dumps(res))


class LogsClientStub:
    def get_log_events(self, **_):
        return {
            "events": [
                {
                    "timestamp": 1631538757000,
                    "message": '{"container_id":"abc123","container_name":"/ecs-algorithms-blah","log":"  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current","source":"stderr"}',
                    "ingestionTime": 1631538761528,
                },
                {
                    "timestamp": 1631538757000,
                    "message": '{"container_id":"abc123","container_name":"/ecs-algorithms-blah","log":"                                 Dload  Upload   Total   Spent    Left  Speed","source":"stderr"}',
                    "ingestionTime": 1631538761528,
                },
                {
                    "timestamp": 1631538757000,
                    "message": '{"container_id":"abc123","container_name":"/ecs-algorithms-blah","log":"\\r  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0curl: (6) Could not resolve host: www.google.com","source":"stderr"}',
                    "ingestionTime": 1631538761528,
                },
            ],
            "nextForwardToken": "f/00000000000000000000000000000000000000000000000000000000",
            "nextBackwardToken": "b/00000000000000000000000000000000000000000000000000000000",
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
        }


class ECSClientStub:
    def register_task_definition(self, **_):
        return {
            "taskDefinition": {
                "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1",
                "containerDefinitions": [
                    {
                        "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout",
                        "image": "alpine:3.14",
                        "cpu": 0,
                        "portMappings": [],
                        "essential": True,
                        "command": ["sleep", "30"],
                        "environment": [],
                        "mountPoints": [],
                        "volumesFrom": [],
                        "linuxParameters": {
                            "capabilities": {"drop": ["ALL"]},
                            "initProcessEnabled": True,
                            "maxSwap": 0,
                            "swappiness": 0,
                        },
                        "user": "nobody",
                        "disableNetworking": True,
                        "privileged": False,
                        "dockerSecurityOptions": ["no-new-privileges"],
                        "ulimits": [
                            {
                                "name": "nproc",
                                "softLimit": 128,
                                "hardLimit": 128,
                            }
                        ],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": "grand-challenge",
                                "awslogs-region": "us-east-1",
                                "awslogs-stream-prefix": "ecs",
                            },
                        },
                    },
                    {
                        "name": "algorithms-job-00000000-0000-0000-0000-000000000000",
                        "image": "amazonlinux:2",
                        "cpu": 2048,
                        "memory": 4096,
                        "portMappings": [],
                        "essential": True,
                        "command": ["curl", "-I", "https://www.google.com"],
                        "environment": [],
                        "mountPoints": [],
                        "volumesFrom": [],
                        "linuxParameters": {
                            "capabilities": {"drop": ["ALL"]},
                            "initProcessEnabled": True,
                            "maxSwap": 0,
                            "swappiness": 0,
                        },
                        "user": "nobody",
                        "disableNetworking": True,
                        "privileged": False,
                        "dockerSecurityOptions": ["no-new-privileges"],
                        "ulimits": [
                            {
                                "name": "nproc",
                                "softLimit": 128,
                                "hardLimit": 128,
                            }
                        ],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": "grand-challenge",
                                "awslogs-region": "us-east-1",
                                "awslogs-stream-prefix": "ecs",
                            },
                        },
                    },
                ],
                "family": "algorithms-job-00000000-0000-0000-0000-000000000000",
                "networkMode": "none",
                "revision": 1,
                "volumes": [],
                "status": "ACTIVE",
                "requiresAttributes": [
                    {
                        "name": "com.amazonaws.ecs.capability.logging-driver.awslogs"
                    },
                    {
                        "name": "com.amazonaws.ecs.capability.docker-remote-api.1.19"
                    },
                    {"name": "ecs.capability.pid-ipc-namespace-sharing"},
                    {
                        "name": "com.amazonaws.ecs.capability.docker-remote-api.1.17"
                    },
                    {
                        "name": "com.amazonaws.ecs.capability.docker-remote-api.1.32"
                    },
                    {
                        "name": "com.amazonaws.ecs.capability.docker-remote-api.1.25"
                    },
                    {
                        "name": "com.amazonaws.ecs.capability.docker-remote-api.1.23"
                    },
                    {
                        "name": "com.amazonaws.ecs.capability.docker-remote-api.1.18"
                    },
                ],
                "placementConstraints": [],
                "compatibilities": ["EXTERNAL", "EC2"],
                "requiresCompatibilities": ["EC2"],
                "cpu": "2048",
                "memory": "4096",
                "ipcMode": "none",
                "registeredAt": datetime(
                    2021, 9, 10, 10, 11, 44, 884000, tzinfo=tzlocal()
                ),
                "registeredBy": "arn:aws:iam::123456789012:user/redacted",
            },
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
        }

    def run_task(self, **_):
        return {
            "tasks": [
                {
                    "attachments": [],
                    "availabilityZone": "us-east-1a",
                    "capacityProviderName": "my-capacity-provider",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/grand-challenge",
                    "containerInstanceArn": "arn:aws:ecs:us-east-1:123456789012:container-instance/grand-challenge/abc1234567890",
                    "containers": [
                        {
                            "containerArn": "arn:aws:ecs:us-east-1:123456789012:container/grand-challenge/abcd1234567890/00000000-0000-0000-0000-000000000002",
                            "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/grand-challenge/abcd1234567890",
                            "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout",
                            "image": "alpine:3.14",
                            "lastStatus": "PENDING",
                            "networkInterfaces": [],
                            "cpu": "0",
                        },
                        {
                            "containerArn": "arn:aws:ecs:us-east-1:123456789012:container/grand-challenge/abcd1234567890/00000000-0000-0000-0000-000000000001",
                            "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/grand-challenge/abcd1234567890",
                            "name": "algorithms-job-00000000-0000-0000-0000-000000000000",
                            "image": "amazonlinux:2",
                            "lastStatus": "PENDING",
                            "networkInterfaces": [],
                            "cpu": "2048",
                            "memory": "4096",
                        },
                    ],
                    "cpu": "2048",
                    "createdAt": datetime(
                        2021, 9, 10, 10, 11, 52, 533000, tzinfo=tzlocal()
                    ),
                    "desiredStatus": "RUNNING",
                    "enableExecuteCommand": False,
                    "group": "family:algorithms-job-00000000-0000-0000-0000-000000000000",
                    "lastStatus": "PENDING",
                    "launchType": "EC2",
                    "memory": "4096",
                    "overrides": {
                        "containerOverrides": [
                            {
                                "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout"
                            },
                            {
                                "name": "algorithms-job-00000000-0000-0000-0000-000000000000"
                            },
                        ],
                        "inferenceAcceleratorOverrides": [],
                    },
                    "tags": [
                        {
                            "key": "aws:ecs:clusterName",
                            "value": "grand-challenge",
                        }
                    ],
                    "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/grand-challenge/abcd1234567890",
                    "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1",
                    "version": 1,
                }
            ],
            "failures": [],
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
        }

    def list_tasks(self, **_):
        return {
            "taskArns": [
                "arn:aws:ecs:us-east-1:123456789012:task/grand-challenge/abcd1234567890"
            ],
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
        }

    def describe_tasks(self, **_):
        return {
            "tasks": [
                {
                    "attachments": [],
                    "availabilityZone": "us-east-1a",
                    "capacityProviderName": "my-capacity-provider",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/grand-challenge",
                    "connectivity": "CONNECTED",
                    "connectivityAt": datetime(
                        2021, 9, 10, 10, 11, 52, 533000, tzinfo=tzlocal()
                    ),
                    "containerInstanceArn": "arn:aws:ecs:us-east-1:123456789012:container-instance/grand-challenge/abc1234567890",
                    "containers": [
                        {
                            "containerArn": "arn:aws:ecs:us-east-1:123456789012:container/grand-challenge/abcd1234567890/00000000-0000-0000-0000-000000000002",
                            "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/grand-challenge/abcd1234567890",
                            "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout",
                            "image": "alpine:3.14",
                            "runtimeId": "asgjdkgdsadsahflkjdfhasjklfhsaljkfh",
                            "lastStatus": "STOPPED",
                            "exitCode": 143,
                            "networkBindings": [],
                            "networkInterfaces": [],
                            "healthStatus": "UNKNOWN",
                            "cpu": "0",
                        },
                        {
                            "containerArn": "arn:aws:ecs:us-east-1:123456789012:container/grand-challenge/abcd1234567890/00000000-0000-0000-0000-000000000001",
                            "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/grand-challenge/abcd1234567890",
                            "name": "algorithms-job-00000000-0000-0000-0000-000000000000",
                            "image": "amazonlinux:2",
                            "runtimeId": "ewtyqpiqwyretuywq",
                            "lastStatus": "STOPPED",
                            "exitCode": 0,
                            "networkBindings": [],
                            "networkInterfaces": [],
                            "healthStatus": "UNKNOWN",
                            "cpu": "2048",
                            "memory": "4096",
                        },
                    ],
                    "cpu": "2048",
                    "createdAt": datetime(
                        2021, 9, 10, 10, 11, 52, 533000, tzinfo=tzlocal()
                    ),
                    "desiredStatus": "STOPPED",
                    "enableExecuteCommand": False,
                    "executionStoppedAt": datetime(
                        2021, 9, 10, 10, 11, 55, 320000, tzinfo=tzlocal()
                    ),
                    "group": "family:algorithms-job-00000000-0000-0000-0000-000000000000",
                    "healthStatus": "UNKNOWN",
                    "lastStatus": "STOPPED",
                    "launchType": "EC2",
                    "memory": "4096",
                    "overrides": {
                        "containerOverrides": [
                            {
                                "name": "algorithms-job-00000000-0000-0000-0000-000000000000-timeout"
                            },
                            {
                                "name": "algorithms-job-00000000-0000-0000-0000-000000000000"
                            },
                        ],
                        "inferenceAcceleratorOverrides": [],
                    },
                    "startedAt": datetime(
                        2021, 9, 10, 10, 11, 55, 287000, tzinfo=tzlocal()
                    ),
                    "stopCode": "EssentialContainerExited",
                    "stoppedAt": datetime(
                        2021, 9, 10, 10, 11, 55, 460000, tzinfo=tzlocal()
                    ),
                    "stoppedReason": "Essential container in task exited",
                    "stoppingAt": datetime(
                        2021, 9, 10, 10, 11, 55, 460000, tzinfo=tzlocal()
                    ),
                    "tags": [],
                    "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/grand-challenge/abcd1234567890",
                    "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1",
                    "version": 3,
                }
            ],
            "failures": [],
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
        }

    def list_task_definitions(self, **_):
        return {
            "taskDefinitionArns": [
                "arn:aws:ecs:us-east-1:123456789012:task-definition/algorithms-job-00000000-0000-0000-0000-000000000000:1"
            ],
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
        }

    def deregister_task_definition(self, **_):
        return self.list_task_definitions()

    def stop_task(self, **_):
        return {
            "task": {
                "attachments": [],
                "capacityProviderName": "my-capacity-provider",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/grand-challenge",
                "containers": [],
                "cpu": "2048",
                "createdAt": datetime(
                    2021, 9, 12, 8, 31, 50, 939000, tzinfo=tzlocal()
                ),
                "desiredStatus": "STOPPED",
                "enableExecuteCommand": False,
                "group": "family:algorithms-job-00000000-0000-0000-0000-000000000000",
                "lastStatus": "PROVISIONING",
                "launchType": "EC2",
                "memory": "4096",
                "overrides": {
                    "containerOverrides": [],
                    "inferenceAcceleratorOverrides": [],
                },
                "stopCode": "UserInitiated",
                "stoppedReason": "Task stopped by user",
                "stoppingAt": datetime(
                    2021, 9, 12, 8, 33, 28, 648000, tzinfo=tzlocal()
                ),
                "tags": [],
                "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/grand-challenge/abcd1234567890",
                "taskDefinitionArn": "",
                "version": 2,
            },
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
        }
