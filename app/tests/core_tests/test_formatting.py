from subprocess import call, run


def test_code_is_black():
    res = call(
        ["black", "--check", "--config", "/opt/poetry/pyproject.toml", "/app"]
    )
    assert res == 0


def test_flake8_passes():
    res = run(["flake8", "--config=/home/django/setup.cfg", "/app"])
    assert res.returncode == 0
