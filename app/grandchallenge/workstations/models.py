from django.conf import settings
from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel

from grandchallenge.container_exec.models import ContainerImageModel
from grandchallenge.container_exec.tasks import start_service, cleanup_service
from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse


class Workstation(UUIDModel, TitleSlugDescriptionModel):
    def get_absolute_url(self):
        return reverse("workstations:detail", kwargs={"slug": self.slug})


class WorkstationImage(UUIDModel, ContainerImageModel):
    workstation = models.ForeignKey(Workstation, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse(
            "workstations:image-detail",
            kwargs={"slug": self.workstation.slug, "pk": self.pk},
        )


class Session(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    workstation = models.ForeignKey(Workstation, on_delete=models.CASCADE)

    # Is the user done with this session?
    user_finished = models.BooleanField(default=False)

    def get_absolute_url(self):
        return reverse(
            "workstations:session-detail",
            kwargs={"slug": self.workstation.slug, "pk": self.pk},
        )

    def save(self, *args, **kwargs):
        created = self._state.adding

        super().save(*args, **kwargs)

        if created:
            start_service.apply_async(
                kwargs={
                    "app_label": self._meta.app_label,
                    "model_name": self._meta.model_name,
                    "pk": self.pk,
                }
            )
        elif self.user_finished:
            cleanup_service.apply_async(
                kwargs={
                    "app_label": self._meta.app_label,
                    "model_name": self._meta.model_name,
                    "pk": self.pk,
                }
            )
