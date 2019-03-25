from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel

from grandchallenge.container_exec.models import ContainerImageModel
from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse


class Workstation(UUIDModel, TitleSlugDescriptionModel):
    def get_absolute_url(self):
        return reverse("workstations:detail", kwargs={"slug": self.slug})


class WorkstationImage(UUIDModel, ContainerImageModel):
    workstation = models.ForeignKey(Workstation, on_delete=models.CASCADE)
