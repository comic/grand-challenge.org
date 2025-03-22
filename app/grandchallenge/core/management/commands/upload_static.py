import asyncio
import logging
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Uploads static files to an S3 bucket"

    def add_arguments(self, parser):
        parser.add_argument(
            "--bucket", type=str, required=True, help="S3 bucket name"
        )
        parser.add_argument(
            "--concurrency",
            type=int,
            default=10,
            help="Number of concurrent uploads",
        )

    def handle(self, *args, **options):
        bucket_name = options["bucket"]
        concurrency = options["concurrency"]

        try:
            s3_client = boto3.client("s3")

            files_to_upload = self._get_files_to_upload()

            if not files_to_upload:
                self.stdout.write(
                    self.style.WARNING("No files found to upload")
                )
                return

            self.stdout.write(
                f"Found {len(files_to_upload)} files to upload to {bucket_name}"
            )

            asyncio.run(
                self._upload_files(
                    s3_client=s3_client,
                    bucket_name=bucket_name,
                    files=files_to_upload,
                    concurrency=concurrency,
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully uploaded {len(files_to_upload)} files to {bucket_name}"
                )
            )

        except (BotoCoreError, ClientError) as e:
            self.stderr.write(self.style.ERROR(f"AWS Error: {str(e)}"))
            raise CommandError(f"Failed to upload files: {str(e)}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Unexpected error: {str(e)}"))
            raise CommandError(f"Failed to upload files: {str(e)}")

    def _get_files_to_upload(self) -> list[Path]:
        files = []

        for path in Path(settings.STATIC_ROOT).rglob("*"):
            if path.is_dir() or path.is_symlink():
                continue
            files.append(path)

        return files

    async def _upload_files(
        self,
        *,
        s3_client,
        bucket_name: str,
        files: list[Path],
        concurrency: int,
    ) -> None:
        semaphore = asyncio.Semaphore(concurrency)
        errors: set[str] = set()

        async def upload_file(file_path: Path) -> None:
            async with semaphore:
                relative_path = file_path.relative_to(
                    Path(settings.STATIC_ROOT).parent
                )
                s3_key = str(relative_path)

                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: s3_client.upload_file(
                            Filename=str(file_path),
                            Bucket=bucket_name,
                            Key=s3_key,
                            ExtraArgs={
                                "ContentType": self._get_content_type(
                                    file_path
                                )
                            },
                        ),
                    )
                    self.stdout.write(f"Uploaded: {s3_key}")
                except Exception as e:
                    error_msg = f"Failed to upload {s3_key}: {str(e)}"
                    errors.add(error_msg)
                    self.stderr.write(self.style.ERROR(error_msg))

        tasks = [upload_file(file_path) for file_path in files]

        await asyncio.gather(*tasks)

        if errors:
            error_count = len(errors)
            raise CommandError(
                f"Failed to upload {error_count} files. First error: {next(iter(errors))}"
            )

    def _get_content_type(self, file_path: Path) -> str:
        content_types = {
            ".br": "application/brotli",
            ".css": "text/css",
            ".eot": "application/vnd.ms-fontobject",
            ".gif": "image/gif",
            ".gz": "application/gzip",
            ".html": "text/html",
            ".ico": "image/x-icon",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".js": "application/javascript",
            ".json": "application/json",
            ".map": "application/json",
            ".md": "text/markdown",
            ".mjs": "application/javascript",
            ".otf": "font/otf",
            ".png": "image/png",
            ".rst": "text/x-rst",
            ".scss": "text/x-scss",
            ".svg": "image/svg+xml",
            ".ttf": "font/ttf",
            ".txt": "text/plain",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
        }

        suffix = file_path.suffix.lower()
        return content_types.get(suffix, "application/octet-stream")
