from math import ceil

from django.conf import settings
from django.db import models
from django.db.models import Avg

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.validators import JSONValidator
from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)


class SessionUtilization(UUIDModel):
    session = models.OneToOneField(
        "workstations.Session",
        related_name="session_utilization",
        null=True,
        on_delete=models.SET_NULL,
    )
    duration = models.DurationField()
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    reader_studies = models.ManyToManyField(
        to="reader_studies.ReaderStudy",
        through="SessionUtilizationReaderStudy",
        related_name="session_utilizations",
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


class SessionUtilizationReaderStudy(models.Model):
    session_utilization = models.ForeignKey(
        SessionUtilization, on_delete=models.CASCADE
    )
    reader_study = models.ForeignKey(
        "reader_studies.ReaderStudy", on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session_utilization", "reader_study"],
                name="unique_session_utilization_reader_study",
            )
        ]


class ComponentJobUtilizationManager(models.QuerySet):
    def average_duration(self):
        """Calculate the average duration that completed jobs ran for"""
        return self.exclude(duration=None).aggregate(
            duration__avg=Avg("duration")
        )["duration__avg"]


class ComponentJobUtilization(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(class)ss",
    )
    phase = models.ForeignKey(
        "evaluation.Phase",
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(class)ss",
    )
    challenge = models.ForeignKey(
        "challenges.Challenge",
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(class)ss",
    )
    archive = models.ForeignKey(
        "archives.Archive",
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(class)ss",
    )
    algorithm_image = models.ForeignKey(
        "algorithms.AlgorithmImage",
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(class)ss",
    )
    algorithm = models.ForeignKey(
        "algorithms.Algorithm",
        null=True,
        on_delete=models.SET_NULL,
        related_name="%(class)ss",
    )
    duration = models.DurationField(null=True)
    compute_cost_euro_millicents = models.PositiveIntegerField(null=True)

    objects = ComponentJobUtilizationManager.as_manager()

    class Meta:
        abstract = True


class JobUtilization(ComponentJobUtilization):
    job = models.OneToOneField(
        "algorithms.Job",
        related_name="jobutilization",
        null=True,
        on_delete=models.SET_NULL,
    )

    def save(self, *args, **kwargs) -> None:
        if self._state.adding:
            self.creator = self.job.creator
            self.algorithm_image = self.job.algorithm_image
            self.algorithm = self.job.algorithm_image.algorithm

        super().save(*args, **kwargs)


class EvaluationUtilization(ComponentJobUtilization):
    evaluation = models.OneToOneField(
        "evaluation.Evaluation",
        related_name="evaluationutilization",
        null=True,
        on_delete=models.SET_NULL,
    )
    external_evaluation = models.BooleanField()

    def save(self, *args, **kwargs) -> None:
        if self._state.adding:
            self.creator = self.evaluation.submission.creator
            self.phase = self.evaluation.submission.phase
            self.external_evaluation = (
                self.evaluation.submission.phase.external_evaluation
            )
            self.archive = self.evaluation.submission.phase.archive
            self.challenge = self.evaluation.submission.phase.challenge
            self.algorithm_image = self.evaluation.submission.algorithm_image
            if self.evaluation.submission.algorithm_image is not None:
                self.algorithm = (
                    self.evaluation.submission.algorithm_image.algorithm
                )

        super().save(*args, **kwargs)
