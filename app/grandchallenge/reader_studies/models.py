from collections import Counter

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Avg, Count, Sum
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.functional import cached_property
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm, get_objects_for_group, remove_perm
from jsonschema import RefResolutionError
from numpy.random.mtrand import RandomState
from sklearn.metrics import accuracy_score

from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import get_logo_path
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import public_s3_storage
from grandchallenge.core.validators import JSONSchemaValidator
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Workstation

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
            "main-overlay": {
                "$id": "#/items/properties/main-overlay",
                "type": "string",
                "title": "The Main Overlay Schema",
                "default": "",
                "examples": ["im1-overlay.mhd"],
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
            "secondary-overlay": {
                "$id": "#/items/properties/secondary-overlay",
                "type": "string",
                "title": "The Secondary Overlay Schema",
                "default": "",
                "examples": ["im2-overlay.mhd"],
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
    workstation = models.ForeignKey(
        "workstations.Workstation", on_delete=models.CASCADE
    )
    workstation_config = models.ForeignKey(
        "workstation_configs.WorkstationConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    logo = models.ImageField(
        upload_to=get_logo_path, storage=public_s3_storage
    )

    # A hanging_list is a list of dictionaries where the keys are the
    # view names, and the values are the filenames to place there.
    hanging_list = JSONField(
        default=list,
        blank=True,
        validators=[JSONSchemaValidator(schema=HANGING_LIST_SCHEMA)],
    )
    shuffle_hanging_list = models.BooleanField(default=False)

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        verbose_name_plural = "reader studies"

    def __str__(self):
        return f"{self.title}"

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
        # Allow readers to add answers (globally), adding them to this reader
        # study is checked in the serializers as there is no
        # get_permission_object in django rest framework.
        assign_perm(
            f"{Answer._meta.app_label}.add_{Answer._meta.model_name}",
            self.readers_group,
        )

    def assign_workstation_permissions(self):
        perm = f"view_{Workstation._meta.model_name}"
        group = self.readers_group

        workstations = get_objects_for_group(
            group=group, perms=perm, klass=Workstation
        )

        if (self.workstation not in workstations) or workstations.count() > 1:
            remove_perm(perm=perm, user_or_group=group, obj=workstations)

            # Allow readers to view the workstation used for this reader study
            assign_perm(perm=perm, user_or_group=group, obj=self.workstation)

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

        self.assign_workstation_permissions()

    def is_editor(self, user):
        return user.groups.filter(pk=self.editors_group.pk).exists()

    def add_editor(self, user):
        return user.groups.add(self.editors_group)

    def remove_editor(self, user):
        return user.groups.remove(self.editors_group)

    def is_reader(self, user):
        return user.groups.filter(pk=self.readers_group.pk).exists()

    def add_reader(self, user):
        return user.groups.add(self.readers_group)

    def remove_reader(self, user):
        return user.groups.remove(self.readers_group)

    @property
    def study_image_names(self):
        return self.images.values_list("name", flat=True)

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
    def hanging_list_diff(self):
        return {
            "in_study_list": set(self.study_image_names)
            - set(self.hanging_image_names),
            "in_hanging_list": set(self.hanging_image_names)
            - set(self.study_image_names),
        }

    @property
    def non_unique_study_image_names(self):
        """Return all of the non-unique image names for this ReaderStudy."""
        return [
            name
            for name, count in Counter(self.study_image_names).items()
            if count > 1
        ]

    @property
    def is_valid(self):
        """Is this ReaderStudy valid?"""
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

    @property
    def image_groups(self):
        return [sorted(x.values()) for x in self.hanging_list]

    @cached_property
    def answerable_questions(self):
        return self.questions.exclude(answer_type=Question.ANSWER_TYPE_HEADING)

    @cached_property
    def answerable_question_count(self):
        return self.answerable_questions.count()

    def add_ground_truth(self, *, data, user):
        answers = []
        for gt in data:
            images = self.images.filter(name__in=gt["images"].split(";"))
            for key in gt.keys():
                if key == "images":
                    continue
                question = self.questions.get(question_text=key)
                if question.answer_type == Question.ANSWER_TYPE_BOOL:
                    if gt[key] not in ["1", "0"]:
                        raise ValidationError(
                            "Expected 1 or 0 for answer type BOOL."
                        )
                    _answer = bool(int(gt[key]))
                else:
                    _answer = gt[key]
                Answer.validate(
                    creator=user,
                    question=question,
                    images=images,
                    answer=_answer,
                    is_ground_truth=True,
                )
                answers.append(
                    {
                        "answer": Answer(
                            creator=user,
                            question=question,
                            answer=_answer,
                            is_ground_truth=True,
                        ),
                        "images": images,
                    }
                )
        for answer in answers:
            answer["answer"].save()
            answer["answer"].images.set(answer["images"])
            answer["answer"].save()

    def get_hanging_list_images_for_user(self, *, user):
        """
        Returns a shuffled list of the hanging list images for a particular
        user. The shuffle is seeded with the users pk, and using RandomState
        from numpy guarantees that the ordering will be consistent across
        python/library versions. Returns the normal list if
        shuffle_hanging_list is false.
        """
        hanging_list = self.hanging_list_images

        if self.shuffle_hanging_list and hanging_list is not None:
            # In place shuffle
            RandomState(seed=int(user.pk)).shuffle(hanging_list)

        return hanging_list

    def generate_hanging_list(self):
        image_names = self.images.values_list("name", flat=True)
        self.hanging_list = [{"main": name} for name in image_names]
        self.save()

    def get_progress_for_user(self, user):
        if not self.is_valid or not self.hanging_list:
            return

        hanging_list_count = len(self.hanging_list)

        if self.answerable_question_count == 0 or hanging_list_count == 0:
            return {"questions": 0.0, "hangings": 0.0, "diff": 0.0}

        expected = hanging_list_count * self.answerable_question_count
        answers = Answer.objects.filter(
            question__in=self.answerable_questions, creator_id=user.id
        ).distinct()
        answer_count = answers.count()

        # There are unanswered questions
        if answer_count % self.answerable_question_count != 0:
            # Group the answers by images and filter out the images that
            # have an inadequate amount of answers
            unanswered_images = (
                answers.order_by("images__name")
                .values("images__name")
                .annotate(answer_count=Count("images__name"))
                .filter(answer_count__lt=self.answerable_question_count)
            )
            image_names = set(
                unanswered_images.values_list("images__name", flat=True)
            ).union(
                set(
                    Image.objects.filter(
                        readerstudies=self, answers__isnull=True
                    )
                    .distinct()
                    .values_list("name", flat=True)
                )
            )
            # Determine which hangings have images with unanswered questions
            hanging_list = [set(x.values()) for x in self.hanging_list]
            completed_hangings = [
                x for x in hanging_list if len(x - image_names) == len(x)
            ]
            completed_hangings = len(completed_hangings)
        else:
            completed_hangings = answer_count / self.answerable_question_count

        hangings = completed_hangings / hanging_list_count * 100
        questions = answer_count / expected * 100
        return {
            "questions": questions,
            "hangings": hangings,
            "diff": questions - hangings,
        }

    def score_for_user(self, user):
        return Answer.objects.filter(
            creator=user, question__reader_study=self, is_ground_truth=False
        ).aggregate(Sum("score"), Avg("score"))

    @cached_property
    def scores_by_user(self):
        return (
            Answer.objects.filter(
                question__reader_study=self, is_ground_truth=False
            )
            .order_by("creator_id")
            .values("creator__username")
            .annotate(Sum("score"), Avg("score"))
            .order_by("-score__sum")
        )

    @property
    def leaderboard(self):
        question_count = float(self.answerable_question_count) * len(
            self.hanging_list
        )
        return {
            "question_count": question_count,
            "grouped_scores": self.scores_by_user,
        }

    @property
    def statistics(self):
        scores_by_question = (
            Answer.objects.filter(
                question__reader_study=self, is_ground_truth=False
            )
            .order_by("question_id")
            .values("question__question_text")
            .annotate(Sum("score"), Avg("score"))
            .order_by("-score__avg")
        )
        scores_by_case = (
            Answer.objects.filter(
                question__reader_study=self, is_ground_truth=False
            )
            .order_by("images__name")
            .values("images__name", "images__pk")
            .annotate(Sum("score"), Avg("score"))
            .order_by("score__avg")
        )
        return {
            "max_score_questions": float(len(self.hanging_list))
            * self.scores_by_user.count(),
            "scores_by_question": scores_by_question,
            "max_score_cases": float(self.answerable_question_count)
            * self.scores_by_user.count(),
            "scores_by_case": scores_by_case,
        }


@receiver(post_delete, sender=ReaderStudy)
def delete_reader_study_groups_hook(*_, instance: ReaderStudy, using, **__):
    """
    Deletes the related groups.

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
    try:
        instance.editors_group.delete(using=using)
    except ObjectDoesNotExist:
        pass

    try:
        instance.readers_group.delete(using=using)
    except ObjectDoesNotExist:
        pass


ANSWER_TYPE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "definitions": {
        "STXT": {"type": "string"},
        "MTXT": {"type": "string"},
        "BOOL": {"type": "boolean"},
        "HEAD": {"type": "null"},
        "2DBB": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "object",
                    "additionalProperties": {"type": "number"},
                    "required": ["major", "minor"],
                },
                "type": {"enum": ["2D bounding box"]},
                "corners": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "minItems": 4,
                    "maxItems": 4,
                },
                "name": {"type": "string"},
            },
            "required": ["version", "type", "corners"],
        },
        "line-object": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "start": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "end": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
            },
            "required": ["start", "end"],
        },
        "DIST": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Distance measurement"]},
                "start": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
                "end": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                },
            },
            "required": ["version", "type", "start", "end"],
        },
        "MDIS": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"enum": ["Multiple distance measurements"]},
                "lines": {
                    "type": "array",
                    "items": {
                        "allOf": [{"$ref": "#/definitions/line-object"}]
                    },
                },
            },
            "required": ["version", "type", "lines"],
        },
    },
    "properties": {
        "version": {
            "type": "object",
            "additionalProperties": {"type": "number"},
            "required": ["major", "minor"],
        }
    },
    # anyOf should exist, check Question.is_answer_valid
    "anyOf": [
        {"$ref": "#/definitions/STXT"},
        {"$ref": "#/definitions/MTXT"},
        {"$ref": "#/definitions/BOOL"},
        {"$ref": "#/definitions/HEAD"},
        {"$ref": "#/definitions/2DBB"},
        {"$ref": "#/definitions/DIST"},
        {"$ref": "#/definitions/MDIS"},
    ],
}


class Question(UUIDModel):
    ANSWER_TYPE_SINGLE_LINE_TEXT = "STXT"
    ANSWER_TYPE_MULTI_LINE_TEXT = "MTXT"
    ANSWER_TYPE_BOOL = "BOOL"
    ANSWER_TYPE_HEADING = "HEAD"
    ANSWER_TYPE_2D_BOUNDING_BOX = "2DBB"
    ANSWER_TYPE_DISTANCE_MEASUREMENT = "DIST"
    ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS = "MDIS"
    # WARNING: Do not change the display text, these are used in the front end
    ANSWER_TYPE_CHOICES = (
        (ANSWER_TYPE_SINGLE_LINE_TEXT, "Single line text"),
        (ANSWER_TYPE_MULTI_LINE_TEXT, "Multi line text"),
        (ANSWER_TYPE_BOOL, "Bool"),
        (ANSWER_TYPE_HEADING, "Heading"),
        (ANSWER_TYPE_2D_BOUNDING_BOX, "2D bounding box"),
        (ANSWER_TYPE_DISTANCE_MEASUREMENT, "Distance measurement"),
        (
            ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
            "Multiple distance measurements",
        ),
    )

    # What is the orientation of the question form when presented on the
    # front end?
    DIRECTION_HORIZONTAL = "H"
    DIRECTION_VERTICAL = "V"
    DIRECTION_CHOICES = (
        (DIRECTION_HORIZONTAL, "Horizontal"),
        (DIRECTION_VERTICAL, "Vertical"),
    )

    # What image port should be used for a drawn annotation?
    IMAGE_PORT_MAIN = "M"
    IMAGE_PORT_SECONDARY = "S"
    IMAGE_PORT_CHOICES = (
        (IMAGE_PORT_MAIN, "Main"),
        (IMAGE_PORT_SECONDARY, "Secondary"),
    )

    SCORING_FUNCTION_ACCURACY = "ACC"
    SCORING_FUNCTION_CHOICES = ((SCORING_FUNCTION_ACCURACY, "Accuracy score"),)

    SCORING_FUNCTIONS = {
        SCORING_FUNCTION_ACCURACY: accuracy_score,
    }

    reader_study = models.ForeignKey(
        ReaderStudy, on_delete=models.CASCADE, related_name="questions"
    )
    question_text = models.TextField()
    help_text = models.TextField(blank=True)
    answer_type = models.CharField(
        max_length=4,
        choices=ANSWER_TYPE_CHOICES,
        default=ANSWER_TYPE_SINGLE_LINE_TEXT,
    )
    image_port = models.CharField(
        max_length=1, choices=IMAGE_PORT_CHOICES, blank=True, default=""
    )
    required = models.BooleanField(default=True)
    direction = models.CharField(
        max_length=1, choices=DIRECTION_CHOICES, default=DIRECTION_HORIZONTAL
    )
    scoring_function = models.CharField(
        max_length=3,
        choices=SCORING_FUNCTION_CHOICES,
        default=SCORING_FUNCTION_ACCURACY,
    )
    order = models.PositiveSmallIntegerField(default=100)

    csv_headers = ["Question text", "Answer type", "Required", "Image port"]

    class Meta:
        ordering = ("order", "created")

    def __str__(self):
        return (
            f"{self.question_text} "
            "("
            f"{self.get_answer_type_display()}, "
            f"{self.get_image_port_display() + ' port,' if self.image_port else ''}"
            f"{'' if self.required else 'not'} required, "
            f"order {self.order}"
            ")"
        )

    @property
    def csv_values(self):
        return [
            self.question_text,
            self.get_answer_type_display(),
            self.required,
            f"{self.get_image_port_display() + ' port,' if self.image_port else ''}",
        ]

    @property
    def api_url(self):
        return reverse(
            "api:reader-studies-question-detail", kwargs={"pk": self.pk}
        )

    @property
    def is_fully_editable(self):
        return self.answer_set.count() == 0

    @property
    def read_only_fields(self):
        if not self.is_fully_editable:
            return ["question_text", "answer_type", "image_port", "required"]
        return []

    def calculate_score(self, answer, ground_truth):
        return self.SCORING_FUNCTIONS[self.scoring_function](
            [answer], [ground_truth], normalize=True
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

    def clean(self):
        # Make sure that the image port is only set when using drawn
        # annotations.
        if (
            self.answer_type
            in [
                self.ANSWER_TYPE_2D_BOUNDING_BOX,
                self.ANSWER_TYPE_DISTANCE_MEASUREMENT,
                self.ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
            ]
        ) != bool(self.image_port):
            raise ValidationError(
                "The image port must (only) be set for annotation questions."
            )

        if self.answer_type == self.ANSWER_TYPE_BOOL and self.required:
            raise ValidationError(
                "Bool answer types should not have Required checked "
                "(otherwise the user will need to tick a box for each image!)"
            )

    def is_answer_valid(self, *, answer):
        try:
            return (
                JSONSchemaValidator(
                    schema={
                        **ANSWER_TYPE_SCHEMA,
                        "anyOf": [
                            {"$ref": f"#/definitions/{self.answer_type}"}
                        ],
                    }
                )(answer)
                is None
            )
        except ValidationError:
            return False
        except RefResolutionError:
            raise RuntimeError(
                f"#/definitions/{self.answer_type} needs to be defined in "
                "ANSWER_TYPE_SCHEMA."
            )


class Answer(UUIDModel):
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    images = models.ManyToManyField("cases.Image", related_name="answers")
    # TODO: add validators=[JSONSchemaValidator(schema=ANSWER_TYPE_SCHEMA)],
    answer = JSONField()
    is_ground_truth = models.BooleanField(default=False)
    score = models.FloatField(null=True)

    csv_headers = Question.csv_headers + [
        "Created",
        "Answer",
        "Images",
        "Creator",
    ]

    class Meta:
        ordering = ("creator", "created")

    def __str__(self):
        return f"{self.question.question_text} {self.answer} ({self.creator})"

    @property
    def api_url(self):
        return reverse(
            "api:reader-studies-answer-detail", kwargs={"pk": self.pk}
        )

    @property
    def csv_values(self):
        return self.question.csv_values + [
            self.created.isoformat(),
            self.answer,
            "; ".join(self.images.values_list("name", flat=True)),
            self.creator.username,
        ]

    @staticmethod
    def validate(*, creator, question, answer, images, is_ground_truth=False):
        if len(images) == 0:
            raise ValidationError(
                "You must specify the images that this answer corresponds to."
            )

        reader_study_images = question.reader_study.images.all()
        for im in images:
            if im not in reader_study_images:
                raise ValidationError(
                    f"Image {im} does not belong to this reader study."
                )

        if is_ground_truth:
            if Answer.objects.filter(
                question=question,
                is_ground_truth=True,
                images__in=images.values_list("id", flat=True),
            ).exists():
                raise ValidationError(
                    "Ground truth already added for this question/image combination"
                )
        else:
            if Answer.objects.filter(
                creator=creator, question=question, images__in=images
            ).exists():
                raise ValidationError(
                    f"User {creator} has already answered this question "
                    f"for at least 1 of these images."
                )
            if not question.reader_study.is_reader(user=creator):
                raise ValidationError(
                    "This user is not a reader for this study."
                )

        if not question.is_answer_valid(answer=answer):
            raise ValidationError(
                f"Your answer is not the correct type. "
                f"{question.get_answer_type_display()} expected, "
                f"{type(answer)} found."
            )

    def calculate_score(self, ground_truth):
        self.score = self.question.calculate_score(self.answer, ground_truth)
        return self.score

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
