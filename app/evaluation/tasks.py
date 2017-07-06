import docker
from celery import shared_task
from django.conf import settings


@shared_task
def add(x, y):
    return x + y


@shared_task
def start_sibling_container():
    client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)
    result = client.containers.run('alpine', 'echo hello world')
    return result.decode()
