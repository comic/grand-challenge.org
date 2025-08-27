from math import ceil

from actstream.models import Follow
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import Avg, Count, Q, Sum
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.functional import cached_property
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm, remove_perm
from referencing.exceptions import Unresolvable
from stdimage import JPEGField

from grandchallenge.anatomy.models import BodyStructure
from grandchallenge.components.models import (
    CIVForObjectMixin,
    CIVSetObjectPermissionsMixin,
    CIVSetStringRepresentationMixin,
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
    InterfaceKindChoices,
    OverlaySegmentsMixin,
    ValuesForInterfacesMixin,
)
from grandchallenge.components.schemas import ANSWER_TYPE_SCHEMA
from grandchallenge.core.fields import HexColorField, RegexField
from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.storage import (
    get_logo_path,
    get_social_image_path,
    public_s3_storage,
)
from grandchallenge.core.templatetags.bleach import md2html
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
    process_access_request,
)
from grandchallenge.core.validators import JSONValidator
from grandchallenge.core.vendored.django.validators import StepValueValidator
from grandchallenge.hanging_protocols.models import (
    HangingProtocolMixin,
    ViewportNames,
)
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.organizations.models import Organization
from grandchallenge.publications.models import Publication
from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)
from grandchallenge.reader_studies.metrics import accuracy_score
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.templatetags.workstations import (
    get_workstation_path_and_query_string,
)
from grandchallenge.workstations.utils import reassign_workstation_permissions

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


CASE_TEXT_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": {"type": "string"},
}


class ReaderStudy(
    UUIDModel,
    TitleSlugDescriptionModel,
    HangingProtocolMixin,
    ValuesForInterfacesMixin,
):
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

    workstation = models.ForeignKey(
        "workstations.Workstation", on_delete=models.PROTECT
    )
    workstation_sessions = models.ManyToManyField(
        "workstations.Session",
        through="WorkstationSessionReaderStudy",
        related_name="reader_studies",
        blank=True,
        editable=False,
    )
    workstation_config = models.ForeignKey(
        "workstation_configs.WorkstationConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    optional_hanging_protocols = models.ManyToManyField(
        "hanging_protocols.HangingProtocol",
        through="OptionalHangingProtocolReaderStudy",
        related_name="optional_for_reader_study",
        blank=True,
        help_text="Optional alternative hanging protocols for this reader study",
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
    instant_verification = models.BooleanField(
        default=False,
        help_text=(
            "In an educational reader study, enabling this setting will allow the "
            "user to go through the reader study faster. The 'Save and continue' "
            "button will be replaced by a 'Verify and continue' button which will "
            "show the answer verification pop up and allow the user to save and go "
            "to the next case upon dismissal."
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
            "by navigating back to previous cases. 'Allow case navigation' must "
            "be checked as well to enable this setting."
        ),
    )
    enable_autosaving = models.BooleanField(
        default=False,
        help_text=(
            "If true, answers to questions are saved in the background while a "
            "user reads a case. 'Allow Answer Modification' must be "
            "enabled as well for this to work."
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
        default=0,
        help_text=(
            "The number of cases for which answers should roll over. "
            "It can be used for repeated readings with slightly different hangings. "
            "For instance, if set to 1. Case 2 will start with the answers from case 1; "
            "whereas case 3 starts anew but its answers will roll over to case 4. "
            "Setting it to 0 (default) means answers will not roll over."
        ),
    )
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
    leaderboard_accessible_to_readers = models.BooleanField(
        default=False,
        help_text=(
            "If checked, readers can see the leaderboard. "
            "Usernames and avatars will be hidden to protect other readers' privacy."
        ),
    )
    end_of_study_text_markdown = models.TextField(
        blank=True,
        help_text="Text to show when a user has completed the reader study",
    )
    max_credits = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="The maximum number of credits that may be consumed for this reader study. Leave blank to allow unlimited usage.",
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        verbose_name_plural = "reader studies"
        ordering = ("created",)
        permissions = [
            ("read_readerstudy", "Can read reader study"),
            ("view_leaderboard", "Can view leaderboard"),
        ]

    copy_fields = {
        "workstation",
        "workstation_config",
        "logo",
        "social_image",
        "help_text_markdown",
        "shuffle_hanging_list",
        "is_educational",
        "instant_verification",
        "roll_over_answers_for_n_cases",
        "allow_answer_modification",
        "enable_autosaving",
        "allow_case_navigation",
        "allow_show_all_annotations",
        "access_request_handling",
        "public",
        "leaderboard_accessible_to_readers",
        "publications",
        "modalities",
        "structures",
        "organizations",
        "end_of_study_text_markdown",
    }

    optional_copy_fields = [
        "editors_group",
        "readers_group",
        "questions",
        "display_sets",
        "case_text",
        "view_content",
        "hanging_protocol",
        "optional_hanging_protocols",
    ]

    def __str__(self):
        return f"{self.title}"

    @property
    def ground_truth_file_headers(self):
        return ["case"] + [
            q.question_text for q in self.ground_truth_applicable_questions
        ]

    def get_ground_truth_csv_dict(self):
        if self.display_sets.count() == 0:
            return {}
        result = []
        answers = {
            q.question_text: q.example_answer
            for q in self.ground_truth_applicable_questions
        }
        for images in self.image_groups:
            _answers = answers.copy()
            _answers["case"] = str(images)
            result.append(_answers)
        return result

    def get_example_ground_truth_csv_text(self, limit=None):
        if self.display_sets.count() == 0:
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
    def api_url(self) -> str:
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

        # Allow editors to view the leaderboard
        assign_perm("view_leaderboard", self.editors_group, self)
        if self.leaderboard_accessible_to_readers:
            assign_perm("view_leaderboard", self.readers_group, self)
        else:
            remove_perm("view_leaderboard", self.readers_group, self)

        if self.public:
            assign_perm(f"view_{self._meta.model_name}", reg_and_anon, self)
        else:
            remove_perm(f"view_{self._meta.model_name}", reg_and_anon, self)

    def clean(self):
        if self.case_text is None:
            self.case_text = {}
        if self.view_content is None:
            self.view_content = {}

        self._clean_questions()

    def _clean_questions(self):
        for question in self.questions.all():
            question.clean()

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()

        super().save(*args, **kwargs)

        self.assign_permissions()
        reassign_workstation_permissions(
            groups=(self.readers_group, self.editors_group),
            workstation=self.workstation,
        )

    def delete(self, *args, **kwargs):
        ct = ContentType.objects.filter(
            app_label=self._meta.app_label, model=self._meta.model_name
        ).get()
        Follow.objects.filter(object_id=self.pk, content_type=ct).delete()
        super().delete(*args, **kwargs)

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
    def help_text(self) -> str:
        """The cleaned help text from the markdown sources"""
        return md2html(
            self.help_text_markdown,
            link_blank_target=True,
            create_permalink_for_headers=False,
        )

    @property
    def help_text_safe(self) -> str:
        """The cleaned help text from the markdown sources"""
        return md2html(
            self.help_text_markdown,
            link_blank_target=True,
            create_permalink_for_headers=False,
        )

    @property
    def end_of_study_text_safe(self) -> str:
        return md2html(
            self.end_of_study_text_markdown,
            link_blank_target=True,
            create_permalink_for_headers=False,
        )

    @cached_property
    def study_image_names(self):
        """Names for all images added to this ``ReaderStudy``."""
        return sorted(
            list(
                self.display_sets.filter(
                    values__image__isnull=False
                ).values_list("values__image__name", flat=True)
            )
        )

    @property
    def image_groups(self):
        """Names of the images as they are grouped in the hanging list."""
        return self.display_sets.all().values_list("pk", flat=True)

    @property
    def has_ground_truth(self) -> bool:
        return Answer.objects.filter(
            question__reader_study_id=self.id, is_ground_truth=True
        ).exists()

    @cached_property
    def answerable_questions(self):
        """
        All questions for this ``ReaderStudy`` except those with answer type
        `heading`.
        """
        return self.questions.exclude(
            answer_type__in=AnswerType.get_non_answerable_types()
        )

    @cached_property
    def answerable_question_count(self):
        """The number of answerable questions for this ``ReaderStudy``."""
        return self.answerable_questions.count()

    def get_progress_for_user(self, user):
        """Returns the percentage of completed hangings and questions for ``user``."""
        if self.display_sets.count() == 0:
            return {"questions": 0.0, "hangings": 0.0, "diff": 0.0}

        n_display_sets = self.display_sets.count()
        expected = n_display_sets * self.answerable_question_count

        answers = Answer.objects.filter(
            question__in=self.answerable_questions,
            creator_id=user.id,
            is_ground_truth=False,
        ).distinct()
        answer_count = answers.count()

        if expected == 0 or answer_count == 0:
            return {"questions": 0.0, "hangings": 0.0, "diff": 0.0}

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
        hangings = completed_hangings / n_display_sets * 100
        return {
            "questions": questions,
            "hangings": hangings,
            "diff": questions - hangings,
        }

    @cached_property
    def questions_with_ground_truth(self):
        return self.questions.annotate(
            gt_count=Count("answer", filter=Q(answer__is_ground_truth=True))
        ).filter(gt_count__gte=1)

    @cached_property
    def ground_truth_applicable_questions(self):
        return self.answerable_questions.exclude(
            answer_type__in=AnswerType.get_annotation_types()
        ).all()

    @property
    def ground_truth_count(self):
        return (
            Answer.objects.filter(
                question__in=self.ground_truth_applicable_questions,
                is_ground_truth=True,
            )
            .values("display_set", "question")
            .distinct()
            .count()
        )

    @property
    def ground_truth_is_complete(self):
        count_gt_viable_questions = len(self.ground_truth_applicable_questions)
        return (
            self.ground_truth_count
            == self.display_sets.count() * count_gt_viable_questions
        )

    def score_for_user(self, user):
        """Returns the average and total score for answers given by ``user``."""

        return Answer.objects.filter(
            creator=user,
            question__in=self.questions_with_ground_truth,
            is_ground_truth=False,
        ).aggregate(Sum("score"), Avg("score"))

    @cached_property
    def scores_by_user(self):
        """The average and total scores for this ``ReaderStudy`` grouped by user."""
        return (
            Answer.objects.filter(
                question__in=self.questions_with_ground_truth,
                is_ground_truth=False,
            )
            .order_by("creator_id")
            .values("creator__username")
            .annotate(Sum("score"), Avg("score"))
            .order_by("-score__sum")
        )

    @cached_property
    def leaderboard(self):
        """The leaderboard for this ``ReaderStudy``."""
        n_hangings = self.display_sets.count()
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

        scores_by_case = (
            DisplaySet.objects.filter(reader_study=self)
            .select_related("reader_study__workstation__config")
            .annotate(
                sum=Sum(
                    "answers__score", filter=Q(answers__is_ground_truth=False)
                ),
                avg=Avg(
                    "answers__score", filter=Q(answers__is_ground_truth=False)
                ),
            )
            .order_by("avg")
            .all()
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
                "answer",
                "question",
                "question__question_text",
                "question__answer_type",
            )
            .order_by("question__order", "question__created")
        ):
            questions.append(gt["question__question_text"])

            field = gt["display_set_id"]
            ground_truths[field] = ground_truths.get(field, {})

            if (
                gt["question__answer_type"]
                == Question.AnswerType.MULTIPLE_CHOICE
            ):
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
            "max_score_questions": float(len(self.display_sets.all()))
            * self.scores_by_user.count(),
            "scores_by_question": scores_by_question,
            "max_score_cases": float(self.answerable_question_count)
            * self.scores_by_user.count(),
            "scores_by_case": scores_by_case,
            "ground_truths": ground_truths,
            "questions": questions,
        }

    @property
    def next_display_set_order(self):
        last = self.display_sets.last()
        highest = getattr(last, "order", 0)
        return (highest + 10) // 10 * 10

    @property
    def civ_sets_list_url(self):
        return reverse(
            "reader-studies:display_sets", kwargs={"slug": self.slug}
        )

    @property
    def bulk_delete_url(self):
        return reverse(
            "reader-studies:display-sets-bulk-delete",
            kwargs={"slug": self.slug},
        )

    @property
    def interface_viewname(self):
        return "components:component-interface-list-reader-studies"

    @property
    def list_url(self):
        return reverse("reader-studies:list")

    @property
    def civ_sets_related_manager(self):
        return self.display_sets

    @property
    def civ_set_model(self):
        return DisplaySet

    def create_civ_set(self, data):
        return self.civ_set_model.objects.create(reader_study=self, **data)

    @property
    def create_civ_set_url(self):
        return reverse(
            "reader-studies:display-set-create", kwargs={"slug": self.slug}
        )

    @property
    def create_civ_set_batch_url(self):
        return reverse(
            "reader-studies:display-sets-create", kwargs={"slug": self.slug}
        )

    @cached_property
    def interfaces_and_values(self):
        interfaces_and_values = super().interfaces_and_values
        interfaces_and_values.interfaces.update(
            set(
                self.questions.filter(interface__isnull=False).values_list(
                    "interface__slug", flat=True
                )
            )
        )
        return interfaces_and_values

    @property
    def credits_consumed(self):
        total = 0
        for session in self.session_utilizations.annotate(
            num=Count("reader_studies")
        ):
            total += session.credits_consumed / session.num
        return ceil(total)

    @property
    def is_launchable(self):
        return (
            self.max_credits is None
            or self.credits_consumed < self.max_credits
        )

    @cached_property
    def questions_with_interactive_algorithm(self):
        return self.questions.exclude(interactive_algorithm="")


class ReaderStudyUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(ReaderStudy, on_delete=models.CASCADE)


class ReaderStudyGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {
            "read_readerstudy",
            "view_leaderboard",
            "change_readerstudy",
            "view_readerstudy",
        }
    )

    content_object = models.ForeignKey(ReaderStudy, on_delete=models.CASCADE)


class WorkstationSessionReaderStudy(models.Model):
    # Through table for optional hanging protocols
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    reader_study = models.ForeignKey(ReaderStudy, on_delete=models.CASCADE)
    workstation_session = models.ForeignKey(
        "workstations.Session", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("reader_study", "workstation_session"),)


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


class DisplaySet(
    CIVSetStringRepresentationMixin,
    CIVSetObjectPermissionsMixin,
    CIVForObjectMixin,
    UUIDModel,
):
    reader_study = models.ForeignKey(
        ReaderStudy, related_name="display_sets", on_delete=models.PROTECT
    )
    values = models.ManyToManyField(
        ComponentInterfaceValue, blank=True, related_name="display_sets"
    )
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255, default="", blank=True)

    def assign_permissions(self):
        assign_perm(
            self.delete_perm,
            self.reader_study.editors_group,
            self,
        )
        assign_perm(
            self.change_perm,
            self.reader_study.editors_group,
            self,
        )
        assign_perm(
            self.view_perm,
            self.reader_study.editors_group,
            self,
        )
        assign_perm(
            self.view_perm,
            self.reader_study.readers_group,
            self,
        )

    class Meta:
        ordering = ("order", "created")
        constraints = [
            models.UniqueConstraint(
                fields=["title", "reader_study"],
                name="unique_display_set_title",
                condition=~Q(title=""),
            )
        ]

    @cached_property
    def is_editable(self):
        return not self.answers.exists()

    @property
    def base_object(self):
        return self.reader_study

    @property
    def api_url(self) -> str:
        """API url for this ``DisplaySet``."""
        return reverse(
            "api:reader-studies-display-set-detail", kwargs={"pk": self.pk}
        )

    @cached_property
    def workstation_url(self):
        """The URL to answer this display set in a workstation"""
        url = reverse(
            "workstations:workstation-session-create",
            kwargs={"slug": self.reader_study.workstation.slug},
        )
        pqs = get_workstation_path_and_query_string(display_set=self)
        return f"{url}{pqs.path}?{pqs.query_string}"

    @property
    def description(self) -> str:
        case_text = self.reader_study.case_text

        if case_text:
            seen_names = set()
            output = ""

            for val in self.values.all():
                try:
                    name = val.image.name
                except AttributeError:
                    continue

                if name in case_text and name not in seen_names:
                    output += md2html(case_text[name])
                    seen_names.add(name)

            return output
        else:
            return ""

    @property
    def standard_index(self) -> int:
        return [*self.reader_study.display_sets.all()].index(self)

    @property
    def update_url(self):
        return reverse(
            "reader-studies:display-set-update",
            kwargs={"slug": self.base_object.slug, "pk": self.pk},
        )

    def get_absolute_url(self):
        return reverse(
            "reader-studies:display-set-detail",
            kwargs={"slug": self.base_object.slug, "pk": self.pk},
        )

    @property
    def delete_url(self):
        return reverse(
            "reader-studies:display-set-delete",
            kwargs={"slug": self.base_object.slug, "pk": self.pk},
        )

    def add_civ(self, *, civ):
        super().add_civ(civ=civ)
        return self.values.add(civ)

    def remove_civ(self, *, civ):
        super().remove_civ(civ=civ)
        return self.values.remove(civ)

    def get_civ_for_interface(self, interface):
        return self.values.get(interface=interface)


class DisplaySetUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(DisplaySet, on_delete=models.CASCADE)


class DisplaySetGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"change_displayset", "delete_displayset", "view_displayset"}
    )

    content_object = models.ForeignKey(DisplaySet, on_delete=models.CASCADE)


class AnswerType(models.TextChoices):
    # WARNING: Do not change the display text, these are used in the front end
    TEXT = "TEXT", "Text"
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
    MASK = "MASK", "Mask"
    LINE = "LINE", "Line"
    MULTIPLE_LINES = "MLIN", "Multiple lines"
    ANGLE = "ANGL", "Angle"
    MULTIPLE_ANGLES = "MANG", "Multiple angles"
    ELLIPSE = "ELLI", "Ellipse"
    MULTIPLE_ELLIPSES = "MELL", "Multiple ellipses"
    THREE_POINT_ANGLE = "3ANG", "Three-point angle"
    MULTIPLE_THREE_POINT_ANGLES = "M3AN", "Multiple three-point angles"

    @staticmethod
    def get_choice_types():
        return [
            AnswerType.CHOICE,
            AnswerType.MULTIPLE_CHOICE,
        ]

    @staticmethod
    def get_annotation_types():
        return [
            AnswerType.BOUNDING_BOX_2D,
            AnswerType.MULTIPLE_2D_BOUNDING_BOXES,
            AnswerType.DISTANCE_MEASUREMENT,
            AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            AnswerType.POINT,
            AnswerType.MULTIPLE_POINTS,
            AnswerType.POLYGON,
            AnswerType.MULTIPLE_POLYGONS,
            AnswerType.MASK,
            AnswerType.LINE,
            AnswerType.MULTIPLE_LINES,
            AnswerType.ANGLE,
            AnswerType.MULTIPLE_ANGLES,
            AnswerType.ELLIPSE,
            AnswerType.MULTIPLE_ELLIPSES,
            AnswerType.THREE_POINT_ANGLE,
            AnswerType.MULTIPLE_THREE_POINT_ANGLES,
        ]

    @staticmethod
    def get_image_types():
        return [
            AnswerType.MASK,
        ]

    @staticmethod
    def get_widget_required_types():
        return [
            AnswerType.TEXT,
            AnswerType.CHOICE,
        ]

    @staticmethod
    def get_non_answerable_types():
        return [AnswerType.HEADING]


ANSWER_TYPE_TO_INTERFACE_KIND_MAP = {
    AnswerType.TEXT: [InterfaceKindChoices.STRING],
    AnswerType.BOOL: [InterfaceKindChoices.BOOL],
    AnswerType.NUMBER: [
        InterfaceKindChoices.FLOAT,
        InterfaceKindChoices.INTEGER,
    ],
    AnswerType.HEADING: [],
    AnswerType.BOUNDING_BOX_2D: [InterfaceKindChoices.TWO_D_BOUNDING_BOX],
    AnswerType.MULTIPLE_2D_BOUNDING_BOXES: [
        InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES
    ],
    AnswerType.DISTANCE_MEASUREMENT: [
        InterfaceKindChoices.DISTANCE_MEASUREMENT
    ],
    AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS: [
        InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS
    ],
    AnswerType.POINT: [InterfaceKindChoices.POINT],
    AnswerType.MULTIPLE_POINTS: [InterfaceKindChoices.MULTIPLE_POINTS],
    AnswerType.POLYGON: [InterfaceKindChoices.POLYGON],
    AnswerType.MULTIPLE_POLYGONS: [InterfaceKindChoices.MULTIPLE_POLYGONS],
    AnswerType.LINE: [InterfaceKindChoices.LINE],
    AnswerType.MULTIPLE_LINES: [InterfaceKindChoices.MULTIPLE_LINES],
    AnswerType.CHOICE: [InterfaceKindChoices.CHOICE],
    AnswerType.MULTIPLE_CHOICE: [InterfaceKindChoices.MULTIPLE_CHOICE],
    AnswerType.MASK: [
        InterfaceKindChoices.SEGMENTATION,
    ],
    AnswerType.ANGLE: [InterfaceKindChoices.ANGLE],
    AnswerType.MULTIPLE_ANGLES: [InterfaceKindChoices.MULTIPLE_ANGLES],
    AnswerType.ELLIPSE: [InterfaceKindChoices.ELLIPSE],
    AnswerType.MULTIPLE_ELLIPSES: [InterfaceKindChoices.MULTIPLE_ELLIPSES],
    AnswerType.THREE_POINT_ANGLE: [InterfaceKindChoices.THREE_POINT_ANGLE],
    AnswerType.MULTIPLE_THREE_POINT_ANGLES: [
        InterfaceKindChoices.MULTIPLE_THREE_POINT_ANGLES
    ],
}


class QuestionWidgetKindChoices(models.TextChoices):
    ACCEPT_REJECT = "ACCEPT_REJECT", "Accept/Reject Findings"
    NUMBER_INPUT = "NUMBER_INPUT", "Number Input"
    NUMBER_RANGE = "NUMBER_RANGE", "Number Range"
    TEXT_INPUT = "TEXT_INPUT", "Text Input"
    TEXT_AREA = "TEXT_AREA", "Text Area"
    SELECT_MULTIPLE = "SELECT_MULTIPLE", "Select Multiple"
    CHECKBOX_SELECT_MULTIPLE = (
        "CHECKBOX_SELECT_MULTIPLE",
        "Checkbox Select Multiple",
    )
    SELECT = "SELECT", "Select"
    RADIO_SELECT = "RADIO_SELECT", "Radio Select"


ANSWER_TYPE_TO_QUESTION_WIDGET = {
    AnswerType.TEXT: [
        QuestionWidgetKindChoices.TEXT_INPUT,
        QuestionWidgetKindChoices.TEXT_AREA,
    ],
    AnswerType.BOOL: [],
    AnswerType.NUMBER: [
        QuestionWidgetKindChoices.NUMBER_INPUT,
        QuestionWidgetKindChoices.NUMBER_RANGE,
    ],
    AnswerType.HEADING: [],
    AnswerType.BOUNDING_BOX_2D: [],
    AnswerType.MULTIPLE_2D_BOUNDING_BOXES: [
        QuestionWidgetKindChoices.ACCEPT_REJECT
    ],
    AnswerType.DISTANCE_MEASUREMENT: [],
    AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS: [
        QuestionWidgetKindChoices.ACCEPT_REJECT
    ],
    AnswerType.POINT: [],
    AnswerType.MULTIPLE_POINTS: [QuestionWidgetKindChoices.ACCEPT_REJECT],
    AnswerType.POLYGON: [],
    AnswerType.MULTIPLE_POLYGONS: [QuestionWidgetKindChoices.ACCEPT_REJECT],
    AnswerType.CHOICE: [
        QuestionWidgetKindChoices.RADIO_SELECT,
        QuestionWidgetKindChoices.SELECT,
    ],
    AnswerType.MULTIPLE_CHOICE: [
        QuestionWidgetKindChoices.CHECKBOX_SELECT_MULTIPLE,
        QuestionWidgetKindChoices.SELECT_MULTIPLE,
    ],
    AnswerType.MASK: [],
    AnswerType.LINE: [],
    AnswerType.MULTIPLE_LINES: [QuestionWidgetKindChoices.ACCEPT_REJECT],
    AnswerType.ANGLE: [],
    AnswerType.MULTIPLE_ANGLES: [QuestionWidgetKindChoices.ACCEPT_REJECT],
    AnswerType.ELLIPSE: [],
    AnswerType.MULTIPLE_ELLIPSES: [QuestionWidgetKindChoices.ACCEPT_REJECT],
    AnswerType.THREE_POINT_ANGLE: [],
    AnswerType.MULTIPLE_THREE_POINT_ANGLES: [
        QuestionWidgetKindChoices.ACCEPT_REJECT
    ],
}

ANSWER_TYPE_TO_QUESTION_WIDGET_CHOICES = {
    answer_type: [(option.name, option.label) for option in options]
    for answer_type, options in ANSWER_TYPE_TO_QUESTION_WIDGET.items()
}

EMPTY_ANSWER_VALUES = {
    AnswerType.TEXT: "",
    AnswerType.NUMBER: None,
    AnswerType.CHOICE: None,
    AnswerType.BOOL: None,
    AnswerType.BOUNDING_BOX_2D: None,
    AnswerType.MULTIPLE_2D_BOUNDING_BOXES: None,
    AnswerType.DISTANCE_MEASUREMENT: None,
    AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS: None,
    AnswerType.POINT: None,
    AnswerType.MULTIPLE_POINTS: None,
    AnswerType.POLYGON: None,
    AnswerType.MULTIPLE_POLYGONS: None,
    AnswerType.LINE: None,
    AnswerType.MULTIPLE_LINES: None,
    AnswerType.MASK: None,
    AnswerType.ANGLE: None,
    AnswerType.MULTIPLE_ANGLES: None,
    AnswerType.ELLIPSE: None,
    AnswerType.MULTIPLE_ELLIPSES: None,
    AnswerType.MULTIPLE_CHOICE: [],
    AnswerType.THREE_POINT_ANGLE: None,
    AnswerType.MULTIPLE_THREE_POINT_ANGLES: None,
}

ANSWER_TYPE_TO_INTERACTIVE_ALGORITHM = {
    AnswerType.HEADING: [],
    AnswerType.TEXT: [],
    AnswerType.NUMBER: [],
    AnswerType.CHOICE: [],
    AnswerType.BOOL: [],
    AnswerType.BOUNDING_BOX_2D: [],
    AnswerType.MULTIPLE_2D_BOUNDING_BOXES: [],
    AnswerType.DISTANCE_MEASUREMENT: [],
    AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS: [],
    AnswerType.POINT: [],
    AnswerType.MULTIPLE_POINTS: [],
    AnswerType.POLYGON: [],
    AnswerType.MULTIPLE_POLYGONS: [],
    AnswerType.LINE: [],
    AnswerType.MULTIPLE_LINES: [],
    AnswerType.MASK: [InteractiveAlgorithmChoices.ULS23_BASELINE],
    AnswerType.ANGLE: [],
    AnswerType.MULTIPLE_ANGLES: [],
    AnswerType.ELLIPSE: [],
    AnswerType.MULTIPLE_ELLIPSES: [],
    AnswerType.MULTIPLE_CHOICE: [],
    AnswerType.THREE_POINT_ANGLE: [],
    AnswerType.MULTIPLE_THREE_POINT_ANGLES: [],
}

ANSWER_TYPE_TO_INTERACTIVE_ALGORITHM_CHOICES = {
    answer_type: [(option.value, option.label) for option in options]
    for answer_type, options in ANSWER_TYPE_TO_INTERACTIVE_ALGORITHM.items()
}


class ImagePort(models.TextChoices):
    MAIN = "M", "Main"
    SECONDARY = "S", "Secondary"
    TERTIARY = "TERTIARY", "Tertiary"
    QUATERNARY = "QUATERNARY", "Quaternary"
    QUINARY = "QUINARY", "Quinary"
    SENARY = "SENARY", "Senary"
    SEPTENARY = "SEPTENARY", "Septenary"
    OCTONARY = "OCTONARY", "Octonary"
    NONARY = "NONARY", "Nonary"
    DENARY = "DENARY", "Denary"
    UNDENARY = "UNDENARY", "Undenary"
    DUODENARY = "DUODENARY", "Duodenary"
    TREDENARY = "TREDENARY", "Tredenary"
    QUATTUORDENARY = "QUATTUORDENARY", "Quattuordenary"
    QUINDENARY = "QUINDENARY", "Quindenary"
    SEXDENARY = "SEXDENARY", "Sexdenary"
    SEPTENDENARY = "SEPTENDENARY", "Septendenary"
    OCTODENARY = "OCTODENARY", "Octodenary"
    NOVEMDENARY = "NOVEMDENARY", "Novemdenary"
    VIGINTENARY = "VIGINTENARY", "Vigintenary"


# This was redefined in the hanging protocol app and not unified
IMAGE_PORT_TO_VIEWPORT_NAME = {
    ImagePort.MAIN: ViewportNames.main,
    ImagePort.SECONDARY: ViewportNames.secondary,
    ImagePort.TERTIARY: ViewportNames.tertiary,
    ImagePort.QUATERNARY: ViewportNames.quaternary,
    ImagePort.QUINARY: ViewportNames.quinary,
    ImagePort.SENARY: ViewportNames.senary,
    ImagePort.SEPTENARY: ViewportNames.septenary,
    ImagePort.OCTONARY: ViewportNames.octonary,
    ImagePort.NONARY: ViewportNames.nonary,
    ImagePort.DENARY: ViewportNames.denary,
    ImagePort.UNDENARY: ViewportNames.undenary,
    ImagePort.DUODENARY: ViewportNames.duodenary,
    ImagePort.TREDENARY: ViewportNames.tredenary,
    ImagePort.QUATTUORDENARY: ViewportNames.quattuordenary,
    ImagePort.QUINDENARY: ViewportNames.quindenary,
    ImagePort.SEXDENARY: ViewportNames.sexdenary,
    ImagePort.SEPTENDENARY: ViewportNames.septendenary,
    ImagePort.OCTODENARY: ViewportNames.octodenary,
    ImagePort.NOVEMDENARY: ViewportNames.novemdenary,
    ImagePort.VIGINTENARY: ViewportNames.vigintenary,
}


class Question(UUIDModel, OverlaySegmentsMixin):
    AnswerType = AnswerType
    ImagePort = ImagePort

    # What is the orientation of the question form when presented on the
    # front end?
    class Direction(models.TextChoices):
        HORIZONTAL = "H", "Horizontal"
        VERTICAL = "V", "Vertical"

    class ScoringFunction(models.TextChoices):
        ACCURACY = "ACC", "Accuracy score"

    SCORING_FUNCTIONS = {ScoringFunction.ACCURACY: accuracy_score}

    EXAMPLE_FOR_ANSWER_TYPE = {
        AnswerType.TEXT: "'\"answer\"'",
        AnswerType.NUMBER: "'1'",
        AnswerType.BOOL: "'true'",
        AnswerType.CHOICE: "'\"option\"'",
        AnswerType.MULTIPLE_CHOICE: '\'["option1", "option2"]\'',
    }

    reader_study = models.ForeignKey(
        ReaderStudy, on_delete=models.PROTECT, related_name="questions"
    )
    question_text = models.TextField()
    help_text = models.TextField(blank=True)
    answer_type = models.CharField(
        max_length=4,
        choices=AnswerType.choices,
    )
    # Set blank because the requirement is dependent on answer_type and handled in the front end
    image_port = models.CharField(
        max_length=14, choices=ImagePort.choices, blank=True, default=""
    )
    default_annotation_color = HexColorField(
        blank=True,
        default="",
        help_text="Default color for displaying and creating annotations for this question",
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
    interface = models.ForeignKey(
        ComponentInterface, on_delete=models.PROTECT, null=True, blank=True
    )
    widget = models.CharField(
        choices=QuestionWidgetKindChoices.choices, max_length=24, blank=True
    )
    interactive_algorithm = models.CharField(
        choices=InteractiveAlgorithmChoices.choices,
        max_length=32,
        blank=True,
        help_text="Which interactive algorithm should be used for this question?",
    )
    answer_max_value = models.SmallIntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="Maximum value for answers of type Number. Can only be set in combination with the 'Number input' or 'Number Range' widgets.",
    )
    answer_min_value = models.SmallIntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="Minimum value for answers of type Number. Can only be set in combination with the 'Number input' or 'Number Range' widgets.",
    )
    answer_step_size = models.DecimalField(
        null=True,
        blank=True,
        default=None,
        max_digits=6,
        decimal_places=3,
        validators=[MinValueValidator(limit_value=0.001)],
        help_text="Step size for answers of type Number. Defaults to 1, allowing only integer values. Can only be set in combination with the 'Number input' or 'Number Range' widgets.",
    )
    answer_min_length = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="Minimum length for answers of type Text. Can only be set in combination with the 'Text Input' or 'Text Area' widgets.",
    )
    answer_max_length = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="Maximum length for answers of type Text. Can only be set in combination with the 'Text Input' or 'Text Area' widgets.",
    )
    answer_match_pattern = RegexField(
        blank=True,
        help_text="Regular expression to match a pattern for answers of type Text. Can only be set in combination with the 'Text Input' or 'Text Area' widgets.",
    )
    empty_answer_confirmation = models.BooleanField(
        default=False,
        help_text="Require an explicit confirmation when saving an empty answer to this question.",
    )
    empty_answer_confirmation_label = models.TextField(
        blank=True,
        help_text="Label to show when confirming an empty answer.",
    )

    class Meta:
        ordering = ("order", "created")
        permissions = [
            (
                "add_interactive_algorithm_to_question",
                "Can add interactive algorithm to question",
            )
        ]

    copy_fields = {
        "question_text",
        "help_text",
        "answer_type",
        "image_port",
        "default_annotation_color",
        "required",
        "direction",
        "scoring_function",
        "order",
        "interface",
        "look_up_table",
        "overlay_segments",
        "widget",
        "interactive_algorithm",
        "answer_max_value",
        "answer_min_value",
        "answer_step_size",
        "answer_min_length",
        "answer_max_length",
        "answer_match_pattern",
        "empty_answer_confirmation",
        "empty_answer_confirmation_label",
    }

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
    def api_url(self) -> str:
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
        if not self.is_fully_editable:
            return [
                "question_text",
                "answer_type",
                "image_port",
                "required",
                "overlay_segments",
                "widget",
                "answer_min_value",
                "answer_max_value",
                "answer_step_size",
                "answer_min_length",
                "answer_max_length",
                "answer_match_pattern",
                "interface",
            ]
        return []

    @property
    def example_answer(self):
        return self.EXAMPLE_FOR_ANSWER_TYPE.get(
            self.answer_type, "<NO EXAMPLE YET>"
        )

    @property
    def allowed_component_interfaces(self):
        allowed_interfaces = ANSWER_TYPE_TO_INTERFACE_KIND_MAP.get(
            self.answer_type
        )
        return ComponentInterface.objects.filter(kind__in=allowed_interfaces)

    def calculate_score(self, answer, ground_truth):
        """
        Calculates the score for ``answer`` by applying ``scoring_function``
        to ``answer`` and ``ground_truth``.
        """
        if self.answer_type == Question.AnswerType.MULTIPLE_CHOICE:
            if len(answer) == 0 and len(ground_truth) == 0:
                return 1.0

            elements = max(len(answer), len(ground_truth))
            ans = [0] * elements
            gt = [0] * elements

            ans[: len(answer)] = answer
            gt[: len(ground_truth)] = ground_truth
        else:
            ans = [answer]
            gt = [ground_truth]
        return self.SCORING_FUNCTIONS[self.scoring_function](gt, ans)

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
        super().clean()
        self._clean_answer_type()
        self._clean_empty_answer_confirmation()
        self._clean_interface()
        self._clean_image_port()
        self._clean_widget()
        self._clean_widget_options()
        self._clean_interactive_algorithm()

    def _clean_answer_type(self):
        # Make sure that the image port is only set when using drawn
        # annotations.
        if (
            self.answer_type in self.AnswerType.get_annotation_types()
        ) != bool(self.image_port):
            raise ValidationError(
                "The image port must (only) be set for annotation questions"
            )

        if (
            self.answer_type in [self.AnswerType.BOOL, self.AnswerType.HEADING]
            and self.required
        ):
            raise ValidationError(
                "Bool or Heading answer types cannot not be Required "
                "(otherwise the user will need to tick a box for each image!)"
            )

        if (
            self.default_annotation_color
            and self.answer_type not in self.AnswerType.get_annotation_types()
        ):
            raise ValidationError(
                "Default annotation color should only be set for annotation questions"
            )

    def _clean_empty_answer_confirmation(self):
        if not self.empty_answer_confirmation:
            return

        if self.required:
            raise ValidationError(
                "Cannot have answer confirmation and have a question be "
                "required at the same time"
            )

        if self.answer_type not in (
            *AnswerType.get_annotation_types(),
            AnswerType.NUMBER,
            AnswerType.TEXT,
        ):
            raise ValidationError(
                "Empty answer confirmation is not supported for "
                f"{self.get_answer_type_display()} type questions. "
                "For (Multiple) Choice types, you can add an empty option "
                "and make the question required"
            )

    def _clean_interface(self):
        if (
            self.interface
            and self.interface not in self.allowed_component_interfaces
        ):
            raise ValidationError(
                f"The socket {self.interface} is not allowed for this "
                f"question type ({self.answer_type})"
            )

    def _clean_image_port(self):
        if self.image_port and self.reader_study.view_content:
            try:
                viewport_content = self.reader_study.view_content[
                    IMAGE_PORT_TO_VIEWPORT_NAME[self.image_port]
                ]
            except KeyError:
                raise ValidationError(
                    f"The {self.get_image_port_display()} view port has not been defined. "
                    f"Please update the view content of this reader study or select a different view port for question {self}."
                )

            if (
                ComponentInterface.objects.filter(
                    slug__in=viewport_content,
                    kind__in=InterfaceKind.interface_type_image(),
                ).count()
                < 1
            ):
                raise ValidationError(
                    f"The {self.get_image_port_display()} view port does not contain an image. "
                    f"Please update the view content of this reader study or select a different view port for question {self}."
                )

    def _clean_widget(self):
        if self.widget:
            if (
                self.widget
                not in ANSWER_TYPE_TO_QUESTION_WIDGET[self.answer_type]
            ):
                raise ValidationError(
                    f"For questions with answer type {self.answer_type} you can only "
                    f"enable the following widgets: "
                    f"{oxford_comma(ANSWER_TYPE_TO_QUESTION_WIDGET[self.answer_type])}."
                )
            if self.widget == QuestionWidgetKindChoices.ACCEPT_REJECT:
                if not self.interface:
                    raise ValidationError(
                        f"In order to use the {self.get_widget_display()} widget, "
                        f"you need to provide a default answer."
                    )
        elif self.answer_type in self.AnswerType.get_widget_required_types():
            raise ValidationError(
                f"The question type {self.get_answer_type_display()} requires a widget."
            )

    def _clean_widget_options(self):
        self._clean_number_options()
        self._clean_text_options()

    def _clean_number_options(self):
        is_step_size_set = self.answer_step_size is not None
        is_min_value_set = self.answer_min_value is not None
        is_max_value_set = self.answer_max_value is not None
        is_number_validation_set = any(
            [is_step_size_set, is_min_value_set, is_max_value_set]
        )
        is_range_configured = all(
            [is_step_size_set, is_min_value_set, is_max_value_set]
        )

        perform_number_validation = (
            self.answer_type == AnswerType.NUMBER
            and self.widget
            in (
                QuestionWidgetKindChoices.NUMBER_INPUT,
                QuestionWidgetKindChoices.NUMBER_RANGE,
            )
        )
        if is_number_validation_set and not perform_number_validation:
            # Server side number validation can only be done with AnswerType.NUMBER.
            # Currently, client side number validation is only done with
            # QuestionWidgetKindChoices.NUMBER_INPUT or NUMBER_RANGE. If we
            # allowed number validation with other widgets here the readers may
            # not get feedback from the viewer about why their answers are rejected
            raise ValidationError(
                "Min and max values and the step size for answers "
                "can only be defined in combination with the "
                "Number Input or Number Range widgets for answers of type Number."
            )

        if (
            self.widget == QuestionWidgetKindChoices.NUMBER_RANGE
            and not is_range_configured
        ):
            raise ValidationError(
                "Number Range widget requires answer min, max and step values to be set."
            )

        if (
            is_min_value_set
            and is_max_value_set
            and self.answer_max_value <= self.answer_min_value
        ):
            raise ValidationError(
                "Answer max value needs to be bigger than answer min value."
            )

    def _clean_text_options(self):
        is_min_length_set = self.answer_min_length is not None
        is_max_length_set = self.answer_max_length is not None
        is_pattern_match_set = len(self.answer_match_pattern) > 0

        is_text_validation_set = any(
            [is_min_length_set, is_max_length_set, is_pattern_match_set]
        )
        if is_text_validation_set and not self.answer_type == AnswerType.TEXT:
            raise ValidationError(
                "Minimum length, maximum length, and/or pattern match for answers "
                "can only be defined for the answers of type Text.",
            )

        if (
            is_min_length_set
            and is_max_length_set
            and self.answer_max_length < self.answer_min_length
        ):
            raise ValidationError(
                "Answer max length needs to be bigger than answer min length."
            )

    def _clean_interactive_algorithm(self):
        if (
            self.interactive_algorithm
            and self.interactive_algorithm
            not in ANSWER_TYPE_TO_INTERACTIVE_ALGORITHM[self.answer_type]
        ):
            raise ValidationError(
                f"{self.interactive_algorithm} is not a valid option for answer type {self.answer_type}."
            )

    @property
    def empty_answer_value(self):
        """Returns the answer value which is considered to be empty"""
        if self.answer_type not in EMPTY_ANSWER_VALUES:
            raise RuntimeError(
                f"{self.answer_type} has no representation of an empty value."
            )
        return EMPTY_ANSWER_VALUES[self.answer_type]

    def is_answer_valid(self, *, answer):
        """Validates ``answer`` against ``ANSWER_TYPE_SCHEMA``."""
        if self.answer_type == Question.AnswerType.HEADING:  # Never valid
            return False

        allowed_types = [{"$ref": f"#/definitions/{self.answer_type}"}]

        if self.empty_answer_value is None:
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
        except Unresolvable:
            raise RuntimeError(
                f"#/definitions/{self.answer_type} needs to be defined in "
                "ANSWER_TYPE_SCHEMA."
            )

    @property
    def validators(self):
        if self.answer_min_value is not None:
            yield MinValueValidator(self.answer_min_value)

        if self.answer_max_value is not None:
            yield MaxValueValidator(self.answer_max_value)

        if self.answer_step_size:
            yield StepValueValidator(
                limit_value=self.answer_step_size,
                offset=self.answer_min_value,
            )

        if self.answer_min_length is not None:
            yield MinLengthValidator(self.answer_min_length)

        if self.answer_max_length is not None:
            yield MaxLengthValidator(self.answer_max_length)

        if self.answer_match_pattern:
            yield RegexValidator(
                regex=self.answer_match_pattern,
                message="Enter a valid answer that matches with the requested format",
            )

    @property
    def is_image_type(self):
        return self.answer_type in self.AnswerType.get_image_types()

    def get_absolute_url(self):
        return self.reader_study.get_absolute_url() + "#questions"


class QuestionUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Question, on_delete=models.CASCADE)


class QuestionGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"view_question"})

    content_object = models.ForeignKey(Question, on_delete=models.CASCADE)


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
    last_edit_duration = models.DurationField(null=True)
    total_edit_duration = models.DurationField(null=True)

    class Meta:
        ordering = ("created",)
        unique_together = (
            ("creator", "display_set", "question", "is_ground_truth"),
        )

    def __str__(self):
        return f"{self.question.question_text} {self.answer} ({self.creator})"

    @property
    def api_url(self) -> str:
        """API url for this ``Answer``."""
        return reverse(
            "api:reader-studies-answer-detail", kwargs={"pk": self.pk}
        )

    # TODO this should be a model clean method
    @staticmethod
    def validate(  # noqa: C901
        *,
        creator,
        question,
        answer,
        display_set,
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

        if display_set.reader_study != question.reader_study:
            raise ValidationError(
                f"Display set {display_set} does not belong to this reader study."
            )

        if not is_ground_truth:
            if (
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

        if question.answer_type == Question.AnswerType.MULTIPLE_CHOICE:
            if not all(x in valid_options for x in answer):
                raise ValidationError(
                    "Provided options are not valid for this question"
                )

        # Image types can have empty answers while an image is being uploaded,
        # as such we never consider it empty.
        answer_is_empty = (
            answer == question.empty_answer_value
            and not question.is_image_type
        )
        if question.required and answer_is_empty:
            raise ValidationError(
                "Answer for required question cannot be empty"
            )

        if not answer_is_empty:
            for validator in question.validators:
                validator(answer)

    @property
    def answer_text(self):
        if self.question.answer_type == Question.AnswerType.CHOICE:
            return (
                self.question.options.filter(pk=self.answer)
                .values_list("title", flat=True)
                .first()
                or ""
            )

        if self.question.answer_type == Question.AnswerType.MULTIPLE_CHOICE:
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

    def save(self, *args, calculate_score=True, **kwargs):
        adding = self._state.adding

        if not self.is_ground_truth and calculate_score:
            try:
                ground_truth = Answer.objects.get(
                    question=self.question,
                    is_ground_truth=True,
                    display_set=self.display_set,
                )
            except Answer.DoesNotExist:
                pass  # Nothing to do here
            else:
                self.calculate_score(ground_truth=ground_truth.answer)

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        # Allow the editors and creator to view this answer
        assign_perm(
            "view_answer",
            self.question.reader_study.editors_group,
            self,
        )
        assign_perm(
            "delete_answer",
            self.question.reader_study.editors_group,
            self,
        )
        assign_perm("view_answer", self.creator, self)
        assign_perm("change_answer", self.creator, self)


class AnswerUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"view_answer", "change_answer"})

    content_object = models.ForeignKey(Answer, on_delete=models.CASCADE)


class AnswerGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"view_answer", "delete_answer"})

    content_object = models.ForeignKey(Answer, on_delete=models.CASCADE)


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

    def delete(self, *args, **kwargs):
        ct = ContentType.objects.filter(
            app_label=self._meta.app_label, model=self._meta.model_name
        ).get()
        Follow.objects.filter(object_id=self.pk, content_type=ct).delete()
        super().delete(*args, **kwargs)

    class Meta(RequestBase.Meta):
        unique_together = (("reader_study", "user"),)


class OptionalHangingProtocolReaderStudy(models.Model):
    # Through table for optional hanging protocols
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    reader_study = models.ForeignKey(ReaderStudy, on_delete=models.CASCADE)
    hanging_protocol = models.ForeignKey(
        "hanging_protocols.HangingProtocol", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("reader_study", "hanging_protocol"),)
