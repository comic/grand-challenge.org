import uuid

from comic.celery import debug_task
from evaluation.tasks import evaluate_submission


def test_debug_task():
    # Just ensure that the debug task runs
    res = debug_task.delay()
    res.get(timeout=5)
    assert res.state == 'SUCCESS'


def test_start_sibling_container():
    res = evaluate_submission.delay(job_id=uuid.uuid4())
    assert res.get(timeout=15) == 'hello world\n'
