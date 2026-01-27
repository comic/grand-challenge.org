import shutil
import sys
import tempfile
import time
from concurrent.futures import Future
from functools import partial
from multiprocessing import Process
from pathlib import Path
from unittest import mock

import psutil
import pytest


@pytest.fixture(scope="module")
def helpers():
    """
    Fixture that renders the helpers.py.template to a real Python module
    and makes it importable for both parent and child processes.
    """
    # Create a temporary directory and copy the template as a real Python module
    temp_dir = tempfile.mkdtemp()
    template_path = Path(
        "grandchallenge/forge/templates/forge/partials/example_evaluation_method/helpers.py.template"
    )
    helpers_path = Path(temp_dir) / "helpers.py"
    shutil.copy(template_path, helpers_path)

    # Add temp directory to sys.path so child processes can import it
    sys.path.insert(0, temp_dir)

    # Now import it normally
    import helpers as helpers_module

    yield helpers_module

    # Cleanup: remove from sys.path and delete temp directory
    sys.path.remove(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def working_process(p):
    if p["pk"] == "prediction1":
        time.sleep(2)
    return f"{p['pk']} result"


def failing_process(*_):
    raise RuntimeError("Simulated Failing Process")


def child_process():
    while True:
        print("Child busy")
        time.sleep(1)


def child_spawning_process(*_):
    child = Process(target=child_process)
    child.start()
    return "Done"


def forever_process(*_):
    while True:
        time.sleep(1)


def stop_children(process_pid, interval):
    stopped = False
    while not stopped:
        process = psutil.Process(process_pid)
        children = process.children(recursive=True)
        if children:
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass  # Not a problem
            stopped = True
        time.sleep(interval)


def fail_on_prediction_2(p):
    if p["pk"] == "prediction2":
        raise RuntimeError("Simulated failure")
    else:
        time.sleep(10)  # Long sleep: should be cancelled/killed
        return f"{p['pk']} result"


@pytest.mark.timeout(4)
@pytest.mark.forge_integration
def test_prediction_processing(helpers):
    predictions = [{"pk": "prediction1"}, {"pk": "prediction2"}]
    result = helpers.run_prediction_processing(
        fn=working_process, predictions=predictions
    )
    assert {"prediction1 result", "prediction2 result"} == set(result)


@pytest.mark.timeout(4)
@pytest.mark.forge_integration
def test_prediction_processing_error(helpers):
    predictions = [
        {"pk": "prediction1"}
    ]  # Use one prediction for reproducibility
    with pytest.raises(helpers.PredictionProcessingError):
        helpers.run_prediction_processing(
            fn=failing_process, predictions=predictions
        )


@pytest.mark.timeout(4)
@pytest.mark.forge_integration
def test_prediction_processing_killing_of_child_processes(helpers):
    # If something goes wrong, this test could deadlock
    # 5 seconds should be more than enough

    predictions = [{"pk": "prediction1"}, {"pk": "prediction2"}]
    result = helpers.run_prediction_processing(
        fn=child_spawning_process, predictions=predictions
    )

    # The above call returning already shows that it correctly terminates
    # child processes, just for sanity:
    assert len(result) == len(predictions)


@pytest.mark.timeout(4)
@pytest.mark.forge_integration
def test_prediction_processing_catching_killing_of_child_processes(helpers):
    predictions = [{"pk": "prediction1"}, {"pk": "prediction2"}]

    child_stopper = None

    # Set up the fake child murder scene
    old_func = helpers._start_pool_worker

    def add_child_terminator(*args, **kwargs):
        process = old_func(*args, **kwargs)
        nonlocal child_stopper
        child_stopper = Process(
            target=partial(stop_children, process.pid, 0.5)
        )
        child_stopper.start()
        return process

    try:
        with mock.patch.object(
            helpers,
            "_start_pool_worker",
            add_child_terminator,
        ):
            with pytest.raises(helpers.PredictionProcessingError):
                helpers.run_prediction_processing(
                    fn=forever_process, predictions=predictions
                )
    finally:
        if child_stopper and child_stopper.is_alive():
            child_stopper.terminate()


@pytest.mark.timeout(4)
@pytest.mark.forge_integration
def test_prediction_processing_canceling_processes_correctly(helpers):
    predictions = [
        {"pk": "prediction1"},
        {"pk": "prediction2"},  # <- Should fail at this
        {"pk": "prediction3"},
        {"pk": "prediction4"},
    ]
    with mock.patch.object(
        helpers,
        "get_max_workers",
        lambda: 2,
    ):
        with pytest.raises(helpers.PredictionProcessingError) as exc:
            helpers.run_prediction_processing(
                fn=fail_on_prediction_2,
                predictions=predictions,
            )

        # Returning here on time is sufficient to ensure that things work as intended
        # Sanity: check that there is indeed only
        assert len(exc.value.predictions) == 1


@pytest.mark.forge_integration
def test_collect_errors(helpers):

    future0 = Future()  # Finished no exception
    future0.set_running_or_notify_cancel()
    future0.set_result("foo")
    assert future0.done()

    future1 = Future()  # Finished with exception
    future1.set_running_or_notify_cancel()
    future1.set_exception(RuntimeError("Simulated failure"))
    assert future1.done()

    future2 = Future()  # Running
    future2.set_running_or_notify_cancel()
    assert future2.running()

    future3 = Future()  # Canceled
    future3.cancel()
    assert future3.cancelled()

    future4 = Future()  # Pending
    assert not any([future4.done(), future4.running(), future4.cancelled()])

    future_to_predictions = {
        future0: {"pk": "prediction0"},
        future1: {"pk": "prediction1"},
        future2: {"pk": "prediction2"},
        future3: {"pk": "prediction3"},
        future4: {"pk": "prediction4"},
    }

    errors = {}
    helpers._collect_errors(future_to_predictions, errors)

    assert set(errors.keys()) == {"prediction1"}
