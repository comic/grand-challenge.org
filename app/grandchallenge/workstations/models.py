from django.conf import settings
from django.core.validators import MaxValueValidator, RegexValidator
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
    http_port = models.PositiveIntegerField(
        default=8080, validators=[MaxValueValidator(2 ** 16 - 1)]
    )
    websocket_port = models.PositiveIntegerField(
        default=4114, validators=[MaxValueValidator(2 ** 16 - 1)]
    )
    initial_path = models.CharField(
        max_length=256,
        default="Applications/GrandChallengeViewer/index.html",
        validators=[
            RegexValidator(
                regex=r"^(?:[^/][^\s]*)\Z",
                message="This path is invalid, it must not start with a /",
            )
        ],
    )

    def get_absolute_url(self):
        return reverse(
            "workstations:image-detail",
            kwargs={"slug": self.workstation.slug, "pk": self.pk},
        )


class Session(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    workstation_image = models.ForeignKey(
        WorkstationImage, on_delete=models.CASCADE
    )
    # Is the user done with this session?
    user_finished = models.BooleanField(default=False)

    @property
    def hostname(self):
        return (
            f"{self.pk}.{self._meta.model_name}.{self._meta.app_label}".lower()
        )

    def get_absolute_url(self):
        return reverse(
            "workstations:session-detail",
            kwargs={
                "slug": self.workstation_image.workstation.slug,
                "pk": self.pk,
            },
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
