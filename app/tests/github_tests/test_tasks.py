import subprocess
from unittest.mock import patch

import pytest

from grandchallenge.github.models import CloneStatusChoices
from grandchallenge.github.tasks import get_zipfile
from tests.github_tests.factories import GitHubWebhookMessageFactory


@pytest.mark.django_db
@patch("grandchallenge.github.tasks.get_repo_url")
def test_get_zipfile(get_repo_url):
    get_repo_url.return_value = "https://x-access-token:some-token@github.com/DIAGNijmegen/rse-panimg-does-not-exist"

    ghwm = GitHubWebhookMessageFactory()
    assert ghwm.clone_status == CloneStatusChoices.PENDING
    with pytest.raises(subprocess.CalledProcessError):
        get_zipfile(pk=ghwm.pk)

    ghwm.refresh_from_db()
    assert ghwm.zipfile.name == ""
    assert "returned non-zero exit status" in ghwm.error
    assert ghwm.clone_status == CloneStatusChoices.FAILURE

    ghwm2 = GitHubWebhookMessageFactory()
    assert ghwm2.clone_status == CloneStatusChoices.PENDING
    get_repo_url.return_value = "https://github.com/DIAGNijmegen/rse-panimg"
    get_zipfile(pk=ghwm2.pk)

    ghwm2.refresh_from_db()
    assert ghwm2.zipfile is not None
    previous_zipfile = ghwm2.zipfile
    assert ghwm2.clone_status == CloneStatusChoices.SUCCESS
    assert "diagnijmegen-rse-panimg-v0-4-2" in ghwm2.zipfile.name
    assert ghwm2.has_open_source_license is True
    assert ghwm2.license_check_result == "Apache License 2.0"

    # check that task is idempotent
    get_zipfile(pk=ghwm2.pk)
    ghwm2.refresh_from_db()
    assert ghwm2.zipfile == previous_zipfile
