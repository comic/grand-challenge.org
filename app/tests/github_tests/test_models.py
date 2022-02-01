import pytest

from grandchallenge.github.models import GitHubWebhookMessage


@pytest.mark.parametrize(
    "check_result,expected_keys,expected_oss",
    (
        ({}, set(), False),
        ({"licenses": []}, set(), False),
        ({"licenses": [{"key": "apache-2.0"}]}, {"apache-2.0"}, True),
        (
            {"licenses": [{"key": "apache-2.0"}, {"key": "mit"}]},
            {"apache-2.0", "mit"},
            True,
        ),
        (
            {"licenses": [{"key": "apache-2.0"}, {"key": "whatever"}]},
            {"apache-2.0", "whatever"},
            False,
        ),
        (
            {"licenses": [{"key": "apache-2.0"}, {"notakey": "whatever"}]},
            {"apache-2.0", None},
            False,
        ),
    ),
)
def test_license_keys(check_result, expected_keys, expected_oss):
    ghwm = GitHubWebhookMessage()
    ghwm.license_check_result = check_result

    assert ghwm.license_keys == expected_keys
    assert ghwm.has_open_source_license == expected_oss
