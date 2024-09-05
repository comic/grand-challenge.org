from functools import cached_property

from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.utils.access_requests import process_access_request
from grandchallenge.core.validators import JSONSchemaValidator, JSONValidator


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
    )

    question_text = models.TextField(blank=False)
    question_help_text = models.TextField(blank=True)

    schema = models.JSONField(
        default=string_type_schema,
        help_text="A JSON schema definition against which an answer is validated. See https://json-schema.org/."
        "Only Draft 7, 6, 4 or 3 are supported.",
        validators=[JSONSchemaValidator()],
    )

    required = models.BooleanField(default=True)

    @cached_property
    def has_answers(self):
        return RegistrationQuestionAnswer.objects.filter(
            question=self
        ).exists()

    @property
    def read_only_fields(self):
        if self.has_answers:
            return {"question_text", "question_help_text", "schema"}
        else:
            return set()

    class Meta:
        unique_together = (("question_text", "challenge"),)

    def clean(self):
        super().clean()

        if (
            type(self)
            .objects.filter(
                challenge=self.challenge,
                question_text=self.question_text,
            )
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                f"There is already an existing {self._meta.model._meta.verbose_name} with this question text"
            )


class RegistrationQuestionAnswer(models.Model):
    registration_request = models.ForeignKey(
        RegistrationRequest,
        on_delete=models.CASCADE,
    )
    question = models.ForeignKey(
        RegistrationQuestion,
        on_delete=models.CASCADE,
    )

    answer = models.JSONField(blank=True, editable=False)

    class Meta:
        unique_together = (("registration_request", "question"),)

    @property
    def answered(self):
        return not (isinstance(self.answer, str) and len(self.answer) == 0)

    def clean(self):
        super().clean()

        if not self.answered and self.question.required:
            raise ValidationError(
                f"The question {self.question.question_text!r} requires an answer"
            )

        if self.answered and self.question.schema:
            JSONValidator(schema=self.question.schema)(value=self.answer)

        # Cannot add a database-level constraint for this, so do it during cleaning:
        if self.question.challenge != self.registration_request.challenge:
            raise ValidationError(
                "Cannot answer questions for a registration with different challenges"
            )
