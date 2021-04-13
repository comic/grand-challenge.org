import requests
from celery import shared_task
from django.apps import apps
from django.conf import settings


@shared_task
def create_workspace(*, workspace_pk):
    Workspace = apps.get_model(  # noqa: N806
        app_label="workspaces", model_name="Workspace"
    )

    workspace = Workspace.objects.get(pk=workspace_pk)

    with requests.Session() as s:
        _authorise(client=s, auth=workspace.user.workbench_token)

        if settings.DEBUG:
            ip_address = _get_ip_address(s)
        else:
            ip_address = workspace.allowed_ip

        # TODO - use models.WorkspaceType
        env_type_id = _get_env_type_id(s, name="SageMaker Notebook-v1")

        # TODO - use models.WorkspaceTypeConfiguration
        configuration = _get_configuration(
            s,
            env_type_id=env_type_id,
            configuration_id="FIX ME",  # TODO
            instance_type=workspace.configuration.instance_type,
        )

        # TODO - use models.WorkbenchProject
        project = _get_project(s)

        new_workspace = _create_workspace(
            client=s,
            cidr=f"{ip_address}/32",
            description=f"Created at {workspace.created}",
            env_type_config_id=configuration["id"],
            env_type_id=env_type_id,
            name=f"Workspace-{str(workspace.pk)}",
            project_id=project["id"],
            study_ids=[],
        )

        workspace.status = new_workspace["status"]
        workspace.service_catalog_id = new_workspace["id"]
        workspace.full_clean()
        workspace.save()


def _authorise(*, client, auth):
    uri = "api/authentication/public/provider/configs"
    response = client.get(f"{settings.WORKBENCH_API_URL}{uri}")
    response.raise_for_status()

    configs = response.json()

    # get the auth provider url
    auth_configs = [
        c for c in configs if c["id"] == auth.get_provider_display()
    ]

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


def _get_configurations(client, env_type_id, include="all"):
    uri = f"api/workspace-types/{env_type_id}/configurations"
    response = client.get(
        f"{settings.WORKBENCH_API_URL}{uri}", params={"include": include}
    )
    response.raise_for_status()
    return response.json()


def _get_configuration(client, env_type_id, configuration_id, instance_type):
    # TODO, bug in https://github.com/awslabs/service-workbench-on-aws/blob/fd7c3ffaa32099a1cf393cb47620b70c6928ec9f/addons/addon-environment-sc-api/packages/environment-type-mgmt-api/lib/controllers/env-type-configs-controller.js#L65
    # Get does not work
    # uri = f"api/workspace-types/{env_type_id}/configurations/{configuration_id}"
    # response = client.get(f"{base_uri()}{uri}")
    # response.raise_for_status()
    # return response

    configurations = _get_configurations(client, env_type_id=env_type_id)

    # TODO use configuration ids
    # workspace_configurations = [c for c in configurations if c["id"] == configuration_id]

    workspace_configurations = [
        c
        for c in configurations
        if {"key": "InstanceType", "value": instance_type} in c["params"]
    ]

    if len(workspace_configurations) != 1:
        raise RuntimeError(
            f"Configuration id {configuration_id} not found for environment {env_type_id}"
        )

    return workspace_configurations[0]


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
