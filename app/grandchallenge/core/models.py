import uuid
from itertools import chain

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import (
    TitleSlugDescriptionModel as BaseTitleSlugDescriptionModel,
)

from grandchallenge.core import utils


class TitleSlugDescriptionModel(BaseTitleSlugDescriptionModel):
    # Fix issue in upstream where description can be null
    description = models.TextField(_("description"), blank=True)

    class Meta(BaseTitleSlugDescriptionModel.Meta):
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract class that consists of a UUID primary key, created and modified
    times
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class RequestBase(models.Model):
    """
    When a user wants to join a project, admins have the option of reviewing
    each user before allowing or denying them. This class records the needed
    info for that.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        help_text="which user requested to participate?",
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)
    changed = models.DateTimeField(auto_now=True)
    PENDING = "PEND"
    ACCEPTED = "ACPT"
    REJECTED = "RJCT"
    REGISTRATION_CHOICES = (
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
    )
    status = models.CharField(
        max_length=4, choices=REGISTRATION_CHOICES, default=PENDING
    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def status_to_string(self):

        status = (
            f"Your request to join {self.object_name}, "
            f"sent {self.format_date(self.created)}"
        )
        if self.status == self.PENDING:
            try:
                user_is_verified = self.user.verification.is_verified
            except ObjectDoesNotExist:
                user_is_verified = False

            if (
                not user_is_verified
                and self.base_object.access_request_handling
                == utils.access_requests.AccessRequestHandlingOptions.ACCEPT_VERIFIED_USERS
            ):
                status += ", is awaiting review. Your request will be automatically accepted if you verify your account."
            else:
                status += ", is awaiting review"

        elif self.status == self.ACCEPTED:
            status += ", was accepted at " + self.format_date(self.changed)
        elif self.status == self.REJECTED:
            status += ", was rejected at " + self.format_date(self.changed)

        return status

    @staticmethod
    def format_date(date):
        return localtime(date).strftime("%b %d, %Y at %H:%M")

    def user_affiliation(self):
        profile = self.user.user_profile
        return profile.institution + " - " + profile.department

    class Meta:
        abstract = True


class FieldChangeMixin:
    def __init__(self, *args, tracked_properties=(), **kwargs):
        super().__init__(*args, **kwargs)

        self._tracked_attrs = {
            f.name: f.attname
            for f in chain(
                self._meta.concrete_fields, self._meta.private_fields
            )
        }

        many_to_many_field_names = {f.name for f in self._meta.many_to_many}

        for attname in tracked_properties:
            is_already_tracked = attname in self._tracked_attrs
            is_many_to_many_field = attname in many_to_many_field_names
            is_property = isinstance(getattr(type(self), attname), property)

            if is_already_tracked or is_many_to_many_field or not is_property:
                raise ValueError(f"{attname} cannot be tracked")
            else:
                self._tracked_attrs[attname] = attname

        self._initial_state = self._current_state

    @property
    def _current_state(self):
        return {
            name: getattr(self, attname)
            for name, attname in self._tracked_attrs.items()
        }

    def _current_value(self, field_name):
        return self._current_state[field_name]

    def initial_value(self, field_name):
        return self._initial_state[field_name]

    def has_changed(self, field_name):
        return self._current_value(field_name) != self.initial_value(
            field_name
        )
