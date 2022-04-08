import itertools
import json
from collections import Counter

import numpy as np
from actstream.models import Follow
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Avg, Count, OuterRef, Q, Subquery, Sum
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.functional import cached_property
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm, get_objects_for_group, remove_perm
from jsonschema import RefResolutionError
from numpy.random.mtrand import RandomState
from simple_history.models import HistoricalRecords
from sklearn.metrics import accuracy_score
from stdimage import JPEGField

from grandchallenge.anatomy.models import BodyStructure
from grandchallenge.cases.models import Image
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.components.schemas import ANSWER_TYPE_SCHEMA
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.storage import (
    get_logo_path,
    get_social_image_path,
    public_s3_storage,
)
from grandchallenge.core.templatetags.bleach import md2html
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
    process_access_request,
)
from grandchallenge.core.validators import JSONValidator
from grandchallenge.hanging_protocols.models import ImagePort, ViewContentMixin
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.organizations.models import Organization
from grandchallenge.publications.models import Publication
from grandchallenge.subdomains.utils import reverse

__doc__ = """
A reader study enables you to have a set of readers answer a set of questions
about a set of images.

Editors
    You can add multiple editors to your reader study.
    An editor is someone who can edit the reader study settings, add other editors,
    add and remove readers, add images and edit questions.
Readers
    A user who can read this study, creating an answer for each question and
    image in the study.
Cases
    The set of images that will be used in the study.
Hanging List
    How the each image will be presented to the user as a set of hanging protocols.
    For instance, you might want to present two images side by side and
    have a reader answer a question about both, or overlay one image
    on another.


Creating a Reader Study
-----------------------

A ``ReaderStudy`` can use any available ``Workstation``.
A ``WorkstationConfig`` can also be used for the study to customise the default
appearance of the workstation.

Cases
-----

Cases can be added to a reader study by adding ``Image`` instances.
Multiple image formats are supported:

* ``.mha``
* ``.mhd`` with the accompanying ``.zraw`` or ``.raw`` file
* ``.tif``/``.tiff``
* ``.jpg``/``.jpeg``
* ``.png``
* 3D/4D DICOM support is also available, though this is experimental and not
  guaranteed to work on all ``.dcm`` images.

Defining the Hanging List
-------------------------

When you upload a set of images you have the option to automatically generate
the default hanging list.
The default hanging list presents each reader with 1 image per protocol.

You are able to customise the hanging list in the study edit page.
Here, you are able to assign multiple images and overlays to each protocol.

Available image ports are:
* ``main``
* ``secondary``
* ``tertiary``
* ``quaternary``
* ``quinary``
* ``senary``
* ``septenary``
* ``octonary``
* ``nonary``
* ``denary``

Overlays can be applied to the image ports by using the image-port name with
the suffix '-overlay' (e.g. ``main-overlay``).

Questions
---------

A ``Question`` can be optional and the following ``answer_type`` options are
available:

* Heading (not answerable)
* Bool
* Single line text
* Multiline text

The following annotation answer types are also available:

* Distance measurement
* Multiple distance measurements
* 2D bounding box

To use an annotation answer type you must also select the image port where the
annotation will be made.

Adding Ground Truth
-------------------

To monitor the performance of the readers you are able add ground truth to a
reader study by uploading a csv file.

If ground truth has been added to a ``ReaderStudy``, any ``Answer`` given by a
reader is evaluated by applying the ``scoring_function`` chosen for the ``Question``.

The scores can then be compared on the ``leaderboard``. Statistics are also available
based on these scores: the average and total scores for each question as well
as for each case are displayed in the ``statistics`` view.
"""

#: Supported image-port overlays.
IMAGE_PORT_OVERLAYS = [f"{port.lower()}-overlay" for port in ImagePort.labels]

#: Schema used to validate if the hanging list is of the correct format.
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
            port: {
                "$id": f"#/items/properties/{port}",
                "type": "string",
                "title": f"The {port.title()} Schema",
                "default": "",
                "examples": [f"im_{port}.mhd"],
                "pattern": "^(.*)$",
            }
            for port in [p.lower() for p in ImagePort.labels]
            + IMAGE_PORT_OVERLAYS
        },
    },
}

CASE_TEXT_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": {"type": "string"},
}


class ReaderStudy(UUIDModel, TitleSlugDescriptionModel, ViewContentMixin):
    """
    Reader Study model.

    A reader study is a tool that allows users to have a set of readers answer
    a set of questions on a set of images (cases).
    """

    editors_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="editors_of_readerstudy",
    )
    readers_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="readers_of_readerstudy",
    )
    images = models.ManyToManyField(
        "cases.Image", related_name="readerstudies"
    )

    workstation = models.ForeignKey(
        "workstations.Workstation", on_delete=models.PROTECT
    )
    workstation_config = models.ForeignKey(
        "workstation_configs.WorkstationConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    hanging_protocol = models.ForeignKey(
        "hanging_protocols.HangingProtocol",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    public = models.BooleanField(
        default=False,
        help_text=(
            "Should this reader study be visible to all users on the "
            "overview page? This does not grant all users permission to read "
            "this study. Users will still need to be added to the "
            "study's readers group in order to do that."
        ),
    )
    access_request_handling = models.CharField(
        max_length=25,
        choices=AccessRequestHandlingOptions.choices,
        default=AccessRequestHandlingOptions.MANUAL_REVIEW,
        help_text=("How would you like to handle access requests?"),
    )
    logo = JPEGField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        variations=settings.STDIMAGE_LOGO_VARIATIONS,
    )
    social_image = JPEGField(
        upload_to=get_social_image_path,
        storage=public_s3_storage,
        blank=True,
        help_text="An image for this reader study which is displayed when you post the link on social media. Should have a resolution of 640x320 px (1280x640 px for best display).",
        variations=settings.STDIMAGE_SOCIAL_VARIATIONS,
    )
    help_text_markdown = models.TextField(blank=True)

    # A hanging_list is a list of dictionaries where the keys are the
    # view names, and the values are the filenames to place there.
    hanging_list = models.JSONField(
        default=list,
        blank=True,
        validators=[JSONValidator(schema=HANGING_LIST_SCHEMA)],
    )
    shuffle_hanging_list = models.BooleanField(default=False)
    is_educational = models.BooleanField(
        default=False,
        help_text=(
            "If checked, readers get the option to verify their answers "
            "against the uploaded ground truth. This also means that "
            "the uploaded ground truth will be readily available to "
            "the readers."
        ),
    )
    case_text = models.JSONField(
        default=dict,
        blank=True,
        validators=[JSONValidator(schema=CASE_TEXT_SCHEMA)],
    )
    allow_answer_modification = models.BooleanField(
        default=False,
        help_text=(
            "If true, readers are allowed to modify their answers for a case "
            "by navigating back to previous cases. 'allow_case_browsing' must "
            "be checked with this as well."
        ),
    )
    allow_case_navigation = models.BooleanField(
        default=False,
        help_text=(
            "If true, readers are allowed to navigate back and forth between "
            "cases in this reader study."
        ),
    )
    allow_show_all_annotations = models.BooleanField(
        default=False,
        help_text=(
            "If true, readers are allowed to show/hide all annotations "
            "for a case."
        ),
    )
    roll_over_answers_for_n_cases = models.PositiveSmallIntegerField(
        default=False,
        help_text=(
            "The number of cases for which answers should roll over. "
            "It can be used for repeated readings with slightly different hangings. "
            "For instance, if set to 1. Case 2 will start with the answers from case 1; "
            "whereas case 3 starts anew but its answers will rollover to case 4."
        ),
    )
    validate_hanging_list = models.BooleanField(default=True)
    publications = models.ManyToManyField(
        Publication,
        blank=True,
        help_text="The publications associated with this reader study",
    )
    modalities = models.ManyToManyField(
        ImagingModality,
        blank=True,
        help_text="The imaging modalities contained in this reader study",
    )
    structures = models.ManyToManyField(
        BodyStructure,
        blank=True,
        help_text="The structures contained in this reader study",
    )
    organizations = models.ManyToManyField(
        Organization,
        blank=True,
        help_text="The organizations associated with this reader study",
        related_name="readerstudies",
    )
    use_display_sets = models.BooleanField(default=True)

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        verbose_name_plural = "reader studies"
        ordering = ("created",)
        permissions = [("read_readerstudy", "Can read reader study")]

    copy_fields = (
        "workstation",
        "workstation",
        "logo",
        "social_image",
        "help_text_markdown",
        "shuffle_hanging_list",
        "is_educational",
        "roll_over_answers_for_n_cases",
        "allow_answer_modification",
        "allow_case_navigation",
        "allow_show_all_annotations",
        "access_request_handling",
    )

    def __str__(self):
        return f"{self.title}"

    @property
    def case_field(self):
        return "case" if self.use_display_sets else "images"

    @property
    def ground_truth_file_headers(self):
        return [self.case_field] + [
            q.question_text for q in self.answerable_questions
        ]

    def get_ground_truth_csv_dict(self):
        if len(self.hanging_list) == 0 and self.display_sets.count() == 0:
            return {}
        result = []
        answers = {
            q.question_text: q.example_answer
            for q in self.answerable_questions
        }
        for images in self.image_groups:
            _answers = answers.copy()
            _answers[self.case_field] = (
                str(images) if self.use_display_sets else ";".join(images)
            )
            result.append(_answers)
        return result

    def get_example_ground_truth_csv_text(self, limit=None):
        if len(self.hanging_list) == 0 and self.display_sets.count() == 0:
            return "No cases in this reader study"
        headers = self.ground_truth_file_headers
        return "\n".join(
            [
                ",".join(headers),
                "\n".join(
                    [
                        ",".join([x[header] for header in headers])
                        for x in self.get_ground_truth_csv_dict()[:limit]
                    ]
                ),
            ]
        )

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

        # Allow the editors and readers groups to read this study
        assign_perm(f"read_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"read_{self._meta.model_name}", self.readers_group, self)

        # Allow readers and editors to add answers (globally)
        # adding them to this reader study is checked in the serializers as
        # there is no get_permission_object in django rest framework.
        assign_perm(
            f"{Answer._meta.app_label}.add_{Answer._meta.model_name}",
            self.editors_group,
        )
        assign_perm(
            f"{Answer._meta.app_label}.add_{Answer._meta.model_name}",
            self.readers_group,
        )

        # Allow the editors and readers groups to view this study
        assign_perm(f"view_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"view_{self._meta.model_name}", self.readers_group, self)

        reg_and_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        if self.public:
            assign_perm(f"view_{self._meta.model_name}", reg_and_anon, self)
        else:
            remove_perm(f"view_{self._meta.model_name}", reg_and_anon, self)

    def assign_workstation_permissions(self):
        perm = "workstations.view_workstation"

        for group in (self.editors_group, self.readers_group):
            workstations = get_objects_for_group(
                group=group, perms=perm, accept_global_perms=False
            )

            if (
                self.workstation not in workstations
            ) or workstations.count() > 1:
                remove_perm(perm=perm, user_or_group=group, obj=workstations)

                # Allow readers to view the workstation used for this study
                assign_perm(
                    perm=perm, user_or_group=group, obj=self.workstation
                )

    def clean(self):
        if self.hanging_list is None:
            self.hanging_list = []
        if self.case_text is None:
            self.case_text = {}
        if self.view_content is None:
            self.view_content = {}

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()

        super().save(*args, **kwargs)

        self.assign_permissions()
        self.assign_workstation_permissions()

    def delete(self):
        ct = ContentType.objects.filter(
            app_label=self._meta.app_label, model=self._meta.model_name
        ).get()
        Follow.objects.filter(object_id=self.pk, content_type=ct).delete()
        super().delete()

    def is_editor(self, user):
        """Checks if ``user`` is an editor for this ``ReaderStudy``."""
        return user.groups.filter(pk=self.editors_group.pk).exists()

    def add_editor(self, user):
        """Adds ``user`` as an editor for this ``ReaderStudy``."""
        return user.groups.add(self.editors_group)

    def remove_editor(self, user):
        """Removes ``user`` as an editor for this ``ReaderStudy``."""
        return user.groups.remove(self.editors_group)

    def is_reader(self, user):
        """Checks if ``user`` is a reader for this ``ReaderStudy``."""
        return user.groups.filter(pk=self.readers_group.pk).exists()

    def add_reader(self, user):
        """Adds ``user`` as a reader for this ``ReaderStudy``."""
        return user.groups.add(self.readers_group)

    def remove_reader(self, user):
        """Removes ``user`` as a reader for this ``ReaderStudy``."""
        return user.groups.remove(self.readers_group)

    @property
    def help_text(self):
        """The cleaned help text from the markdown sources"""
        return md2html(self.help_text_markdown, link_blank_target=True)

    @property
    def cleaned_case_text(self):
        if self.use_display_sets:
            return {}
        else:
            study_images = {im.name: im.api_url for im in self.images.all()}
            return {
                study_images.get(k): md2html(v)
                for k, v in self.case_text.items()
                if k in study_images
            }

    @property
    def study_image_names(self):
        """Names for all images added to this ``ReaderStudy``."""
        if self.use_display_sets:
            return self.ds_images
        else:
            return self.images.values_list("name", flat=True)

    @property
    def hanging_image_names(self):
        """Names for all images in the hanging list."""
        return [
            name for hanging in self.hanging_list for name in hanging.values()
        ]

    @property
    def hanging_list_valid(self):
        """
        Tests that all of the study images are included in the hanging list
        exactly once.
        """
        if self.use_display_sets:
            # As the answers is now linked to a display set, this check is
            # no longer necessary
            return True
        else:
            return not self.validate_hanging_list or sorted(
                self.study_image_names
            ) == sorted(self.hanging_image_names)

    def hanging_list_diff(self, provided=None):
        """
        Returns the diff between the images added to the study and the images
        in the hanging list.
        """
        comparison = provided or self.study_image_names
        return {
            "in_provided_list": set(comparison)
            - set(self.hanging_image_names),
            "in_hanging_list": set(self.hanging_image_names) - set(comparison),
        }

    @property
    def non_unique_study_image_names(self):
        """Returns all of the non-unique image names for this ``ReaderStudy``."""
        if self.use_display_sets:
            # As the answers is now linked to a display set, this check is
            # no longer necessary
            return []
        else:
            return [
                name
                for name, count in Counter(self.study_image_names).items()
                if count > 1
            ]

    @property
    def is_valid(self):
        """
        Returns ``True`` if the hanging list is valid and there are no
        duplicate image names in this ``ReaderStudy`` and ``False`` otherwise.
        """
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
        """Names of the images as they are grouped in the hanging list."""
        if self.use_display_sets:
            return self.display_sets.all().values_list("pk", flat=True)
        else:
            return [sorted(x.values()) for x in self.hanging_list]

    @property
    def has_ground_truth(self):
        return Answer.objects.filter(
            question__reader_study_id=self.id, is_ground_truth=True
        ).exists()

    @cached_property
    def ds_images(self):
        return sorted(
            list(
                self.display_sets.filter(
                    values__image__isnull=False
                ).values_list("values__image__name", flat=True)
            )
        )

    @cached_property
    def answerable_questions(self):
        """
        All questions for this ``ReaderStudy`` except those with answer type
        `heading`.
        """
        return self.questions.exclude(answer_type=Question.AnswerType.HEADING)

    @cached_property
    def answerable_question_count(self):
        """The number of answerable questions for this ``ReaderStudy``."""
        return self.answerable_questions.count()

    def add_ground_truth(self, *, data, user):  # noqa: C901
        """Add ground truth answers provided by ``data`` for this ``ReaderStudy``."""
        answers = []
        for gt in data:
            if self.use_display_sets:
                display_set = self.display_sets.get(pk=gt[self.case_field])
                images = []
            else:
                display_set = None
                images = self.images.filter(
                    name__in=gt[self.case_field].split(";")
                )
            for key in gt.keys():
                if key == self.case_field or key.endswith("__explanation"):
                    continue
                question = self.questions.get(question_text=key)
                _answer = json.loads(gt[key])
                if question.answer_type == Question.AnswerType.CHOICE:
                    try:
                        option = question.options.get(title=_answer)
                        _answer = option.pk
                    except CategoricalOption.DoesNotExist:
                        raise ValidationError(
                            f"Option '{_answer}' is not valid for question {question.question_text}"
                        )
                if question.answer_type in (
                    Question.AnswerType.MULTIPLE_CHOICE,
                    Question.AnswerType.MULTIPLE_CHOICE_DROPDOWN,
                ):
                    _answer = list(
                        question.options.filter(title__in=_answer).values_list(
                            "pk", flat=True
                        )
                    )
                kwargs = {
                    "creator": user,
                    "question": question,
                    "answer": _answer,
                    "is_ground_truth": True,
                }
                if self.use_display_sets:
                    kwargs["display_set"] = display_set
                else:
                    kwargs["images"] = images

                Answer.validate(**kwargs)
                try:
                    explanation = json.loads(gt.get(key + "__explanation", ""))
                except (json.JSONDecodeError, TypeError):
                    explanation = ""
                if self.use_display_sets:
                    answer_obj = Answer.objects.filter(
                        display_set=display_set,
                        question=question,
                        is_ground_truth=True,
                    ).first()

                else:
                    answer_obj = Answer.objects.filter(
                        images__in=images,
                        question=question,
                        is_ground_truth=True,
                    ).first()
                answers.append(
                    {
                        "answer_obj": answer_obj
                        or Answer(
                            creator=user,
                            question=question,
                            is_ground_truth=True,
                            explanation="",
                        ),
                        "answer": _answer,
                        "explanation": explanation,
                        "images": images,
                        "display_set": display_set,
                    }
                )

        for answer in answers:
            answer["answer_obj"].answer = answer["answer"]
            answer["answer_obj"].explanation = answer["explanation"]
            answer["answer_obj"].save()
            answer["answer_obj"].images.set(answer["images"])
            answer["answer_obj"].display_set = answer["display_set"]
            answer["answer_obj"].save()

    def get_hanging_list_images_for_user(self, *, user):
        """
        Returns a shuffled list of the hanging list images for a particular
        user.

        The shuffle is seeded with the users pk, and using ``RandomState``
        from numpy guarantees that the ordering will be consistent across
        python/library versions. Returns the normal list if
        ``shuffle_hanging_list`` is ``False``.
        """
        hanging_list = self.hanging_list_images

        if self.shuffle_hanging_list and hanging_list is not None:
            # In place shuffle
            RandomState(seed=int(user.pk)).shuffle(hanging_list)

        return hanging_list

    def generate_hanging_list(self):
        """
        Generates a new hanging list.

        Each image in the ``ReaderStudy`` is assigned to the primary port of its
        own hanging.
        """
        image_names = self.images.values_list("name", flat=True)
        hanging_list = [{"main": name} for name in image_names]
        self.hanging_list = hanging_list
        self.save()

    def get_progress_for_user(self, user):
        """Returns the percentage of completed hangings and questions for ``user``."""
        no_cases = (
            self.use_display_sets
            and self.display_sets.count() == 0
            or not self.use_display_sets
            and not self.hanging_list
        )
        if not self.is_valid or no_cases:
            return {"questions": 0.0, "hangings": 0.0, "diff": 0.0}

        hanging_list_count = (
            self.display_sets.count()
            if self.use_display_sets
            else len(self.hanging_list)
        )
        expected = hanging_list_count * self.answerable_question_count

        answers = Answer.objects.filter(
            question__in=self.answerable_questions,
            creator_id=user.id,
            is_ground_truth=False,
        ).distinct()
        answer_count = answers.count()

        if expected == 0 or answer_count == 0:
            return {"questions": 0.0, "hangings": 0.0, "diff": 0.0}

        if self.use_display_sets:
            completed_hangings = (
                self.display_sets.annotate(
                    answers_for_user=Count(
                        "answers",
                        filter=Q(
                            answers__creator=user,
                            answers__is_ground_truth=False,
                        ),
                    )
                ).filter(answers_for_user=self.answerable_question_count)
            ).count()
            questions = answer_count / expected * 100
            hangings = completed_hangings / hanging_list_count * 100
            return {
                "questions": questions,
                "hangings": hangings,
                "diff": questions - hangings,
            }
        else:
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
                    Image.objects.filter(readerstudies=self)
                    .annotate(
                        answers_for_user=Count(
                            Subquery(
                                Answer.objects.filter(
                                    creator=user,
                                    images=OuterRef("pk"),
                                    is_ground_truth=False,
                                ).values("pk")[:1]
                            )
                        )
                    )
                    .filter(answers_for_user=0)
                    .order_by("name")
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

            hangings = completed_hangings / hanging_list_count * 100
            questions = answer_count / expected * 100
            return {
                "questions": questions,
                "hangings": hangings,
                "diff": questions - hangings,
            }

    def score_for_user(self, user):
        """Returns the average and total score for answers given by ``user``."""
        return Answer.objects.filter(
            creator=user, question__reader_study=self, is_ground_truth=False
        ).aggregate(Sum("score"), Avg("score"))

    @cached_property
    def scores_by_user(self):
        """The average and total scores for this ``ReaderStudy`` grouped by user."""
        return (
            Answer.objects.filter(
                question__reader_study=self, is_ground_truth=False
            )
            .order_by("creator_id")
            .values("creator__username")
            .annotate(Sum("score"), Avg("score"))
            .order_by("-score__sum")
        )

    @cached_property
    def leaderboard(self):
        """The leaderboard for this ``ReaderStudy``."""
        n_hangings = (
            self.display_sets.count()
            if self.use_display_sets
            else len(self.hanging_list)
        )
        question_count = float(self.answerable_question_count) * n_hangings
        return {
            "question_count": question_count,
            "grouped_scores": self.scores_by_user,
        }

    @cached_property
    def statistics(self):
        """Statistics per question and case based on the total / average score."""
        scores_by_question = (
            Answer.objects.filter(
                question__reader_study=self, is_ground_truth=False
            )
            .order_by("question_id")
            .values("question__question_text")
            .annotate(Sum("score"), Avg("score"))
            .order_by("-score__avg")
        )

        if self.use_display_sets:
            scores_by_case = (
                Answer.objects.filter(
                    question__reader_study=self, is_ground_truth=False
                )
                .order_by("display_set")
                .values("display_set_id")
                .annotate(
                    Sum("score"),
                    Avg("score"),
                )
                .order_by("score__avg")
            )
        else:
            scores_by_case = (
                Answer.objects.filter(
                    question__reader_study=self, is_ground_truth=False
                )
                .order_by("images__name")
                .values("images__name", "images__pk")
                .annotate(
                    Sum("score"),
                    Avg("score"),
                )
                .order_by("score__avg")
            )

        options = {}
        for option in CategoricalOption.objects.filter(
            question__reader_study=self
        ).values("id", "title", "question"):
            qt = option["question"]
            options[qt] = options.get(qt, {})
            options[qt].update({option["id"]: option["title"]})

        ground_truths = {}
        questions = []
        for gt in (
            Answer.objects.filter(
                question__reader_study=self, is_ground_truth=True
            )
            .values(
                "display_set_id",
                "images__name",
                "answer",
                "question",
                "question__question_text",
                "question__answer_type",
            )
            .order_by("question__order", "question__created")
        ):
            questions.append(gt["question__question_text"])

            field = (
                gt["display_set_id"]
                if self.use_display_sets
                else gt["images__name"]
            )
            ground_truths[field] = ground_truths.get(field, {})

            if gt["question__answer_type"] in [
                Question.AnswerType.MULTIPLE_CHOICE,
                Question.AnswerType.MULTIPLE_CHOICE_DROPDOWN,
            ]:
                human_readable_answers = [
                    options[gt["question"]].get(a, a) for a in gt["answer"]
                ]
                human_readable_answers.sort()
                human_readable_answer = ", ".join(human_readable_answers)
            else:
                human_readable_answer = options.get(gt["question"], {}).get(
                    gt["answer"], gt["answer"]
                )

            ground_truths[field][
                gt["question__question_text"]
            ] = human_readable_answer

        questions = list(dict.fromkeys(questions))

        return {
            "max_score_questions": float(len(self.hanging_list))
            * self.scores_by_user.count(),
            "scores_by_question": scores_by_question,
            "max_score_cases": float(self.answerable_question_count)
            * self.scores_by_user.count(),
            "scores_by_case": scores_by_case,
            "ground_truths": ground_truths,
            "questions": questions,
        }

    @cached_property
    def values_for_interfaces(self):
        cache_key = f"{self._meta.app_label}.{self._meta.model_name}-{self.slug}-{self.modified.timestamp()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        for key in cache.keys(
            f"{self._meta.app_label}.{self._meta.model_name}-{self.slug}-*"
        ):
            cache.delete(key)
        vals = list(
            self.display_sets.select_related(
                "values", "values__interface", "values__image"
            )
            .values(
                "values__interface",
                "values__interface__slug",
                "values__id",
                "values__image__name",
                "values__file",
                "values__value",
            )
            .order_by("values__id")
            .distinct()
        )
        interfaces = {
            x["values__interface__slug"]: x["values__interface"] for x in vals
        }
        values_for_interfaces = {
            interface: {
                "id": interfaces[interface],
                "values": [
                    x
                    for x in vals
                    if x["values__interface__slug"] == interface
                ],
                "selected": "",
                "selected_image": "",
            }
            for interface in sorted(interfaces.keys())
        }

        cache.set(cache_key, values_for_interfaces, timeout=None)
        return values_for_interfaces


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


class DisplaySet(UUIDModel):
    reader_study = models.ForeignKey(
        ReaderStudy, related_name="display_sets", on_delete=models.PROTECT
    )
    values = models.ManyToManyField(
        ComponentInterfaceValue, blank=True, related_name="display_sets"
    )
    order = models.PositiveSmallIntegerField(default=0)

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        assign_perm(
            f"delete_{self._meta.model_name}",
            self.reader_study.editors_group,
            self,
        )
        assign_perm(
            f"change_{self._meta.model_name}",
            self.reader_study.editors_group,
            self,
        )
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

    @cached_property
    def value_list(self):
        cache_key = (
            f"{self._meta.app_label}.{self._meta.model_name}-{self.pk}-"
            f"{self.reader_study.modified.timestamp()}-"
            f"{self.modified.timestamp()}"
        )
        cached = cache.get(cache_key)
        if cached:
            return cached
        for key in cache.keys(
            f"{self._meta.app_label}.{self._meta.model_name}-{self.pk}-*"
        ):
            cache.delete(key)
        if self.is_editable:
            items = self.reader_study.values_for_interfaces
            for civ in self.values.all():
                items[civ.interface.slug]["selected"] = civ.id
                items[civ.interface.slug]["selected_image"] = (
                    civ.image_id or ""
                )
        else:
            items = {
                val.interface.slug: {
                    "title": val.title,
                    "selected_image": val.image_id,
                }
                for val in self.values.all()
            }
        cache.set(cache_key, items, timeout=None)
        return items

    @cached_property
    def is_editable(self):
        return not self.answers.exists()

    @property
    def api_url(self):
        """API url for this ``DisplaySet``."""
        return reverse(
            "api:reader-studies-display-set-detail", kwargs={"pk": self.pk}
        )

    @property
    def description(self):
        case_text = self.reader_study.case_text
        return "".join(
            [
                md2html(case_text[val.image.name])
                for val in self.values.filter(image__isnull=False)
                if val.image.name in case_text
            ]
        )


class AnswerType(models.TextChoices):
    # WARNING: Do not change the display text, these are used in the front end
    SINGLE_LINE_TEXT = "STXT", "Single line text"
    MULTI_LINE_TEXT = "MTXT", "Multi line text"
    BOOL = "BOOL", "Bool"
    NUMBER = "NUMB", "Number"
    HEADING = "HEAD", "Heading"
    BOUNDING_BOX_2D = "2DBB", "2D bounding box"
    MULTIPLE_2D_BOUNDING_BOXES = "M2DB", "Multiple 2D bounding boxes"
    DISTANCE_MEASUREMENT = "DIST", "Distance measurement"
    MULTIPLE_DISTANCE_MEASUREMENTS = ("MDIS", "Multiple distance measurements")
    POINT = "POIN", "Point"
    MULTIPLE_POINTS = "MPOI", "Multiple points"
    POLYGON = "POLY", "Polygon"
    MULTIPLE_POLYGONS = "MPOL", "Multiple polygons"
    CHOICE = "CHOI", "Choice"
    MULTIPLE_CHOICE = "MCHO", "Multiple choice"
    MULTIPLE_CHOICE_DROPDOWN = "MCHD", "Multiple choice dropdown"
    MASK = "MASK", "Mask"
    LINE = "LINE", "Line"
    MULTIPLE_LINES = "MLIN", "Multiple lines"


class Question(UUIDModel):
    AnswerType = AnswerType

    # What is the orientation of the question form when presented on the
    # front end?
    class Direction(models.TextChoices):
        HORIZONTAL = "H", "Horizontal"
        VERTICAL = "V", "Vertical"

    class ScoringFunction(models.TextChoices):
        ACCURACY = "ACC", "Accuracy score"

    SCORING_FUNCTIONS = {ScoringFunction.ACCURACY: accuracy_score}

    EXAMPLE_FOR_ANSWER_TYPE = {
        AnswerType.SINGLE_LINE_TEXT: "'\"answer\"'",
        AnswerType.MULTI_LINE_TEXT: "'\"answer\\nanswer\\nanswer\"'",
        AnswerType.BOOL: "'true'",
        AnswerType.CHOICE: "'\"option\"'",
        AnswerType.MULTIPLE_CHOICE: '\'["option1", "option2"]\'',
        AnswerType.MULTIPLE_CHOICE_DROPDOWN: '\'["option1", "option2"]\'',
    }

    reader_study = models.ForeignKey(
        ReaderStudy, on_delete=models.PROTECT, related_name="questions"
    )
    question_text = models.TextField()
    help_text = models.TextField(blank=True)
    answer_type = models.CharField(
        max_length=4,
        choices=AnswerType.choices,
        default=AnswerType.SINGLE_LINE_TEXT,
    )
    # Set blank because the requirement is dependent on answer_type and handled in the front end
    image_port = models.CharField(
        max_length=10, choices=ImagePort.choices, blank=True, default=""
    )
    required = models.BooleanField(default=True)
    direction = models.CharField(
        max_length=1, choices=Direction.choices, default=Direction.HORIZONTAL
    )
    scoring_function = models.CharField(
        max_length=3,
        choices=ScoringFunction.choices,
        default=ScoringFunction.ACCURACY,
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
        """Values that are included in this ``Question``'s csv export."""
        return [
            self.question_text,
            self.get_answer_type_display(),
            self.required,
            f"{self.get_image_port_display() + ' port,' if self.image_port else ''}",
        ]

    @property
    def api_url(self):
        """API url for this ``Question``."""
        return reverse(
            "api:reader-studies-question-detail", kwargs={"pk": self.pk}
        )

    @property
    def is_fully_editable(self):
        """``True`` if no ``Answer`` has been given for this ``Question``."""
        return self.answer_set.count() == 0

    @property
    def read_only_fields(self):
        """
        ``question_text``, ``answer_type``, ``image_port``, ``required`` if
        this ``Question`` is fully editable, an empty list otherwise.
        """
        if not self.is_fully_editable:
            return ["question_text", "answer_type", "image_port", "required"]
        return []

    @property
    def example_answer(self):
        return self.EXAMPLE_FOR_ANSWER_TYPE.get(
            self.answer_type, "<NO EXAMPLE YET>"
        )

    def calculate_score(self, answer, ground_truth):
        """
        Calculates the score for ``answer`` by applying ``scoring_function``
        to ``answer`` and ``ground_truth``.
        """
        if self.answer_type in (
            Question.AnswerType.MULTIPLE_CHOICE,
            Question.AnswerType.MULTIPLE_CHOICE_DROPDOWN,
        ):
            if len(answer) == 0 and len(ground_truth) == 0:
                return 1.0
            ans = np.zeros(max(len(answer), len(ground_truth)), dtype=int)
            gt = ans.copy()
            ans[: len(answer)] = answer
            gt[: len(ground_truth)] = ground_truth
        else:
            ans = [answer]
            gt = [ground_truth]
        return self.SCORING_FUNCTIONS[self.scoring_function](
            ans, gt, normalize=True
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
        if (self.answer_type in self.annotation_types) != bool(
            self.image_port
        ):
            raise ValidationError(
                "The image port must (only) be set for annotation questions."
            )

        if (
            self.answer_type in [self.AnswerType.BOOL, self.AnswerType.HEADING]
            and self.required
        ):
            raise ValidationError(
                "Bool or Heading answer types cannot not be Required "
                "(otherwise the user will need to tick a box for each image!)"
            )

    @property
    def annotation_types(self):
        return [
            self.AnswerType.BOUNDING_BOX_2D,
            self.AnswerType.MULTIPLE_2D_BOUNDING_BOXES,
            self.AnswerType.DISTANCE_MEASUREMENT,
            self.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            self.AnswerType.POINT,
            self.AnswerType.MULTIPLE_POINTS,
            self.AnswerType.POLYGON,
            self.AnswerType.MULTIPLE_POLYGONS,
            self.AnswerType.MASK,
            self.AnswerType.LINE,
            self.AnswerType.MULTIPLE_LINES,
        ]

    @property
    def allow_null_types(self):
        return [
            *self.annotation_types,
            self.AnswerType.CHOICE,
            self.AnswerType.NUMBER,
        ]

    def is_answer_valid(self, *, answer):
        """Validates ``answer`` against ``ANSWER_TYPE_SCHEMA``."""
        allowed_types = [{"$ref": f"#/definitions/{self.answer_type}"}]

        if self.answer_type in self.allow_null_types:
            allowed_types.append({"$ref": "#/definitions/null"})

        try:
            return (
                JSONValidator(
                    schema={**ANSWER_TYPE_SCHEMA, "anyOf": allowed_types}
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

    @property
    def is_image_type(self):
        return self.answer_type in [self.AnswerType.MASK]

    def get_absolute_url(self):
        return self.reader_study.get_absolute_url() + "#questions"


class CategoricalOption(models.Model):
    question = models.ForeignKey(
        Question, related_name="options", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=1024)
    default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({'' if self.default else 'not '}default)"


class Answer(UUIDModel):
    """
    An ``Answer`` can be provided to a ``Question`` that is a part of a
    ``ReaderStudy``.
    """

    # TODO do this for all UUID models
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    creator = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    images = models.ManyToManyField("cases.Image", related_name="answers")
    display_set = models.ForeignKey(
        DisplaySet, related_name="answers", on_delete=models.PROTECT, null=True
    )
    answer = models.JSONField(
        null=True, validators=[JSONValidator(schema=ANSWER_TYPE_SCHEMA)]
    )
    answer_image = models.ForeignKey(
        "cases.Image", null=True, on_delete=models.PROTECT
    )
    is_ground_truth = models.BooleanField(default=False)
    score = models.FloatField(null=True)
    explanation = models.TextField(blank=True, default="")
    history = HistoricalRecords(
        excluded_fields=[
            "created",
            "modified",
            "creator",
            "question",
            "images",
            "is_ground_truth",
            "score",
        ]
    )

    _csv_headers = Question.csv_headers + [
        "Created",
        "Answer",
        "Images",
        "Creator",
    ]

    class Meta:
        ordering = ("created",)

    def __str__(self):
        return f"{self.question.question_text} {self.answer} ({self.creator})"

    @property
    def api_url(self):
        """API url for this ``Answer``."""
        return reverse(
            "api:reader-studies-answer-detail", kwargs={"pk": self.pk}
        )

    @cached_property
    def history_values(self):
        return self.history.values_list("answer", "history_date")

    @property
    def csv_values(self):
        """Values that are included in this ``Answer``'s csv export."""
        return (
            self.question.csv_values
            + [
                self.created.isoformat(),
                self.answer_text,
                "; ".join(self.images.values_list("name", flat=True)),
                self.creator.username,
            ]
            + list(itertools.chain(*self.history_values))
        )

    @property
    def csv_headers(self):
        return self._csv_headers + list(
            itertools.chain(
                *[
                    [f"Answer-{x}", f"Modification_date-{x}"]
                    for x in range(len(self.history_values))
                ]
            )
        )

    @staticmethod
    def validate(  # noqa: C901
        *,
        creator,
        question,
        answer,
        images=None,
        display_set=None,
        is_ground_truth=False,
        instance=None,
    ):
        """Validates all fields provided for ``answer``."""
        if question.answer_type == Question.AnswerType.HEADING:
            # Maintained for historical consistency
            raise ValidationError("Headings are not answerable.")

        if not question.is_answer_valid(answer=answer):
            raise ValidationError(
                f"Your answer is not the correct type. "
                f"{question.get_answer_type_display()} expected, "
                f"{type(answer)} found."
            )

        if (images is None or len(images) == 0) and display_set is None:
            raise ValidationError(
                "You must specify the images or display sey that this answer "
                "corresponds to."
            )
        if images is not None and len(images) > 0 and display_set is not None:
            raise ValidationError(
                "You can only specify one of these two field: images, display_set."
            )
        if images is not None:
            reader_study_images = question.reader_study.images.all()
            for im in images:
                if im not in reader_study_images:
                    raise ValidationError(
                        f"Image {im} does not belong to this reader study."
                    )

        if display_set is not None:
            if display_set.reader_study != question.reader_study:
                raise ValidationError(
                    f"Display set {display_set} does not belong to this reader study."
                )
        if not is_ground_truth:
            if (
                images is not None
                and len(images) > 0
                and (
                    Answer.objects.exclude(pk=getattr(instance, "pk", None))
                    .filter(
                        creator=creator,
                        question=question,
                        is_ground_truth=False,
                        images__in=images,
                    )
                    .annotate(count_images=Count("images", distinct=True))
                    .filter(count_images=len(images))
                    .exists()
                )
            ):
                raise ValidationError(
                    f"User {creator} has already answered this question "
                    f"for this set of images."
                )
            if display_set is not None and (
                Answer.objects.exclude(pk=getattr(instance, "pk", None))
                .filter(
                    creator=creator,
                    question=question,
                    is_ground_truth=False,
                    display_set=display_set,
                )
                .exists()
            ):
                raise ValidationError(
                    f"User {creator} has already answered this question "
                    f"for this display set."
                )

        if not creator.has_perm("read_readerstudy", question.reader_study):
            raise ValidationError("This user is not a reader for this study.")

        valid_options = question.options.values_list("id", flat=True)
        if question.answer_type == Question.AnswerType.CHOICE:
            if not question.required:
                valid_options = (*valid_options, None)
            if answer not in valid_options:
                raise ValidationError(
                    "Provided option is not valid for this question"
                )

        if question.answer_type in (
            Question.AnswerType.MULTIPLE_CHOICE,
            Question.AnswerType.MULTIPLE_CHOICE_DROPDOWN,
        ):
            if not all(x in valid_options for x in answer):
                raise ValidationError(
                    "Provided options are not valid for this question"
                )

        if (
            question.answer_type == Question.AnswerType.NUMBER
            and question.required
            and answer is None
        ):
            raise ValidationError(
                "Answer for required question cannot be None"
            )

    @property
    def answer_text(self):
        if self.question.answer_type == Question.AnswerType.CHOICE:
            return (
                self.question.options.filter(pk=self.answer)
                .values_list("title", flat=True)
                .first()
                or ""
            )
        if self.question.answer_type in (
            Question.AnswerType.MULTIPLE_CHOICE,
            Question.AnswerType.MULTIPLE_CHOICE_DROPDOWN,
        ):
            return ", ".join(
                self.question.options.filter(pk__in=self.answer)
                .order_by("title")
                .values_list("title", flat=True)
            )
        return self.answer

    def calculate_score(self, ground_truth):
        """Calculate the score for this ``Answer`` based on ``ground_truth``."""
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
        assign_perm(f"change_{self._meta.model_name}", self.creator, self)


class ReaderStudyPermissionRequest(RequestBase):
    """
    When a user wants to read a reader study, editors have the option of
    reviewing each user before accepting or rejecting them. This class records
    the needed info for that.
    """

    reader_study = models.ForeignKey(
        ReaderStudy,
        help_text="To which reader study has the user requested access?",
        on_delete=models.CASCADE,
    )
    rejection_text = models.TextField(
        blank=True,
        help_text=(
            "The text that will be sent to the user with the reason for their "
            "rejection."
        ),
    )

    @property
    def base_object(self):
        return self.reader_study

    @property
    def object_name(self):
        return self.base_object.title

    @property
    def add_method(self):
        return self.base_object.add_reader

    @property
    def remove_method(self):
        return self.base_object.remove_reader

    @property
    def permission_list_url(self):
        return reverse(
            "reader-studies:permission-request-list",
            kwargs={"slug": self.base_object.slug},
        )

    def __str__(self):
        return f"{self.object_name} registration request by user {self.user.username}"

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            process_access_request(request_object=self)

    def delete(self):
        ct = ContentType.objects.filter(
            app_label=self._meta.app_label, model=self._meta.model_name
        ).get()
        Follow.objects.filter(object_id=self.pk, content_type=ct).delete()
        super().delete()

    class Meta(RequestBase.Meta):
        unique_together = (("reader_study", "user"),)
