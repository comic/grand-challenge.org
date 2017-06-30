import subprocess


def docker_command(args):
    """
    Runs a docker command
    :param args: Arguments to pass to the docker command
    :return: Subprocess response
    """
    return subprocess.call(['docker'] + args)


def test_docker_registry_push():
    test_image = 'alpine:latest'
    registry_host = 'localhost:5000'
    registry_image = registry_host + '/' + test_image

    assert docker_command(['pull', test_image]) == 0

    assert docker_command(['tag', test_image, registry_image]) == 0

    # This should fail as we have basic auth inplace
    assert docker_command(['push', registry_image]) == 1

    # Authenticate
    assert docker_command(
        ['login', '-u', 'testuser', '-p', 'testpassword', registry_host]) == 0

    # Now it should work
    assert docker_command(['push', registry_image]) == 0

    assert docker_command(['image', 'remove', test_image]) == 0

    assert docker_command(['image', 'remove', registry_image]) == 0

    assert docker_command(['image', 'pull', registry_image]) == 0

    assert docker_command(['logout', registry_host]) == 0
