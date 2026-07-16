import glob
import importlib
import json
import os
import zipfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from grandchallenge.forge.forge import (
    generate_example_algorithm,
    generate_example_evaluation,
    generate_phase_pack,
    generate_upload_to_archive_script,
)
from grandchallenge.forge.models import ForgePhase
from tests.forge_tests.utils import (
    _test_script_run,
    add_numerical_slugs,
    mocked_binaries,
    phase_context_factory,
    zipfile_to_filesystem,
)


def test_maximum_path_length():
    phase = phase_context_factory()
    # Set a long slug to test maximum path length
    phase["slug"] = "a" * 50  # Typical max length for a slug
    phase["algorithm_interfaces"][0]["inputs"][0]["relative_path"] = (
        "b" * 65  # Maximum length current relative path
    )

    # Windows has a maximum path length of 260 characters
    windows_max_path_length = 260
    typical_download_path_length = len("C:\\Users\\Username\\Downloads")

    max_path_length = windows_max_path_length - typical_download_path_length

    with zipfile.ZipFile(BytesIO(), "w") as zip_file:
        generate_phase_pack(
            output_zip_file=zip_file,
            target_zpath=Path("/"),
            phase=ForgePhase(**phase),
        )

        for file in zip_file.filelist:
            assert (
                len(file.filename) <= max_path_length
            ), f"Path {file.filename} exceeds maximum characters"


def test_for_pack_content(tmp_path):
    testrun_zpath = Path(str(uuid4()))
    phase = phase_context_factory()

    with zipfile_to_filesystem(
        output_path=tmp_path, preserve_permissions=False
    ) as zip_file:
        generate_phase_pack(
            output_zip_file=zip_file,
            target_zpath=testrun_zpath,
            phase=ForgePhase(**phase),
        )

    pack_path = tmp_path / testrun_zpath

    assert (pack_path / "README.md").exists()

    assert (pack_path / "upload_to_archive").exists()

    assert (pack_path / "example_algorithm").exists()
    for idx, interface in enumerate(phase["algorithm_interfaces"]):
        for input in interface["inputs"]:
            expected_file = (
                pack_path
                / "example_algorithm"
                / "test"
                / "input"
                / f"interf{idx}"
                / input["relative_path"]
            )
            assert expected_file.exists()

    eval_path = pack_path / "example_evaluation_method"
    assert eval_path.exists()
    eval_input_path = eval_path / "test" / "input"
    assert (eval_input_path / "predictions.json").exists()
    for input in phase["evaluation_additional_inputs"]:
        expected_file = eval_input_path / input["relative_path"]
        assert expected_file.exists()


def directly_import_module(name, path):
    """Returns the named Python module loaded from the path"""
    assert path.exists()
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


@contextmanager
def change_directory(new_path):
    # Save the current working directory
    current_path = os.getcwd()

    try:
        # Change the working directory
        os.chdir(new_path)
        yield
    finally:
        # Change back to the original working directory
        os.chdir(current_path)


@pytest.mark.parametrize(
    "phase_context",
    [
        phase_context_factory(),
        add_numerical_slugs(phase_context_factory()),
    ],
)
def test_pack_upload_to_archive_script(phase_context, tmp_path):
    """Checks if the upload to archive script works as intended"""
    testrun_zpath = Path(str(uuid4()))

    with zipfile_to_filesystem(
        output_path=tmp_path, preserve_permissions=False
    ) as zip_file:
        generate_upload_to_archive_script(
            output_zip_file=zip_file,
            target_zpath=testrun_zpath,
            context_object=ForgePhase(**phase_context),
        )

    script_dir = tmp_path / testrun_zpath

    with change_directory(script_dir):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_gcapi = MagicMock()
        mock_gcapi.Client.return_value = mock_client

        with patch.dict("sys.modules", {"gcapi": mock_gcapi}):
            # Load the script as a module
            upload_files = directly_import_module(
                name="upload_files",
                path=script_dir / "upload_files.py",
            )

            # Run the script, but noop print
            def debug_print(_):
                pass

            with patch("builtins.print", debug_print):
                upload_files.main()

        # Assert that it reaches out via gcapi
        assert mock_gcapi.Client.call_count == 1

        # Two interface, each with 3 cases
        assert mock_client.add_case_to_archive.call_count == 2 * 3


@pytest.mark.forge_integration
def test_pack_example_algorithm_run_permissions(tmp_path):
    testrun_zpath = Path(str(uuid4()))
    phase_context = phase_context_factory()

    with zipfile_to_filesystem(output_path=tmp_path) as zip_file:
        generate_example_algorithm(
            context_object=ForgePhase(**phase_context),
            output_zip_file=zip_file,
            target_zpath=testrun_zpath,
        )

    algorithm_path = tmp_path / testrun_zpath

    # Run it twice to ensure all permissions are correctly handled
    for _ in range(0, 2):
        _test_script_run(script_path=algorithm_path / "do_test_run.sh")


@pytest.mark.parametrize(
    "phase_context",
    [
        phase_context_factory(),
        add_numerical_slugs(phase_context_factory()),
    ],
)
@pytest.mark.forge_integration
def test_pack_example_algorithm_run(phase_context, tmp_path):
    testrun_zpath = Path(str(uuid4()))

    with zipfile_to_filesystem(output_path=tmp_path) as zip_file:
        generate_example_algorithm(
            context_object=ForgePhase(**phase_context),
            output_zip_file=zip_file,
            target_zpath=testrun_zpath,
        )

    algorithm_path = tmp_path / testrun_zpath

    _test_script_run(script_path=algorithm_path / "do_test_run.sh")

    for idx, interface in enumerate(phase_context["algorithm_interfaces"]):
        output_dir = algorithm_path / "test" / "output" / f"interf{idx}"
        # Check if output is generated
        for output in interface["outputs"]:
            expected_file = output_dir / output["relative_path"]
            assert expected_file.exists()


@pytest.mark.forge_integration
def test_pack_example_algorithm_save(tmp_path):
    testrun_zpath = Path(str(uuid4()))
    phase_context = phase_context_factory()

    with zipfile_to_filesystem(output_path=tmp_path) as zip_file:
        generate_example_algorithm(
            context_object=ForgePhase(**phase_context),
            output_zip_file=zip_file,
            target_zpath=testrun_zpath,
        )

    algorithm_path = tmp_path / testrun_zpath

    with mocked_binaries():
        _test_script_run(script_path=algorithm_path / "do_save.sh")

    # Check if saved image exists
    tar_filename = f"example_algorithm_{phase_context['slug']}"
    pattern = str(algorithm_path / f"{tar_filename}_*.tar.gz")
    matching_files = glob.glob(pattern)
    assert len(matching_files) == 1, (
        f"Example do_save.sh does not generate the exported "
        f"image matching: {pattern}"
    )


@pytest.mark.forge_integration
def test_pack_example_evaluation_run_permissions(tmp_path):
    testrun_zpath = Path(str(uuid4()))

    with zipfile_to_filesystem(output_path=tmp_path) as zip_file:
        generate_example_evaluation(
            context_object=ForgePhase(**phase_context_factory()),
            output_zip_file=zip_file,
            target_zpath=testrun_zpath,
        )

    evaluation_path = tmp_path / testrun_zpath

    # Run it twice to ensure all permissions are correctly handled
    for _ in range(0, 2):
        _test_script_run(script_path=evaluation_path / "do_test_run.sh")


@pytest.mark.parametrize(
    "phase_context, num_metrics",
    (
        (
            phase_context_factory(),
            6,
        ),
        (
            add_numerical_slugs(phase_context_factory()),
            6,
        ),
        # Just the algorithm interfaces
        (
            phase_context_factory(
                evaluation_additional_inputs=[],
                evaluation_additional_outputs=[],
            ),
            6,
        ),
        # Just the evaluation additional outputs
        (
            phase_context_factory(
                algorithm_interfaces=[],
                evaluation_additional_inputs=[],
            ),
            0,
        ),
        # Just the evaluation additional inputs
        (
            phase_context_factory(
                algorithm_interfaces=[],
                evaluation_additional_outputs=[],
            ),
            0,
        ),
    ),
)
@pytest.mark.forge_integration
def test_pack_example_evaluation_run(phase_context, num_metrics, tmp_path):
    testrun_zpath = Path(str(uuid4()))

    with zipfile_to_filesystem(output_path=tmp_path) as zip_file:
        generate_example_evaluation(
            context_object=ForgePhase(**phase_context),
            output_zip_file=zip_file,
            target_zpath=testrun_zpath,
        )

    evaluation_path = tmp_path / testrun_zpath
    output_dir = evaluation_path / "test" / "output"
    metrics_file = evaluation_path / "test" / "output" / "metrics.json"

    # Sanity
    assert not metrics_file.exists()
    for output in phase_context["evaluation_additional_outputs"]:
        expected_file = output_dir / output["relative_path"]
        assert not expected_file.exists()

    _test_script_run(script_path=evaluation_path / "do_test_run.sh")

    assert metrics_file.exists()

    # Read and validate the contents of the generated metrics.json file
    with open(metrics_file) as f:
        metrics_data = json.load(f)
    assert len(metrics_data["results"]) == num_metrics

    # Check if the additional outputs are generated
    for output in phase_context["evaluation_additional_outputs"]:
        expected_file = output_dir / output["relative_path"]
        assert expected_file.exists()


@pytest.mark.forge_integration
def test_pack_example_evaluation_save(tmp_path):
    testrun_zpath = Path(str(uuid4()))
    phase_context = phase_context_factory()

    with zipfile_to_filesystem(output_path=tmp_path) as zip_file:
        generate_example_evaluation(
            context_object=ForgePhase(**phase_context),
            output_zip_file=zip_file,
            target_zpath=testrun_zpath,
        )

    evaluation_path = tmp_path / testrun_zpath

    with mocked_binaries():
        _test_script_run(script_path=evaluation_path / "do_save.sh")

    # Check if saved image exists
    tar_filename = f"example_evaluation_{phase_context['slug']}"
    pattern = str(evaluation_path / f"{tar_filename}_*.tar.gz")
    matching_files = glob.glob(pattern)
    assert len(matching_files) == 1, (
        f"Example do_save.sh does not generate the exported "
        f"image matching: {pattern}"
    )
