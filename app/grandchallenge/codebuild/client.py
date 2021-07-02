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
        self.project_name = project_name
        self.msg = msg
        self.algorithm = algorithm
        self.build_id = build_id
        if build_id is not None:
            self.build_number = build_id.split(":")[-1]

    def start_build(self, source, folder_name):
        data = self.client.start_build(
            projectName=settings.CODEBUILD_PROJECT_NAME,
            sourceLocationOverride=source,
            environmentVariablesOverride=[
                {
                    "name": "IMAGE_REPO_NAME",
                    "value": self.project_name,
                    "type": "PLAINTEXT",
                },
                {
                    "name": "IMAGE_TAG",
                    "value": self.project_name,
                    "type": "PLAINTEXT",
                },
                {
                    "name": "FOLDER_NAME",
                    "value": folder_name,
                    "type": "PLAINTEXT",
                },
            ],
        )
        self.build_id = data["build"]["id"]
        build = Build.objects.create(
            build_id=self.build_id,
            project_name=self.project_name,
            status=data["build"]["buildStatus"],
            build_config={"source": {"location": source}},
            webhook_message=self.msg,
            algorithm=self.algorithm,
        )
        return build.pk

    def get_build_status(self):
        builds = self.client.batch_get_builds(ids=[self.build_id])
        self.build = builds["builds"][0]
        return self.build["buildStatus"]

    def add_logs_for_build(self, build):
        with private_s3_storage.open(
            f"codebuild/logs/{self.build_number}.gz"
        ) as file:
            with NamedTemporaryFile(delete=True) as tmp_file:
                with open(tmp_file.name, "wb") as fd:
                    for chunk in file.chunks():
                        fd.write(chunk)

                tmp_file.flush()
                temp_file = files.File(
                    tmp_file, name=f"{self.build_number}.gz",
                )
                build.build_log = temp_file
                build.save()

    def add_image_to_algorithm(self):
        with private_s3_storage.open(
            f"codebuild/artifacts/{self.build_number}/{settings.CODEBUILD_PROJECT_NAME}/container-image.tar.gz"
        ) as file:
            with NamedTemporaryFile(delete=True) as tmp_file:
                with open(tmp_file.name, "wb") as fd:
                    for chunk in file.chunks():
                        fd.write(chunk)

                tmp_file.flush()
                temp_file = files.File(
                    tmp_file, name=f"{self.project_name}.tar",
                )
                AlgorithmImage.objects.create(
                    algorithm=self.algorithm, image=temp_file
                )
        return temp_file
