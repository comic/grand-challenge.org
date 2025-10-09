import asyncio
import logging
from pathlib import Path

import aioboto3
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.management.base import BaseCommand

from grandchallenge.components.backends.base import (
    ASYNC_BOTO_CONFIG,
    CONCURRENCY,
)

logger = logging.getLogger(__name__)

CONTENT_TYPES = {
    "": "application/octet-stream",
    ".css": "text/css",
    ".eot": "application/vnd.ms-fontobject",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".jpg": "image/jpeg",
    ".js": "application/javascript",
    ".json": "application/json",
    ".map": "application/json",
    ".md": "text/markdown",
    ".mjs": "application/javascript",
    ".png": "image/png",
    ".rst": "text/x-rst",
    ".scss": "text/x-scss",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".txt": "text/plain",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


async def s3_upload_file(
    *, filename, bucket, key, content_type, cache_control, semaphore, s3_client
):
    async with semaphore:
        await s3_client.upload_file(
            Filename=filename,
            Bucket=bucket,
            Key=key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": cache_control,
            },
        )
        logger.info(f"Uploaded s3://{bucket}/{key}")


class Command(BaseCommand):
    help = "Uploads static files to an S3 bucket"

    def add_arguments(self, parser):
        parser.add_argument(
            "--bucket", type=str, required=True, help="S3 bucket name"
        )

    def handle(self, *args, **options):
        bucket_name = options["bucket"]

        files_to_upload = self._get_files_to_upload()

        if not files_to_upload:
            raise RuntimeError("No files found to upload")

        self.stdout.write(
            f"Found {len(files_to_upload)} files to upload to {bucket_name}"
        )

        self._upload_files(
            bucket_name=bucket_name,
            files=files_to_upload,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully uploaded {len(files_to_upload)} files to {bucket_name}"
            )
        )

    def _get_files_to_upload(self) -> list[Path]:
        files = []

        for path in Path(settings.STATIC_ROOT).rglob("*"):
            if path.is_dir() or path.is_symlink():
                continue
            files.append(path)

        return files

    @async_to_sync
    async def _upload_files(
        self,
        *,
        bucket_name: str,
        files: list[Path],
    ) -> None:
        semaphore = asyncio.Semaphore(CONCURRENCY)
        session = aioboto3.Session()

        async with session.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            config=ASYNC_BOTO_CONFIG,
        ) as s3_client:
            async with asyncio.TaskGroup() as task_group:
                for file in files:
                    relative_path = file.relative_to(
                        Path(settings.STATIC_ROOT).parent
                    )

                    task_group.create_task(
                        s3_upload_file(
                            filename=str(file),
                            bucket=bucket_name,
                            key=str(relative_path),
                            content_type=CONTENT_TYPES[file.suffix.lower()],
                            cache_control=settings.PUBLIC_FILE_CACHE_CONTROL,
                            semaphore=semaphore,
                            s3_client=s3_client,
                        )
                    )
