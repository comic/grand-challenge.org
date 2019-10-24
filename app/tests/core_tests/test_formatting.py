from subprocess import call


def test_code_is_black():
    res = call(
        ["black", "--check", "--config", "/opt/poetry/pyproject.toml", "/app"]
    )
    assert res == 0
