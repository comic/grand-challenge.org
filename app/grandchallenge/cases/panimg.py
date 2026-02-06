import shlex
import subprocess
from pathlib import Path

from django.utils._os import safe_join
from pydantic import TypeAdapter

from grandchallenge.cases.panimg_models import (
    PanImgFile,
    PanImgResult,
    PostProcessorResult,
)


def convert(*, input_directory, output_directory, builders):
    builders_command = []
    for builder in builders:
        builders_command.extend(["--image-builder", builder])

    panimg_command = shlex.join(
        [
            "panimg",
            "convert",
            "--input-dir",
            str(input_directory.resolve()),
            "--output-dir",
            str(output_directory.resolve()),
            *builders_command,
            "--no-post-processing",
        ]
    )

    cli_result = subprocess.run(
        [
            "bash",
            "-c",
            f"source /opt/virtualenvs/panimg/bin/activate && {panimg_command}",
        ],
        text=True,
        check=True,
        capture_output=True,
    )

    panimg_result: PanImgResult = TypeAdapter(PanImgResult).validate_json(
        cli_result.stdout.splitlines()[-1]
    )

    return panimg_result


def post_process(*, image_file, output_directory):
    panimg_file = _download_image_file(
        image_file=image_file, output_directory=output_directory
    )

    panimg_command = shlex.join(
        [
            "panimg",
            "post-process",
            "--image-id",
            str(panimg_file.image_id),
            "--image-type",
            panimg_file.image_type,
            "--input-file",
            str(panimg_file.file),
            "--post-processor",
            "DZI",
        ]
    )

    cli_result = subprocess.run(
        [
            "bash",
            "-c",
            f"source /opt/virtualenvs/panimg/bin/activate && {panimg_command}",
        ],
        text=True,
        check=True,
        capture_output=True,
    )

    post_processor_result: PostProcessorResult = TypeAdapter(
        PostProcessorResult
    ).validate_json(cli_result.stdout.splitlines()[-1])

    return post_processor_result


def _download_image_file(*, image_file, output_directory):
    """
    Downloads an image file to a directory

    Returns a PanImgFiles that point to the local files
    """
    dest = safe_join(output_directory, image_file.file.name)

    panimg_file = PanImgFile(
        image_id=image_file.image.pk,
        image_type=image_file.image_type,
        file=dest,
    )

    # Safe to create directories as safe_join has been used
    Path(dest).parent.mkdir(parents=True, exist_ok=True)

    with image_file.file.open("rb") as fs, open(dest, "wb") as fd:
        for chunk in fs.chunks():
            fd.write(chunk)

    return panimg_file
