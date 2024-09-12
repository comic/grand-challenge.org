from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.db import models
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.utils.access_requests import process_access_request
from grandchallenge.core.validators import JSONSchemaValidator


class RegistrationRequest(RequestBase):
    """
    When a user wants to join a project, admins have the option of reviewing
    each user before allowing or denying them. This class records the needed
    info for that.
    """

    challenge = models.ForeignKey(
        Challenge,
        help_text="To which project does the user want to register?",
        on_delete=models.CASCADE,
    )

    @property
    def base_object(self):
        return self.challenge

    @property
    def object_name(self):
        return self.challenge.short_name

    @property
    def add_method(self):
        return self.base_object.add_participant

    @property
    def remove_method(self):
        return self.base_object.remove_participant

    def __str__(self):
        return f"{self.challenge.short_name} registration request by user {self.user.username}"

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            process_access_request(request_object=self)

    def delete(self, *args, **kwargs):
        ct = ContentType.objects.filter(
            app_label=self._meta.app_label, model=self._meta.model_name
        ).get()
        Follow.objects.filter(object_id=self.pk, content_type=ct).delete()
        super().delete(*args, **kwargs)

    class Meta:
        unique_together = (("challenge", "user"),)


def string_type_schema():
    return {"type": "string"}


class RegistrationQuestion(UUIDModel):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="registration_questions",
    )

    question_text = models.TextField(
        blank=False,
        help_text="Text that will be displayed as a label during registration.",
    )
    question_help_text = models.TextField(
        blank=True,
        help_text="Text that will be displayed as a helpful note during registration.",
    )

    schema = models.JSONField(
        default=string_type_schema,
        help_text="A JSON schema definition against which an answer is validated. See https://json-schema.org/."
        "Only Draft 7, 6, 4 or 3 are supported.",
        validators=[JSONSchemaValidator()],
    )

    required = models.BooleanField(
        default=True,
        help_text="Whether the question requires an answer or not.",
    )

    class Meta:
        unique_together = (("question_text", "challenge"),)

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        # Admins can view, change, and delete a question
        assign_perm(
            "view_registrationquestion", self.challenge.admins_group, self
        )
        assign_perm(
            "change_registrationquestion", self.challenge.admins_group, self
        )
        assign_perm(
            "delete_registrationquestion", self.challenge.admins_group, self
        )


class RegistrationQuestionUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(
        RegistrationQuestion, on_delete=models.CASCADE
    )


class RegistrationQuestionGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(
        RegistrationQuestion, on_delete=models.CASCADE
    )
