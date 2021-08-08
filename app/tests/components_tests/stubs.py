import json
import shutil

from grandchallenge.components.backends.aws_batch import AWSBatchExecutor


class AWSBatchExecutorStub(AWSBatchExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _batch_client(self):
        return BatchClientStub()

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
                    "timestamp": 1628419220719,
                    "message": "Traceback (most recent call last):",
                    "ingestionTime": 1628419220812,
                },
                {
                    "timestamp": 1628419220719,
                    "message": '  File "/tmp/copy_io.py", line 26, in <module>',
                    "ingestionTime": 1628419220812,
                },
                {
                    "timestamp": 1628419220719,
                    "message": '    with open(f"/output/{output_filename}.json", "w") as f:',
                    "ingestionTime": 1628419220812,
                },
                {
                    "timestamp": 1628419220719,
                    "message": "FileNotFoundError: [Errno 2] No such file or directory: '/output/results.json'",
                    "ingestionTime": 1628419220812,
                },
            ],
            "nextForwardToken": "f/00000000000000000000000000000000000000000000000000000000",
            "nextBackwardToken": "b/00000000000000000000000000000000000000000000000000000000",
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
        }


class BatchClientStub:
    def describe_job_definitions(self, **_):
        return {
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
            "jobDefinitions": [
                {
                    "jobDefinitionName": "job-aj0b0000-0000-0000-0000-000000000000",
                    "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/job-aj0b0000-0000-0000-0000-000000000000:1",
                    "revision": 1,
                    "status": "INACTIVE",
                    "type": "container",
                    "parameters": {},
                    "containerProperties": {
                        "image": "dev-algorithm-image:latest",
                        "command": [],
                        "volumes": [],
                        "environment": [],
                        "mountPoints": [],
                        "privileged": False,
                        "ulimits": [
                            {
                                "hardLimit": 128,
                                "name": "nproc",
                                "softLimit": 128,
                            }
                        ],
                        "user": "nobody",
                        "resourceRequirements": [
                            {"value": "4096", "type": "MEMORY"},
                            {"value": "2", "type": "VCPU"},
                        ],
                        "linuxParameters": {
                            "devices": [],
                            "initProcessEnabled": True,
                            "tmpfs": [],
                            "maxSwap": 0,
                            "swappiness": 0,
                        },
                        "secrets": [],
                    },
                    "timeout": {"attemptDurationSeconds": 7260},
                    "tags": {},
                    "propagateTags": True,
                    "platformCapabilities": ["EC2"],
                }
            ],
        }

    def deregister_job_definition(self, **_):
        return {
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0}
        }

    def list_jobs(self, **_):
        return {
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
            "jobSummaryList": [
                {
                    "jobArn": "arn:aws:batch:us-east-1:123456789012:job/ej0b0000-0000-0000-0000-000000000000",
                    "jobId": "ej0b0000-0000-0000-0000-000000000000",
                    "jobName": "job-aj0b0000-0000-0000-0000-000000000000",
                    "createdAt": 1628419894623,
                    "status": "SUCCEEDED",
                    "stoppedAt": 1628419993846,
                    "container": {"exitCode": 0},
                    "jobDefinition": "arn:aws:batch:us-east-1:123456789012:job-definition/job-aj0b0000-0000-0000-0000-000000000000:1",
                },
            ],
        }

    def describe_jobs(self, **_):
        return {
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
            "jobs": [
                {
                    "jobArn": "arn:aws:batch:us-east-1:123456789012:job/ej0b0000-0000-0000-0000-000000000000",
                    "jobName": "job-aj0b0000-0000-0000-0000-000000000000",
                    "jobId": "ej0b0000-0000-0000-0000-000000000000",
                    "jobQueue": "arn:aws:batch:us-east-1:123456789012:job-queue/dev-job-queue",
                    "status": "SUCCEEDED",
                    "attempts": [
                        {
                            "container": {
                                "containerInstanceArn": "arn:aws:ecs:us-east-1:123456789012:container-instance/dev-job-queue_Batch_bac00000-0000-0000-0000-000000000000/aaa00000000000000000000000000",
                                "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/dev-job-queue_Batch_bac00000-0000-0000-0000-000000000000/aaaaa00000000000000000000000000",
                                "exitCode": 0,
                                "logStreamName": "job-aj0b0000-0000-0000-0000-000000000000/default/aaaaa00000000000000000000000000",
                                "networkInterfaces": [],
                            },
                            "startedAt": 1628419993498,
                            "stoppedAt": 1628419993846,
                            "statusReason": "Essential container in task exited",
                        }
                    ],
                    "statusReason": "Essential container in task exited",
                    "createdAt": 1628419894623,
                    "startedAt": 1628419993498,
                    "stoppedAt": 1628419993846,
                    "dependsOn": [],
                    "jobDefinition": "arn:aws:batch:us-east-1:123456789012:job-definition/job-aj0b0000-0000-0000-0000-000000000000:1",
                    "parameters": {},
                    "container": {
                        "image": "dev-algorithm-image:latest",
                        "command": [],
                        "volumes": [],
                        "environment": [],
                        "mountPoints": [],
                        "ulimits": [
                            {
                                "hardLimit": 128,
                                "name": "nproc",
                                "softLimit": 128,
                            }
                        ],
                        "privileged": False,
                        "user": "nobody",
                        "exitCode": 1,
                        "containerInstanceArn": "arn:aws:ecs:us-east-1:123456789012:container-instance/dev-job-queue_Batch_bac00000-0000-0000-0000-000000000000/aaa00000000000000000000000000",
                        "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/dev-job-queue_Batch_bac00000-0000-0000-0000-000000000000/aaaaa00000000000000000000000000",
                        "logStreamName": "job-aj0b0000-0000-0000-0000-000000000000/default/aaaaa00000000000000000000000000",
                        "networkInterfaces": [],
                        "resourceRequirements": [
                            {"value": "4096", "type": "MEMORY"},
                            {"value": "2", "type": "VCPU"},
                        ],
                        "linuxParameters": {
                            "devices": [],
                            "initProcessEnabled": True,
                            "tmpfs": [],
                            "maxSwap": 0,
                            "swappiness": 0,
                        },
                        "secrets": [],
                    },
                    "timeout": {"attemptDurationSeconds": 7260},
                    "tags": {},
                    "propagateTags": True,
                    "platformCapabilities": ["EC2"],
                }
            ],
        }

    def register_job_definition(self, **_):
        return {
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
            "jobDefinitionName": "job-aj0b0000-0000-0000-0000-000000000000",
            "jobDefinitionArn": "arn:aws:batch:us-east-1:123456789012:job-definition/job-aj0b0000-0000-0000-0000-000000000000:1",
            "revision": 3,
        }

    def submit_job(self, **_):
        return {
            "ResponseMetadata": {"HTTPStatusCode": 200, "RetryAttempts": 0},
            "jobArn": "arn:aws:batch:us-east-1:123456789012:job/ej0b0000-0000-0000-0000-000000000000",
            "jobName": "job-aj0b0000-0000-0000-0000-000000000000",
            "jobId": "ej0b0000-0000-0000-0000-000000000000",
        }
