from django.db import models
from django.db.transaction import on_commit
from django.utils.text import get_valid_filename

from grandchallenge.core.storage import private_s3_storage
from grandchallenge.github.tasks import get_tarball


def tarball_path(instance, filename):
    # Convert the pk to a hex, padded to 4 chars with zeros
    pk_as_padded_hex = f"{instance.pk:04x}"

    return (
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{pk_as_padded_hex[-4:-2]}/{pk_as_padded_hex[-2:]}/{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class GitHubWebhookMessage(models.Model):
    created = models.DateTimeField(
        auto_now_add=True, help_text="When we received the event."
    )
    payload = models.JSONField(default=None, null=True)
    tarball = models.FileField(
        null=True, upload_to=tarball_path, storage=private_s3_storage
    )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding and self.payload.get("ref_type") == "tag":
            on_commit(lambda: get_tarball.apply_async(kwargs={"pk": self.pk}))

    class Meta:
        indexes = [
            models.Index(fields=["created"]),
        ]
