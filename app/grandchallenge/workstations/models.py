from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel

from grandchallenge.container_exec.models import ContainerImageModel
from grandchallenge.core.models import UUIDModel


class Workstation(UUIDModel, TitleSlugDescriptionModel):
    pass


class WorkstationImage(UUIDModel, ContainerImageModel):
    workstation = models.ForeignKey(Workstation, on_delete=models.CASCADE)
