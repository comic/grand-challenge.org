from subprocess import run


def test_black():
    res = run(
        ["black", "--check", "--config", "/opt/poetry/pyproject.toml", "/app"]
    )
    assert res.returncode == 0


def test_flake8():
    res = run(["flake8", "--config=/home/django/setup.cfg", "/app"])
    assert res.returncode == 0
