import factory

from grandchallenge.workspaces.models import (
    Workspace,
    WorkspaceTypeConfiguration,
)
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import UserFactory


class WorkSpaceTypeConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkspaceTypeConfiguration


class WorkspaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workspace

    phase = factory.SubFactory(PhaseFactory)
    configuration = factory.SubFactory(WorkSpaceTypeConfigurationFactory)
    user = factory.SubFactory(UserFactory)
    allowed_ip = factory.Faker("ipv4_public")
