import re
from datetime import timedelta

import requests
from django.conf import settings
from django.db import models
from django.db.transaction import on_commit
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _

from grandchallenge.core.storage import private_s3_storage
from grandchallenge.github.exceptions import GitHubBadRefreshTokenException
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
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()

        payload = resp.json()

        if "error" in payload:
            if payload["error"] == "bad_refresh_token":
                # User has deleted their installation, they need
                # to start the auth process again
                raise GitHubBadRefreshTokenException
            else:
                raise RuntimeError(payload["error"])
        else:
            self.update_from_payload(payload=payload)

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


class CloneStatusChoices(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    STARTED = "STARTED", _("Started")
    SUCCESS = "SUCCESS", _("Success")
    FAILURE = "FAILURE", _("Failure")
    INVALID = "INVALID", _("Invalid")
    NOT_APPLICABLE = "NOT_APPLICABLE", _("Not Applicable")


class GitHubWebhookMessage(models.Model):
    CloneStatusChoices = CloneStatusChoices

    created = models.DateTimeField(
        auto_now_add=True, help_text="When we received the event."
    )
    payload = models.JSONField(default=None, null=True)
    zipfile = models.FileField(
        null=True, upload_to=zipfile_path, storage=private_s3_storage
    )
    license_check_result = models.JSONField(blank=True, default=dict)
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    clone_status = models.CharField(
        choices=CloneStatusChoices,
        default=CloneStatusChoices.NOT_APPLICABLE,
        max_length=14,
    )

    def __str__(self):
        return f"{self.repo_name} {self.tag}"

    @property
    def repo_name(self):
        if not self.payload.get("repository"):
            return "repo"
        return re.sub(
            "[^0-9a-zA-Z]+", "-", self.payload["repository"]["full_name"]
        ).lower()

    @property
    def tag(self):
        if not self.payload.get("ref"):
            return "tag"
        return re.sub("[^0-9a-zA-Z]+", "-", self.payload["ref"]).lower()

    @property
    def tag_url(self):
        return f"https://github.com/{self.payload['repository']['full_name']}/releases/tag/{self.payload['ref']}"

    @property
    def user_error(self):
        if "This repository is over its data quota" in self.stdout:
            return (
                f"Repository {self.repo_name} has used all of its LFS "
                f"bandwidth. Please purchase more data packs on GitHub for "
                f"this repo so that we can clone it."
            )
        elif "This repository exceeded its LFS budget" in self.stdout:
            return (
                f"Repository {self.repo_name} has used all of its LFS "
                f"budget. Please assign more LFS budget on GitHub for "
                f"this repo so that we can clone it."
            )
        else:
            return ""

    @property
    def licenses(self):
        return self.license_check_result.get("licenses", [])

    @property
    def license_keys(self):
        return {_license.get("key") for _license in self.licenses}

    @property
    def has_open_source_license(self):
        return bool(self.license_keys) and self.license_keys.issubset(
            settings.OPEN_SOURCE_LICENSES
        )

    def save(self, *args, **kwargs):
        post_save_task = None

        if self._state.adding:
            if self.payload.get("ref_type") == "tag":
                post_save_task = get_zipfile
                self.clone_status = CloneStatusChoices.PENDING
            elif self.payload.get("action") == "deleted":
                post_save_task = unlink_algorithm
                self.clone_status = CloneStatusChoices.NOT_APPLICABLE
            else:
                self.clone_status = CloneStatusChoices.INVALID

        super().save(*args, **kwargs)

        if post_save_task:
            on_commit(
                post_save_task.signature(kwargs={"pk": self.pk}).apply_async
            )

    class Meta:
        indexes = [models.Index(fields=["created"])]
