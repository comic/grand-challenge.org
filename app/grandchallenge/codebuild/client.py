from time import sleep

import boto3
from django.conf import settings
from django.core import files
from django.core.files.temp import NamedTemporaryFile

from grandchallenge.algorithms.models import AlgorithmImage


class CodeBuildClient:
    build_id = None

    def __init__(
        self, *, project_name,
    ):
        self.client = boto3.client(
            "codebuild",
            aws_access_key_id=settings.CODEBUILD_ACCESS_KEY,
            aws_secret_access_key=settings.CODEBUILD_SECRET_KEY,
            region_name="eu-central-1",
        )
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.CODEBUILD_ACCESS_KEY,
            aws_secret_access_key=settings.CODEBUILD_SECRET_KEY,
            region_name="eu-central-1",
        )
        self.project_name = project_name
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

    def get_build_status(self):
        builds = self.client.batch_get_builds(ids=[self.build_id])
        build = builds["builds"][0]
        return build["buildStatus"]

    def wait_for_completion(self):
        build_status = self.get_build_status()
        while self.get_build_status() == "IN_PROGRESS":
            sleep(3)
            build_status = self.get_build_status()
        return build_status

    def add_image_to_algorithm(self, *, algorithm):
        response = self.s3_client.get_object(
            Bucket=settings.PRIVATE_S3_STORAGE_KWARGS["bucket_name"],
            Key=f"{self.project_name}/{self.project_name}.tar",
        )
        with NamedTemporaryFile(delete=True) as tmp_file:
            with open(tmp_file.name, "wb") as fd:
                for chunk in response["Body"].iter_chunks():
                    fd.write(chunk)

            tmp_file.flush()
            temp_file = files.File(tmp_file, name="{self.project_name}.tar",)
            AlgorithmImage.objects.create(algorithm=algorithm, image=temp_file)
        return temp_file
