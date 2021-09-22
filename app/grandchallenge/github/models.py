import re
from datetime import timedelta

import requests
from django.conf import settings
from django.db import models
from django.db.transaction import on_commit
from django.utils import timezone
from django.utils.text import get_valid_filename

from grandchallenge.core.storage import private_s3_storage
from grandchallenge.github.tasks import get_zipfile, unlink_algorithm


def zipfile_path(instance, filename):
    # Convert the pk to a hex, padded to 4 chars with zeros
    pk_as_padded_hex = f"{instance.pk:04x}"

    return (
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{pk_as_padded_hex[-4:-2]}/{pk_as_padded_hex[-2:]}/{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class GitHubUserToken(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    access_token = models.CharField(max_length=64)
    access_token_expires = models.DateTimeField()
    refresh_token = models.CharField(max_length=128)
    refresh_token_expires = models.DateTimeField()
    github_user_id = models.BigIntegerField(null=True)

    def __str__(self):
        return f"Token for {self.user}, expires at {self.access_token_expires}"

    @property
    def access_token_is_expired(self):
        return self.access_token_expires < timezone.now()

    def refresh_access_token(self):
        resp = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
            },
            timeout=5,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        resp.raise_for_status()
        self.update_from_payload(payload=resp.json())

    def update_from_payload(self, *, payload):
        # Small grace time for when the tokens were issued
        token_acquired_at = timezone.now() - timedelta(seconds=60)

        self.access_token = payload["access_token"]
        self.access_token_expires = token_acquired_at + timedelta(
            seconds=int(payload["expires_in"])
        )
        self.refresh_token = payload["refresh_token"]
        self.refresh_token_expires = token_acquired_at + timedelta(
            seconds=int(payload["refresh_token_expires_in"])
        )


class GitHubWebhookMessage(models.Model):
    created = models.DateTimeField(
        auto_now_add=True, help_text="When we received the event."
    )
    payload = models.JSONField(default=None, null=True)
    zipfile = models.FileField(
        null=True, upload_to=zipfile_path, storage=private_s3_storage
    )
    has_open_source_license = models.BooleanField(default=False)
    license_check_result = models.CharField(max_length=1024, blank=True)
    error = models.TextField(blank=True)

    def __str__(self):
        return f"{self.repo_name} {self.tag}"

    @property
    def repo_name(self):
        if not self.payload.get("repository"):
            return "repo"
        return re.sub(
            "[^0-9a-zA-Z]+", "-", self.payload["repository"]["full_name"],
        ).lower()

    @property
    def tag(self):
        if not self.payload.get("ref"):
            return "tag"
        return re.sub("[^0-9a-zA-Z]+", "-", self.payload["ref"],).lower()

    @property
    def tag_url(self):
        return f"https://github.com/{self.payload['repository']['full_name']}/releases/tag/{self.payload['ref']}"

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding and self.payload.get("ref_type") == "tag":
            on_commit(lambda: get_zipfile.apply_async(kwargs={"pk": self.pk}))
        if adding and self.payload.get("action") == "deleted":
            on_commit(
                lambda: unlink_algorithm.apply_async(kwargs={"pk": self.pk})
            )

    class Meta:
        indexes = [
            models.Index(fields=["created"]),
        ]
