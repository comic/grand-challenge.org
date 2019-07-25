from collections import Counter

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField
from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.validators import JSONSchemaValidator
from grandchallenge.subdomains.utils import reverse


HANGING_LIST_SCHEMA = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-06/schema#",
    "type": "array",
    "title": "The Hanging List Schema",
    "items": {
        "$id": "#/items",
        "type": "object",
        "title": "The Items Schema",
        "required": ["main"],
        "additionalProperties": False,
        "properties": {
            "main": {
                "$id": "#/items/properties/main",
                "type": "string",
                "title": "The Main Schema",
                "default": "",
                "examples": ["im1.mhd"],
                "pattern": "^(.*)$",
            },
            "secondary": {
                "$id": "#/items/properties/secondary",
                "type": "string",
                "title": "The Secondary Schema",
                "default": "",
                "examples": ["im2.mhd"],
                "pattern": "^(.*)$",
            },
        },
    },
}


class ReaderStudy(UUIDModel, TitleSlugDescriptionModel):
    editors_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name=f"editors_of_readerstudy",
    )
    readers_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name=f"readers_of_readerstudy",
    )
    images = models.ManyToManyField(
        "cases.Image", related_name="readerstudies"
    )

    # A hanging_list is a list of dictionaries where the keys are the
    # view names, and the values are the filenames to place there.
    hanging_list = JSONField(
        default=list,
        blank=True,
        validators=[JSONSchemaValidator(schema=HANGING_LIST_SCHEMA)],
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        verbose_name_plural = "reader studies"

    def get_absolute_url(self):
        return reverse("reader-studies:detail", kwargs={"slug": self.slug})

    @property
    def api_url(self):
        return reverse("api:reader-study-detail", kwargs={"pk": self.pk})

    def create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.readers_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_readers"
        )

    def assign_permissions(self):
        # Allow the editors group to change this study
        assign_perm(
            f"change_{self._meta.model_name}", self.editors_group, self
        )
        # Allow the editors and readers groups to view this study
        assign_perm(f"view_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"view_{self._meta.model_name}", self.readers_group, self)
        # Allow editors to add questions (globally), adding them to this reader
        # study is checked in the views
        assign_perm(
            f"{Question._meta.app_label}.add_{Question._meta.model_name}",
            self.editors_group,
        )
        # Allow readers to add answers (globally), adding them to this reader
        # study is checked in the serializers
        assign_perm(
            f"{Answer._meta.app_label}.add_{Answer._meta.model_name}",
            self.readers_group,
        )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def is_reader(self, user):
        return user.groups.filter(pk=self.readers_group.pk).exists()

    @property
    def study_image_names(self):
        return [im.name for im in self.images.all()]

    @property
    def hanging_image_names(self):
        return [
            name for hanging in self.hanging_list for name in hanging.values()
        ]

    @property
    def hanging_list_valid(self):
        """
        Test that all of the study images are included in the hanging list
        exactly once.
        """
        return sorted(self.study_image_names) == sorted(
            self.hanging_image_names
        )

    @property
    def non_unique_study_image_names(self):
        """
        Get all of the image names that are non-unique for this ReaderStudy
        """
        return [
            name
            for name, count in Counter(self.study_image_names).items()
            if count > 1
        ]

    @property
    def is_valid(self):
        """ Is this ReaderStudy valid? """
        return (
            self.hanging_list_valid
            and len(self.non_unique_study_image_names) == 0
        )

    @property
    def hanging_list_images(self):
        """
        Substitutes the image name for the image detail api url for each image
        defined in the hanging list.
        """
        if not self.is_valid:
            return None

        study_images = {im.name: im.api_url for im in self.images.all()}

        hanging_list_images = [
            {view: study_images.get(name) for view, name in hanging.items()}
            for hanging in self.hanging_list
        ]

        return hanging_list_images


class Question(UUIDModel):
    ANSWER_TYPE_SINGLE_LINE_TEXT = "S"
    ANSWER_TYPE_MULTI_LINE_TEXT = "M"
    ANSWER_TYPE_BOOL = "B"
    ANSWER_TYPE_HEADING = "H"
    ANSWER_TYPE_CHOICES = (
        (ANSWER_TYPE_SINGLE_LINE_TEXT, "Single line text"),
        (ANSWER_TYPE_MULTI_LINE_TEXT, "Multi line text"),
        (ANSWER_TYPE_BOOL, "Bool"),
        (ANSWER_TYPE_HEADING, "Heading"),
    )

    DIRECTION_HORIZONTAL = "H"
    DIRECTION_VERTICAL = "V"
    DIRECTION_CHOICES = (
        (DIRECTION_HORIZONTAL, "Horizontal"),
        (DIRECTION_VERTICAL, "Vertical"),
    )

    reader_study = models.ForeignKey(
        ReaderStudy, on_delete=models.CASCADE, related_name="questions"
    )
    question_text = models.TextField()
    answer_type = models.CharField(
        max_length=1,
        choices=ANSWER_TYPE_CHOICES,
        default=ANSWER_TYPE_SINGLE_LINE_TEXT,
    )
    direction = models.CharField(
        max_length=1, choices=DIRECTION_CHOICES, default=DIRECTION_HORIZONTAL
    )
    order = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"{self.question_text} ({self.get_answer_type_display()})"

    @property
    def api_url(self):
        return reverse(
            "api:reader-studies-question-detail", kwargs={"pk": self.pk}
        )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        # Allow the editors and readers groups to view this question
        assign_perm(
            f"view_{self._meta.model_name}",
            self.reader_study.editors_group,
            self,
        )
        assign_perm(
            f"view_{self._meta.model_name}",
            self.reader_study.readers_group,
            self,
        )

    class Meta:
        ordering = ("order", "created")


class Answer(UUIDModel):
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    images = models.ManyToManyField("cases.Image", related_name="answers")
    answer = JSONField()

    @property
    def api_url(self):
        return reverse(
            "api:reader-studies-answer-detail", kwargs={"pk": self.pk}
        )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        # Allow the editors and creator to view this answer
        assign_perm(
            f"view_{self._meta.model_name}",
            self.question.reader_study.editors_group,
            self,
        )
        assign_perm(f"view_{self._meta.model_name}", self.creator, self)

    class Meta:
        ordering = ("creator", "created")
