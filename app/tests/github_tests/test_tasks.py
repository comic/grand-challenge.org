import subprocess
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils.timezone import now

from grandchallenge.github.models import CloneStatusChoices, GitHubUserToken
from grandchallenge.github.tasks import (
    cleanup_expired_tokens,
    get_zipfile,
    refresh_expiring_user_tokens,
)
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.github_tests.factories import (
    GitHubUserTokenFactory,
    GitHubWebhookMessageFactory,
)


@pytest.mark.django_db
@patch("grandchallenge.github.tasks.get_repo_url")
def test_get_zipfile(get_repo_url):
    get_repo_url.return_value = "https://x-access-token:some-token@github.com/DIAGNijmegen/rse-panimg-does-not-exist"

    # repo won't be cloned without linked algorithm
    ghwm = GitHubWebhookMessageFactory()
    assert ghwm.clone_status == CloneStatusChoices.PENDING
    get_zipfile(pk=ghwm.pk)
    ghwm.refresh_from_db()
    assert ghwm.clone_status == CloneStatusChoices.NOT_APPLICABLE
    assert ghwm.zipfile.name == ""

    _ = AlgorithmFactory(repo_name="DIAGNijmegen/rse-panimg")
    ghwm = GitHubWebhookMessageFactory()
    assert ghwm.clone_status == CloneStatusChoices.PENDING
    with pytest.raises(subprocess.CalledProcessError):
        get_zipfile(pk=ghwm.pk)

    ghwm.refresh_from_db()
    assert ghwm.zipfile.name == ""
    assert "Authentication failed for" in ghwm.stdout
    assert ghwm.clone_status == CloneStatusChoices.FAILURE

    ghwm2 = GitHubWebhookMessageFactory()
    assert ghwm2.clone_status == CloneStatusChoices.PENDING
    get_repo_url.return_value = "https://github.com/DIAGNijmegen/rse-panimg"
    get_zipfile(pk=ghwm2.pk)
    assert ghwm2.license_keys == set()

    ghwm2.refresh_from_db()
    assert ghwm2.clone_status == CloneStatusChoices.SUCCESS
    assert "diagnijmegen-rse-panimg-v0-4-2" in ghwm2.zipfile.name
    assert ghwm2.license_keys == {"apache-2.0"}
    assert ghwm2.has_open_source_license is True

    # check that task only runs once
    with pytest.raises(RuntimeError) as error:
        get_zipfile(pk=ghwm2.pk)

    assert "Clone status was not pending" in str(error)


@pytest.mark.django_db
def test_cleanup_expired_tokens():
    t1 = GitHubUserTokenFactory()
    t2 = GitHubUserTokenFactory()

    t2.refresh_token_expires = now() - timedelta(days=1)
    t2.save()

    assert GitHubUserToken.objects.count() == 2

    cleanup_expired_tokens()

    assert GitHubUserToken.objects.get() == t1


@pytest.mark.django_db
def test_refresh_expiring_user_tokens(django_capture_on_commit_callbacks):
    t1, t2, t3 = GitHubUserTokenFactory.create_batch(3)

    t1.refresh_token_expires = now() + timedelta(days=180)
    t1.save()

    t2.refresh_token_expires = now() - timedelta(days=1)
    t2.save()

    t3.refresh_token_expires = now() + timedelta(days=2)
    t3.save()

    with django_capture_on_commit_callbacks() as callbacks:
        refresh_expiring_user_tokens()

    assert len(callbacks) == 1
    assert (
        repr(callbacks[0])
        == f"<bound method Signature.apply_async of grandchallenge.github.tasks.refresh_user_token(pk={t3.pk})>"
    )
