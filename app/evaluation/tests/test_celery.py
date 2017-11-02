import uuid

import pytest
from evaluation.tasks import evaluate_submission

# TODO - This integration test does not work right now as celery cannot connect
# to the django test database.
@pytest.mark.skip
@pytest.mark.integration
def test_start_sibling_container():
    res = evaluate_submission.delay(job_id=uuid.uuid4())
    assert res.get(timeout=15) == 'hello world\n'
