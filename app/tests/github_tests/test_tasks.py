from unittest.mock import patch

import pytest

from grandchallenge.github.tasks import get_zipfile
from tests.github_tests.factories import GitHubWebhookMessageFactory


@pytest.mark.django_db
@patch(
    "grandchallenge.github.tasks.get_repo_url",
    return_value="https://github.com/DIAGNijmegen/rse-panimg",
)
def test_get_zipfile(get_repo_url):
    ghwm = GitHubWebhookMessageFactory()
    get_zipfile(pk=ghwm.pk)

    ghwm.refresh_from_db()
    assert ghwm.zipfile is not None
    assert "diagnijmegen-rse-panimg-v0-4-2" in ghwm.zipfile.name
    assert ghwm.has_open_source_license is True
    assert ghwm.license_check_result == "Apache License 2.0"
