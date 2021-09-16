import subprocess
from unittest.mock import patch

import pytest

from grandchallenge.github.tasks import get_zipfile
from tests.github_tests.factories import GitHubWebhookMessageFactory


@pytest.mark.django_db
@patch("grandchallenge.github.tasks.get_repo_url")
def test_get_zipfile(get_repo_url):
    get_repo_url.return_value = "https://x-access-token:some-token@github.com/DIAGNijmegen/rse-panimg-does-not-exist"

    ghwm = GitHubWebhookMessageFactory()
    with pytest.raises(subprocess.CalledProcessError):
        get_zipfile(pk=ghwm.pk)

    ghwm.refresh_from_db()
    assert ghwm.zipfile.name == ""
    assert "returned non-zero exit status" in ghwm.error

    get_repo_url.return_value = "https://github.com/DIAGNijmegen/rse-panimg"
    get_zipfile(pk=ghwm.pk)

    ghwm.refresh_from_db()
    assert ghwm.zipfile is not None
    assert "diagnijmegen-rse-panimg-v0-4-2" in ghwm.zipfile.name
    assert ghwm.has_open_source_license is True
    assert ghwm.license_check_result == "Apache License 2.0"
