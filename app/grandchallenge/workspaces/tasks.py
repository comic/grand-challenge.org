import requests
from celery import shared_task
from django.conf import settings

from grandchallenge.workspaces.models import (
    WorkbenchToken,
    Workspace,
    WorkspaceKindChoices,
    WorkspaceStatus,
    WorkspaceTypeConfiguration,
)


@shared_task
def create_workspace_type_configuration(*, workspace_type_configuration_pk):
    configuration = WorkspaceTypeConfiguration.objects.get(
        pk=workspace_type_configuration_pk
    )
    auth = WorkbenchToken.objects.get(
        user__username=settings.WORKBENCH_ADMIN_USERNAME
    )

    with requests.Session() as s:
        _authorise(client=s, auth=auth)

        # TODO - use models.WorkspaceType
        env_type_id = _get_env_type_id(s, name="SageMaker Notebook-v1")

        _add_configuration(
            client=s, env_type_id=env_type_id, configuration=configuration
        )


@shared_task
def create_workspace(*, workspace_pk):
    workspace = Workspace.objects.get(pk=workspace_pk)

    with requests.Session() as s:
        _authorise(client=s, auth=workspace.user.workbench_token)

        if settings.DEBUG:
            ip_address = _get_ip_address(s)
        else:
            ip_address = workspace.allowed_ip

        # TODO - use models.WorkspaceType
        env_type_id = _get_env_type_id(s, name="SageMaker Notebook-v1")

        # TODO - use models.WorkbenchProject
        project = _get_project(s)

        instance = _create_workspace(
            client=s,
            cidr=f"{ip_address}/32",
            description=f"Created at {workspace.created}",
            env_type_config_id=workspace.configuration.pk,
            env_type_id=env_type_id,
            name=f"Workspace-{str(workspace.pk)}",
            project_id=project["id"],
            study_ids=[],
        )

        workspace.status = instance["status"]
        workspace.service_workbench_id = instance["id"]
        workspace.full_clean()
        workspace.save()

        tasks = wait_for_workspace_to_start.signature(
            kwargs={"workspace_pk": workspace.pk}, immutable=True
        )

        if (
            workspace.configuration.kind
            == WorkspaceKindChoices.SAGEMAKER_NOTEBOOK
        ):
            tasks |= get_workspace_url.signature(
                kwargs={"workspace_pk": workspace.pk}, immutable=True
            )

        tasks.apply_async()


@shared_task(bind=True, max_retries=20)
def wait_for_workspace_to_start(self, *, workspace_pk):
    """Checks if the workspace is up for up to 10 minutes."""
    workspace = Workspace.objects.get(pk=workspace_pk)

    if workspace.status != WorkspaceStatus.PENDING:
        # Nothing to do
        return

    with requests.Session() as s:
        _authorise(client=s, auth=workspace.user.workbench_token)

        instance = _get_workspace(
            s, workspace_id=workspace.service_workbench_id
        )

        if instance["status"] == WorkspaceStatus.PENDING:
            # Raises celery.exceptions.Retry
            self.retry(countdown=30)
            # TODO catch MaxRetriesExceeded?
        else:
            workspace.status = instance["status"]
            workspace.full_clean()
            workspace.save()


@shared_task
def get_workspace_url(*, workspace_pk):
    workspace = Workspace.objects.get(pk=workspace_pk)

    if workspace.configuration.kind != WorkspaceKindChoices.SAGEMAKER_NOTEBOOK:
        raise ValueError("URLs can only be generated for SageMaker Notebooks")

    with requests.Session() as s:
        _authorise(client=s, auth=workspace.user.workbench_token)

        instance = _get_workspace(
            s, workspace_id=workspace.service_workbench_id
        )

        if instance["status"] != WorkspaceStatus.COMPLETED:
            raise RuntimeError("Workspace was not running")
        else:
            connection = _get_workspace_connection(
                s, workspace_id=workspace.service_workbench_id
            )
            url = _create_workspace_url(
                s,
                workspace_id=workspace.service_workbench_id,
                connection_id=connection["id"],
            )
            workspace.notebook_url = url
            workspace.full_clean()
            workspace.save()


def _authorise(*, client, auth):
    uri = "api/authentication/public/provider/configs"
    response = client.get(f"{settings.WORKBENCH_API_URL}{uri}")
    response.raise_for_status()

    configs = response.json()

    # get the auth provider url
    auth_configs = [c for c in configs if c["id"] == auth.provider.lower()]

    if len(auth_configs) != 1:
        raise ValueError(
            f"Auth provider '{auth.get_provider_display()}' is not supported by this service workbench instance"
        )

    auth_config = auth_configs[0]

    # obtain the auth token
    # TODO: is this only for internal auth?
    response = client.post(
        f"{settings.WORKBENCH_API_URL}{auth_config['signInUri']}",
        data={
            "username": auth.email,
            "password": auth.token,
            "authenticationProviderId": auth_config["id"],
        },
    )
    response.raise_for_status()

    # set the token auth header
    # TODO: what is the expiry on tokens?
    client.headers.update({"Authorization": response.json()["idToken"]})


def _get_ip_address(client):
    uri = "api/ip"
    response = client.get(f"{settings.WORKBENCH_API_URL}{uri}")
    response.raise_for_status()
    return response.json()["ipAddress"]


def _get_workspace_types(client, status="approved"):
    uri = "api/workspace-types"
    response = client.get(
        f"{settings.WORKBENCH_API_URL}{uri}", params={"status": status}
    )
    response.raise_for_status()
    return response.json()


def _get_env_type_id(client, name):
    workspaces = _get_workspace_types(client)

    workspace_types = [
        w for w in workspaces if w["name"].casefold() == name.casefold()
    ]

    if len(workspace_types) != 1:
        raise RuntimeError(f"Unique workspace was not found for '{name}'.")

    workspace_type = workspace_types[0]

    return f"{workspace_type['product']['productId']}-{workspace_type['provisioningArtifact']['id']}"


def _add_configuration(
    client, env_type_id, configuration, allow_role_ids=("researcher",)
):
    uri = f"api/workspace-types/{env_type_id}/configurations"
    response = client.post(
        f"{settings.WORKBENCH_API_URL}{uri}",
        json={
            "id": str(configuration.pk),
            "name": configuration.name,
            "allowRoleIds": allow_role_ids,
            "denyRoleIds": [],
            "params": configuration.params,
            "tags": [],
        },
    )
    response.raise_for_status()
    return response.json()


def _get_project(client):
    uri = "api/projects"
    response = client.get(f"{settings.WORKBENCH_API_URL}{uri}")
    response.raise_for_status()

    projects = response.json()

    if len(projects) != 1:
        raise RuntimeError("Too many projects found")

    return projects[0]


def _create_workspace(
    client,
    cidr,
    description,
    env_type_config_id,
    env_type_id,
    name,
    project_id,
    study_ids,
):
    uri = "api/workspaces/service-catalog/"
    payload = {
        "cidr": cidr,
        "description": description,
        "envTypeConfigId": env_type_config_id,
        "envTypeId": env_type_id,
        "name": name,
        "projectId": project_id,
        "studyIds": study_ids,
    }
    response = client.post(f"{settings.WORKBENCH_API_URL}{uri}", data=payload)
    response.raise_for_status()
    return response.json()


def _get_workspace(client, workspace_id):
    uri = f"api/workspaces/service-catalog/{workspace_id}"
    response = client.get(f"{settings.WORKBENCH_API_URL}{uri}")
    response.raise_for_status()
    return response.json()


def _get_workspace_connections(client, workspace_id):
    uri = f"api/workspaces/service-catalog/{workspace_id}/connections"
    response = client.get(f"{settings.WORKBENCH_API_URL}{uri}")
    response.raise_for_status()
    return response.json()


def _get_workspace_connection(
    client, workspace_id, connection_type="SageMaker"
):
    connections = _get_workspace_connections(client, workspace_id)

    workspace_connections = [
        c for c in connections if c["type"] == connection_type
    ]

    if len(workspace_connections) != 1:
        raise RuntimeError(
            f"Connection '{connection_type}' not found for {workspace_id}"
        )

    return workspace_connections[0]


def _create_workspace_url(client, workspace_id, connection_id):
    uri = f"api/workspaces/service-catalog/{workspace_id}/connections/{connection_id}/url"
    response = client.post(f"{settings.WORKBENCH_API_URL}{uri}")
    response.raise_for_status()
    return response.json()["url"]
