import pytest
from celery import shared_task
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from tests.factories import UploadSessionFactory


@pytest.mark.django_db
def test_linked_task_called_with_session_pk(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    called = {}

    @shared_task
    def local_linked_task(*_, **kwargs):
        called.update(**kwargs)

    session = UploadSessionFactory()

    with capture_on_commit_callbacks(execute=True):
        session.process_images(linked_task=local_linked_task.signature())

    assert called == {"upload_session_pk": session.pk}
