from django.contrib.auth import get_user_model
from django.db import models
from guardian.shortcuts import assign_perm

from grandchallenge.core.models import TitleSlugDescriptionModel, UUIDModel


class HangingProtocol(UUIDModel, TitleSlugDescriptionModel):
    creator = models.ForeignKey(
        get_user_model(), null=True, on_delete=models.SET_NULL
    )
    json = models.JSONField(blank=False)

    def __str__(self):
        return f"{self.title} (created by {self.creator})"

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding and self.creator:
            assign_perm(
                f"{self._meta.app_label}.change_{self._meta.model_name}",
                self.creator,
                self,
            )
