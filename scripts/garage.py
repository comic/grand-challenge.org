import subprocess

from django.conf import settings

GARAGE_CONTAINER_NAME = "grand-challengeorg-garage.localhost-1"
GARAGE_MAIN_KEY_NAME = "grand-challenge-development-key"
GARAGE_COMPONENTS_KEY_NAME = "grand-challenge-components-key"
GARAGE_WEBSITE_BUCKET_NAME = "garage"


def run():
    """Sets up the permissions on the garage buckets"""
    print("🔐 Setting up garage 🔐")

    if not settings.DEBUG:
        raise RuntimeError(
            "Skipping this command, server is not in DEBUG mode."
        )

    _setup_layout()
    _create_main_key()
    _create_buckets()
    _allow_public_access()

    print("✨ Garage set up ✨")


def _get_node_id():
    output = subprocess.check_output(
        args=[
            "docker",
            "exec",
            "-it",
            GARAGE_CONTAINER_NAME,
            "/garage",
            "node",
            "id",
            "-q",
        ],
        text=True,
    )

    return output.strip().split("@")[0]


def _setup_layout():
    node_id = _get_node_id()

    subprocess.check_call(
        args=[
            "docker",
            "exec",
            "-it",
            GARAGE_CONTAINER_NAME,
            "/garage",
            "layout",
            "assign",
            "-z",
            "dc1",
            "-c",
            "1G",
            node_id,
        ],
    )

    subprocess.check_call(
        args=[
            "docker",
            "exec",
            "-it",
            GARAGE_CONTAINER_NAME,
            "/garage",
            "layout",
            "apply",
            "--version",
            "1",
        ],
    )


def _create_main_key():
    subprocess.check_call(
        args=[
            "docker",
            "exec",
            "-it",
            GARAGE_CONTAINER_NAME,
            "/garage",
            "key",
            "import",
            "--yes",
            "-n",
            GARAGE_MAIN_KEY_NAME,
            "GKf64f851b810c99aac5d4c6b6",
            "3f908b5fc4b17f5d41112ff6888d99e195dd380594d810c0b3b17016bf25eba9",
        ],
    )


def _create_buckets():
    buckets = [
        "grand-challenge-private",
        "grand-challenge-protected",
        GARAGE_WEBSITE_BUCKET_NAME,
        "grand-challenge-uploads",
        "grand-challenge-components-inputs",
        "grand-challenge-components-outputs",
    ]

    for bucket in buckets:
        subprocess.check_call(
            args=[
                "docker",
                "exec",
                "-it",
                GARAGE_CONTAINER_NAME,
                "/garage",
                "bucket",
                "create",
                bucket,
            ],
        )

        subprocess.check_call(
            args=[
                "docker",
                "exec",
                "-it",
                GARAGE_CONTAINER_NAME,
                "/garage",
                "bucket",
                "allow",
                "--read",
                "--write",
                "--owner",
                bucket,
                "--key",
                GARAGE_MAIN_KEY_NAME,
            ],
        )


def _allow_public_access():
    subprocess.check_call(
        args=[
            "docker",
            "exec",
            "-it",
            GARAGE_CONTAINER_NAME,
            "/garage",
            "bucket",
            "website",
            "--allow",
            GARAGE_WEBSITE_BUCKET_NAME,
        ],
    )
