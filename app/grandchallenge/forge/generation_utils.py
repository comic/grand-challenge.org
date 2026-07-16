import json
import logging
import time
import uuid
import zipfile
from pathlib import Path

import black
import isort
from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from pydantic import BaseModel

from grandchallenge.forge.models import ForgeSocketValue

FORGE_MODULE_PATH = Path(__file__).parent
FORGE_RESOURCES_PATH = FORGE_MODULE_PATH / "resources"
FORGE_PARTIALS_PATH = FORGE_MODULE_PATH / "templates" / "forge" / "partials"


logger = logging.getLogger(__name__)


def generate_socket_value_stub_file(*, output_zip_file, target_zpath, socket):
    """Creates a stub based on a component interface"""
    if socket.has_example_value:
        zinfo = zipfile.ZipInfo(str(target_zpath))
        output_zip_file.writestr(
            zinfo,
            json.dumps(
                socket.example_value,
                indent=4,
            ),
        )
        return target_zpath

    # Copy over an example
    if socket.is_json_kind:
        output_zip_file.write(
            FORGE_RESOURCES_PATH / "example.json",
            arcname=str(target_zpath),
        )
    elif socket.is_dicom_image_kind:
        for indx, f in enumerate(
            [  # Note: out of order on purpose: order should come from reading DICOM tags
                "example_2.dcm",
                "example_1.dcm",
                "example_3.dcm",
            ]
        ):
            assert (FORGE_RESOURCES_PATH / f).exists()
            output_zip_file.write(
                FORGE_RESOURCES_PATH / f,
                arcname=str(
                    target_zpath
                    / f"1.2.826.0.1.3680043.10.1666.{indx + 1}.dcm"
                ),
            )
    elif socket.is_panimg_kind:
        output_zip_file.write(
            FORGE_RESOURCES_PATH / "example.mha",
            arcname=str(target_zpath / f"{str(uuid.uuid4())}.mha"),
        )

    else:
        output_zip_file.write(
            FORGE_RESOURCES_PATH / "example.txt",
            arcname=str(target_zpath),
        )

    return target_zpath


def socket_to_socket_value(socket):
    if socket.is_image_kind:
        return ForgeSocketValue(
            image={
                "name": "the_original_filename_of_the_file_that_was_uploaded_or_image_set",
            },
            socket=socket,
        )
    elif socket.is_file_kind:
        return ForgeSocketValue(
            file=f"https://grand-challenge.org/media/some-link/{socket.relative_path}",
            socket=socket,
        )
    elif socket.is_json_kind:
        if socket.has_example_value:
            return ForgeSocketValue(
                value=socket.example_value,
                socket=socket,
            )
        else:
            return ForgeSocketValue(
                value={"some_key": "some_value"},
                socket=socket,
            )
    else:
        raise NotImplementedError


def copy_and_render(
    *,
    templates_dir_name,
    output_zip_file,
    target_zpath,
    context_object,
    extra_context=None,
):
    if not isinstance(context_object, BaseModel):
        raise ValueError("context_object must be an instance of BaseModel")

    context = {
        "object": context_object,
        "grand_challenge_forge_version": settings.COMMIT_ID,
        "use_gpus": not settings.FORGE_DISABLE_GPUS,
    }

    if extra_context:
        context.update(**extra_context)

    source_path = FORGE_PARTIALS_PATH / templates_dir_name

    if not source_path.exists():
        raise TemplateDoesNotExist(source_path)

    for root, _, files in source_path.walk():
        check_allowed_source(path=root)

        # Create relative path
        rel_path = root.relative_to(source_path)
        current_zdir = target_zpath / rel_path

        for file in sorted(files):
            source_file = root / file
            output_file = current_zdir / file

            check_allowed_source(path=source_file)

            if file.endswith(".template"):
                rendered_content = render_to_string(
                    template_name=source_file,
                    context=context,
                )

                targetfile_zpath = output_file.with_suffix("")

                if targetfile_zpath.suffix == ".py":
                    # Replace escaped characters
                    rendered_content = rendered_content.replace("&#x27;", "'")
                    rendered_content = rendered_content.replace("&quot;", '"')
                    rendered_content = rendered_content.replace("&lt;", "<")

                    # First apply isort, then black
                    rendered_content = apply_isort(rendered_content)
                    rendered_content = apply_black(rendered_content)
                else:
                    rendered_content = f"{rendered_content.strip()}\n"

                # Collect information about the file to be written to the zip file
                # (permissions, et cetera)
                zinfo = zipfile.ZipInfo.from_file(
                    source_file,
                    arcname=str(targetfile_zpath),
                )

                # Update the date time of creation, since we are technically
                # creating a new file
                # Also (partially) addresses a problem where docker build injects
                # incorrect files:
                # https://github.com/moby/buildkit/issues/4817#issuecomment-2032551066
                zinfo.date_time = time.localtime()[0:6]

                output_zip_file.writestr(zinfo, rendered_content)
            else:
                output_zip_file.write(
                    str(source_file), arcname=str(output_file)
                )


def check_allowed_source(path):
    if FORGE_PARTIALS_PATH.resolve() not in path.resolve().parents:
        raise PermissionError(
            f"Only files under {FORGE_PARTIALS_PATH} are allowed "
            "to be copied or rendered"
        )


def apply_isort(content):
    # Format rendered Python code string using isort
    result = isort.code(
        content,
        config=isort.Config(
            profile="black",
            float_to_top=True,
        ),
    )
    return result


def apply_black(content):
    # Format rendered Python code string using black
    result = black.format_str(
        content,
        mode=black.Mode(),
    )
    return result
