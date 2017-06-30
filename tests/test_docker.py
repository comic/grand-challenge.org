import subprocess


def test_docker_registry_push():
    response = subprocess.call(['docker', 'pull', 'alpine:latest'])
    assert response == 0

    response = subprocess.call(
        ['docker', 'tag', 'alpine:latest', 'localhost:5000/my-alpine'])
    assert response == 0

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
