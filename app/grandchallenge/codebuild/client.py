import boto3
from django.conf import settings
from django.core import files
from django.core.files.temp import NamedTemporaryFile

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.codebuild.models import Build
from grandchallenge.core.storage import private_s3_storage


class CodeBuildClient:
    build = None

    def __init__(
        self, *, project_name=None, msg=None, algorithm=None, build_id=None,
    ):
        self.client = boto3.client(
            "codebuild",
            aws_access_key_id=settings.CODEBUILD_ACCESS_KEY,
            aws_secret_access_key=settings.CODEBUILD_SECRET_KEY,
            region_name=settings.CODEBUILD_REGION,
        )
        self.log_client = boto3.client(
            "logs",
            aws_access_key_id=settings.CODEBUILD_ACCESS_KEY,
            aws_secret_access_key=settings.CODEBUILD_SECRET_KEY,
            region_name=settings.CODEBUILD_REGION,
        )
        self.project_name = project_name
        self.msg = msg
        self.algorithm = algorithm
        self.build_id = build_id
        self.config = {
            "name": project_name,
            "source": {"type": "S3", "location": ""},
            "artifacts": {
                "type": "S3",
                "location": settings.PRIVATE_S3_STORAGE_KWARGS["bucket_name"],
            },
            "environment": {
                "type": "LINUX_CONTAINER",
                "image": "docker:dind",
                "computeType": "BUILD_GENERAL1_SMALL",
                "privilegedMode": True,
                "registryCredential": {
                    "credential": settings.DOCKER_SECRET_ARN,
                    "credentialProvider": "SECRETS_MANAGER",
                },
                "imagePullCredentialsType": "SERVICE_ROLE",
            },
            "serviceRole": settings.CODEBUILD_SERVICE_ROLE,
            "encryptionKey": settings.CODEBUILD_ENCRYPTION_KEY,
        }

    def create_build_project(self, *, source):
        self.config["source"]["location"] = source
        self.client.create_project(**self.config)

    def start_build(self):
        data = self.client.start_build(projectName=self.project_name)
        self.build_id = data["build"]["id"]
        build = Build.objects.create(
            build_id=self.build_id,
            project_name=self.project_name,
            status=data["build"]["buildStatus"],
            build_config=self.config,
            webhook_message=self.msg,
            algorithm=self.algorithm,
        )
        return build.pk

    def get_build_status(self):
        builds = self.client.batch_get_builds(ids=[self.build_id])
        self.build = builds["builds"][0]
        return self.build["buildStatus"]

    def get_logs(self):
        return self.log_client.get_log_events(
            logGroupName=self.build["logs"]["groupName"],
            logStreamName=self.build["logs"]["streamName"],
        )

    def add_image_to_algorithm(self):
        with private_s3_storage.open(
            f"{self.project_name}/{self.msg.output_path}/{self.project_name}.tar"
        ) as file:
            with NamedTemporaryFile(delete=True) as tmp_file:
                with open(tmp_file.name, "wb") as fd:
                    for chunk in file.chunks():
                        fd.write(chunk)

                tmp_file.flush()
                temp_file = files.File(
                    tmp_file, name="{self.project_name}.tar",
                )
                AlgorithmImage.objects.create(
                    algorithm=self.algorithm, image=temp_file
                )
        return temp_file
