import subprocess
from unittest.mock import patch

import pytest

from grandchallenge.github.models import CloneStatusChoices
from grandchallenge.github.tasks import get_zipfile
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.github_tests.factories import GitHubWebhookMessageFactory


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
    assert ghwm2.clone_status == CloneStatusChoices.FAILURE
    assert "diagnijmegen-rse-panimg-v0-4-2" in ghwm2.zipfile.name
    assert ghwm2.license_keys == {"apache-2.0"}
    assert ghwm2.has_open_source_license is True

    # check that task only runs once
    with pytest.raises(RuntimeError) as error:
        get_zipfile(pk=ghwm2.pk)

    assert "Clone status was not pending" in str(error)
