import subprocess


def test_docker_registry_push():
    response = subprocess.call(['docker', 'pull', 'alpine:latest'])
    assert response == 0

    response = subprocess.call(
        ['docker', 'tag', 'alpine:latest', 'localhost:5000/my-alpine'])
    assert response == 0

    # This should fail as we have basic auth inplace
    response = subprocess.call(
        ['docker', 'push', 'localhost:5000/my-alpine']
    )
    assert response == 1

    # Authenticate
    response = subprocess.call(
        ['docker', 'login', '-u', 'testuser', '-p', 'testpassword', 'localhost:5000']
    )
    assert response == 0

    # Now it should work
    response = subprocess.call(
        ['docker', 'push', 'localhost:5000/my-alpine']
    )
    assert response == 0

    response = subprocess.call(
        ['docker', 'image', 'remove', 'alpine:latest']
    )
    assert response == 0

    response = subprocess.call(
        ['docker', 'image', 'remove', 'localhost:5000/my-alpine']
    )
    assert response == 0

    response = subprocess.call(
        ['docker', 'image', 'pull', 'localhost:5000/my-alpine']
    )
    assert response == 0

    response = subprocess.call(
        ['docker', 'logout', 'localhost:5000']
    )
    assert response == 0
