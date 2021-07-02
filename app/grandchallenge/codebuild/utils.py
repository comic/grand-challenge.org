from django.core.files.temp import NamedTemporaryFile
from django.template.loader import render_to_string


def get_buildspec_path(*, algorithm_name, folder_name, output_path):
    rendered = render_to_string(
        "codebuild/buildspec.yml",
        {
            "algorithm_name": algorithm_name,
            "folder_name": folder_name,
            "output_path": output_path,
        },
    )
    with NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(rendered.encode("ascii"))

    return tmp_file.name
