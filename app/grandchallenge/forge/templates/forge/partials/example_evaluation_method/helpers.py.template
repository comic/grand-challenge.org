import logging
import multiprocessing
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager, Process
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


def setup_logger(level=logging.INFO):
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="[%(levelname)s]%(name)s: %(message)s",
        stream=sys.stdout,
    )


class PredictionProcessingError(Exception):
    def __init__(
        self,
        predictions,
        message="One or more errors occurred during prediction processing.",
    ):
        self.predictions = predictions
        super().__init__(message)


def log_processing_report(futures):
    total = len(futures)
    running = 0
    succeeded = 0

    for future in futures:
        print
        if future.running():
            running += 1
        elif future.done() and future.exception() is None:
            succeeded += 1

    report = "Progress Report:"
    report += f" {int(succeeded / total * 100)}%"
    if succeeded != total:
        report += f" ( {succeeded}/{total}"
        report += f", Running: {running} )"
    logger.info(report)


def get_max_workers():
    """
    Returns the maximum number of concurrent workers

    The optimal number of workers ultimately depends on how many resources
    each process will call upon.

    To limit this, update the Dockerfile GRAND_CHALLENGE_MAX_WORKERS
    """

    environ_cpu_limit = os.getenv("GRAND_CHALLENGE_MAX_WORKERS")
    cpu_count = multiprocessing.cpu_count()
    return min(
        [
            int(environ_cpu_limit or cpu_count),
            cpu_count,
        ]
    )


def run_prediction_processing(*, fn, predictions):
    """
    Processes predictions in a separate process.

    This takes child processes into account:
    - if any child process is terminated, all prediction processing will abort
    - after prediction processing is done, all child processes are terminated

    Note that the results are returned in completing order.

    Parameters
    ----------
    fn : function
        Function to execute that will process each prediction

    predictions : list
        List of predictions.

    Returns
    -------
    A list of results
    """
    with Manager() as manager:
        results = manager.dict()
        errors = manager.dict()

        pool_worker = _start_pool_worker(
            fn=fn,
            predictions=predictions,
            max_workers=get_max_workers(),
            results=results,
            errors=errors,
        )
        try:
            pool_worker.join()
        finally:
            pool_worker.terminate()

        if errors:
            for prediction_pk, tb_str in errors.items():
                print(
                    f"Error in prediction: {prediction_pk}\n{tb_str}",
                    file=sys.stderr,
                )

            raise PredictionProcessingError(errors.keys())

        return list(results.values())


def _start_pool_worker(fn, predictions, max_workers, results, errors):
    process = Process(
        target=_pool_worker,
        name="PredictionProcessing",
        kwargs=dict(
            fn=fn,
            predictions=predictions,
            max_workers=max_workers,
            results=results,
            errors=errors,
        ),
    )
    process.start()

    return process


def _pool_worker(*, fn, predictions, max_workers, results, errors):
    executor = ProcessPoolExecutor(max_workers=max_workers)
    try:
        # Submit the processing tasks of the predictions
        future_to_predictions = {}
        for p in predictions:
            future = executor.submit(fn, p)
            future_to_predictions[future] = p

        for future in as_completed(future_to_predictions):
            log_processing_report(futures=future_to_predictions.keys())
            try:
                result = future.result()
            except Exception:
                break
            else:
                prediction = future_to_predictions[future]
                prediction_pk = prediction["pk"]
                results[prediction_pk] = result
    finally:
        executor.shutdown(
            wait=False,  # Do not wait for any resources to free themselves
            cancel_futures=True,
        )

    _collect_errors(future_to_predictions, errors)

    # Aggressively terminate any child processes
    _terminate_child_processes()


def _collect_errors(future_to_predictions, errors):
    # Collect any failures that occurred during processing
    # Workaround for https://github.com/python/cpython/issues/136655
    # Which prevents us relying solely on as_completed to catch exceptions
    def failed_futures():
        for f, p in future_to_predictions.items():
            if f.done() and not f.cancelled():
                exc = f.exception()
                if exc is not None:
                    yield p, exc

    for prediction, exc in failed_futures():
        tb_exception = traceback.TracebackException.from_exception(exc)

        # Cannot pickle a stack trace, so we render it here
        formatted_tb = "".join(tb_exception.format())
        prediction_pk = prediction["pk"]
        errors[prediction_pk] = formatted_tb


def _terminate_child_processes():
    process = psutil.Process(os.getpid())
    children = process.children(recursive=True)
    for child in children:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass  # Not a problem

    # Wait for processes to terminate
    _, still_alive = psutil.wait_procs(children, timeout=5)

    # Forcefully kill any remaining processes
    for p in still_alive:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass  # That is fine

    # Finally, prevent zombies by waiting for all child processes
    try:
        os.waitpid(-1, 0)
    except ChildProcessError:
        pass  # No child processes, that if fine


def tree(dir_path: Path, prefix: str = ""):
    """A recursive generator, given a directory Path object
    will yield a visual tree structure line by line
    with each line prefixed by the same characters
    """
    space = "    "
    branch = "│   "
    # pointers:
    tee = "├── "
    last = "└── "

    contents = list(dir_path.iterdir())
    # contents each get pointers that are ├── with a final └── :
    pointers = [tee] * (len(contents) - 1) + [last]
    for pointer, path in zip(pointers, contents, strict=True):
        yield prefix + pointer + path.name
        if path.is_dir():  # extend the prefix and recurse:
            extension = branch if pointer == tee else space
            # i.e. space because last, └── , above so no more |
            yield from tree(path, prefix=prefix + extension)
