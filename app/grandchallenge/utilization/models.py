from math import ceil

from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.validators import JSONValidator
from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)
from grandchallenge.workstations.models import Session


class SessionCost(UUIDModel):
    session = models.OneToOneField(
        Session,
        related_name="session_cost",
        null=True,
        on_delete=models.SET_NULL,
    )
    duration = models.DurationField()
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    reader_studies = models.ManyToManyField(
        to="reader_studies.ReaderStudy",
        through="SessionCostReaderStudy",
        related_name="session_costs",
        blank=True,
        help_text="Reader studies accessed during session",
    )
    interactive_algorithms = models.JSONField(
        blank=True,
        default=list,
        help_text=(
            "The interactive algorithms for which hardware has been initialized during the session."
        ),
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema",
                    "type": "array",
                    "items": {
                        "enum": InteractiveAlgorithmChoices.values,
                        "type": "string",
                    },
                    "uniqueItems": True,
                }
            )
        ],
    )

    def save(self, *args, **kwargs) -> None:
        from grandchallenge.reader_studies.models import Question

        adding = self._state.adding

        if adding:
            reader_studies = self.session.reader_studies.all()
            self.creator = self.session.creator
            self.interactive_algorithms = list(
                Question.objects.filter(reader_study__in=reader_studies)
                .exclude(interactive_algorithm="")
                .values_list("interactive_algorithm", flat=True)
                .order_by()
                .distinct()
            )

        super().save(*args, **kwargs)

        if adding:
            self.reader_studies.set(reader_studies)

    @property
    def credits_per_hour(self):
        if self.interactive_algorithms:
            return 1000
        else:
            return 500

    @property
    def credits_consumed(self):
        return ceil(
            self.duration.total_seconds() / 3600 * self.credits_per_hour
        )


class SessionCostReaderStudy(models.Model):
    session_cost = models.ForeignKey(SessionCost, on_delete=models.CASCADE)
    reader_study = models.ForeignKey(
        "reader_studies.ReaderStudy", on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session_cost", "reader_study"],
                name="unique_session_cost_reader_study",
            )
        ]
