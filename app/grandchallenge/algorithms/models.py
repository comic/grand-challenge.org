import logging
from datetime import datetime

from actstream.actions import follow, is_following
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Q, Sum
from django.db.models.signals import post_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from django.template.defaultfilters import truncatechars
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import get_valid_filename
from django.utils.timezone import now
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm, remove_perm
from pictures.models import PictureField

from grandchallenge.algorithms.tasks import update_algorithm_average_duration
from grandchallenge.anatomy.models import BodyStructure
from grandchallenge.charts.specs import stacked_bar
from grandchallenge.components.models import (  # noqa: F401
    CIVForObjectMixin,
    ComponentImage,
    ComponentInterface,
    ComponentInterfaceValue,
    ComponentJob,
    ComponentJobManager,
    ImportStatusChoices,
    Tarball,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.storage import (
    get_logo_path,
    get_social_image_path,
    protected_s3_storage,
    public_s3_storage,
)
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
    process_access_request,
)
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.hanging_protocols.models import HangingProtocolMixin
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.organizations.models import Organization
from grandchallenge.publications.models import Publication
from grandchallenge.reader_studies.models import DisplaySet
from grandchallenge.subdomains.utils import reverse
from grandchallenge.utilization.models import JobUtilization
from grandchallenge.workstations.models import Workstation
from grandchallenge.workstations.utils import reassign_workstation_permissions

logger = logging.getLogger(__name__)


def annotate_input_output_counts(queryset, inputs=None, outputs=None):
    return queryset.annotate(
        input_count=Count("inputs", distinct=True),
        output_count=Count("outputs", distinct=True),
        relevant_input_count=Count(
            "inputs",
            filter=Q(inputs__in=inputs) if inputs is not None else Q(),
            distinct=True,
        ),
        relevant_output_count=Count(
            "outputs",
            filter=Q(outputs__in=outputs) if outputs is not None else Q(),
            distinct=True,
        ),
    )


class AlgorithmInterfaceManager(models.Manager):
    def create(
        self,
        *,
        inputs,
        outputs,
        **kwargs,
    ):
        if not inputs or not outputs:
            raise ValidationError(
                "An interface must have at least one input and one output."
            )

        obj = get_existing_interface_for_inputs_and_outputs(
            inputs=inputs, outputs=outputs
        )
        if not obj:
            obj = super().create(**kwargs)
            obj.inputs.set(inputs)
            obj.outputs.set(outputs)

        return obj

    def delete(self):
        raise NotImplementedError("Bulk delete is not allowed.")


class AlgorithmInterface(UUIDModel):
    inputs = models.ManyToManyField(
        to=ComponentInterface,
        related_name="inputs",
        through="algorithms.AlgorithmInterfaceInput",
    )
    outputs = models.ManyToManyField(
        to=ComponentInterface,
        related_name="outputs",
        through="algorithms.AlgorithmInterfaceOutput",
    )

    objects = AlgorithmInterfaceManager()

    class Meta:
        ordering = ("created",)

    def delete(self, *args, **kwargs):
        raise ValidationError("AlgorithmInterfaces cannot be deleted.")


class AlgorithmInterfaceInput(models.Model):
    input = models.ForeignKey(ComponentInterface, on_delete=models.CASCADE)
    interface = models.ForeignKey(AlgorithmInterface, on_delete=models.CASCADE)


class AlgorithmInterfaceOutput(models.Model):
    output = models.ForeignKey(ComponentInterface, on_delete=models.CASCADE)
    interface = models.ForeignKey(AlgorithmInterface, on_delete=models.CASCADE)


def get_existing_interface_for_inputs_and_outputs(
    *, inputs, outputs, model=AlgorithmInterface
):
    annotated_qs = annotate_input_output_counts(
        model.objects.all(), inputs=inputs, outputs=outputs
    )
    try:
        return annotated_qs.get(
            relevant_input_count=len(inputs),
            relevant_output_count=len(outputs),
            input_count=len(inputs),
            output_count=len(outputs),
        )
    except ObjectDoesNotExist:
        return None


class Algorithm(UUIDModel, TitleSlugDescriptionModel, HangingProtocolMixin):
    GPUTypeChoices = GPUTypeChoices

    editors_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="editors_of_algorithm",
    )
    users_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="users_of_algorithm",
    )
    logo = PictureField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        aspect_ratios=["1/1"],
        width_field="logo_width",
        height_field="logo_height",
    )
    social_image = PictureField(
        upload_to=get_social_image_path,
        storage=public_s3_storage,
        blank=True,
        help_text="An image for this algorithm which is displayed when you post the link for this algorithm on social media. Should have a resolution of 640x320 px (1280x640 px for best display).",
        aspect_ratios=[None],
        width_field="social_image_width",
        height_field="social_image_height",
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
    optional_hanging_protocols = models.ManyToManyField(
        "hanging_protocols.HangingProtocol",
        through="OptionalHangingProtocolAlgorithm",
        related_name="optional_for_algorithm",
        blank=True,
        help_text="Optional alternative hanging protocols for this algorithm",
    )
    public = models.BooleanField(
        default=False,
        help_text=(
            "Should this algorithm be visible to all users on the algorithm "
            "overview page? This does not grant all users permission to use "
            "this algorithm. Users will still need to be added to the "
            "algorithm users group in order to do that."
        ),
    )
    access_request_handling = models.CharField(
        max_length=25,
        choices=AccessRequestHandlingOptions.choices,
        default=AccessRequestHandlingOptions.MANUAL_REVIEW,
        help_text=("How would you like to handle access requests?"),
    )
    detail_page_markdown = models.TextField(blank=True)
    job_create_page_markdown = models.TextField(blank=True)
    additional_terms_markdown = models.TextField(
        blank=True,
        help_text=(
            "By using this algorithm, users agree to the site wide "
            "terms of service. If your algorithm has any additional "
            "terms of usage, define them here."
        ),
    )
    interfaces = models.ManyToManyField(
        to=AlgorithmInterface,
        related_name="algorithm_interfaces",
        through="algorithms.AlgorithmAlgorithmInterface",
    )
    publications = models.ManyToManyField(
        Publication,
        blank=True,
        help_text="The publications associated with this algorithm",
    )
    modalities = models.ManyToManyField(
        ImagingModality,
        blank=True,
        help_text="The imaging modalities supported by this algorithm",
    )
    structures = models.ManyToManyField(
        BodyStructure,
        blank=True,
        help_text="The structures supported by this algorithm",
    )
    organizations = models.ManyToManyField(
        Organization,
        blank=True,
        help_text="The organizations associated with this algorithm",
        related_name="algorithms",
    )
    minimum_credits_per_job = models.PositiveIntegerField(
        default=20,
        help_text=(
            "The minimum number of credits that are required for each execution of this algorithm. "
            "The actual number of credits required may be higher than this depending on the "
            "algorithms configuration."
        ),
        validators=[
            MinValueValidator(limit_value=20),
            MaxValueValidator(limit_value=1000),
        ],
    )
    time_limit = models.PositiveIntegerField(
        default=60 * 60,
        help_text="Time limit for inference jobs in seconds",
        validators=[
            MinValueValidator(
                limit_value=settings.COMPONENTS_MINIMUM_JOB_DURATION
            ),
            MaxValueValidator(
                limit_value=settings.COMPONENTS_MAXIMUM_JOB_DURATION
            ),
        ],
    )
    job_requires_gpu_type = models.CharField(
        max_length=4,
        blank=True,
        default=GPUTypeChoices.NO_GPU,
        choices=GPUTypeChoices.choices,
        help_text="What GPU to attach to this algorithms inference jobs",
    )
    job_requires_memory_gb = models.PositiveSmallIntegerField(
        default=8,
        help_text="How much main memory (DRAM) to assign to this algorithms inference jobs",
    )
    average_duration = models.DurationField(
        null=True,
        default=None,
        editable=False,
        help_text="The average duration of successful jobs.",
    )
    repo_name = models.CharField(blank=True, max_length=512)
    recurse_submodules = models.BooleanField(
        default=False,
        help_text="Do a recursive git pull when a GitHub repo is linked to this algorithm.",
    )
    highlight = models.BooleanField(
        default=False,
        help_text="Should this algorithm be advertised on the home page?",
    )
    contact_email = models.EmailField(
        blank=True,
        help_text="This email will be listed as the contact email for the algorithm and will be visible to all users of Grand Challenge.",
    )
    display_editors = models.BooleanField(
        null=True,
        blank=True,
        help_text="Should the editors of this algorithm be listed on the information page?",
    )
    summary = models.TextField(
        blank=True,
        help_text="Briefly describe your algorithm and how it was developed.",
    )
    mechanism = models.TextField(
        blank=True,
        help_text="Provide a short technical description of your algorithm.",
    )
    validation_and_performance = models.TextField(
        blank=True,
        help_text="If you have performance metrics about your algorithm, you can report them here.",
    )
    uses_and_directions = models.TextField(
        blank=True,
        default="This algorithm was developed for research purposes only.",
        help_text="Describe what your algorithm can be used for, but also what it should not be used for.",
    )
    warnings = models.TextField(
        blank=True,
        help_text="Describe potential risks and inappropriate settings for using the algorithm.",
    )
    common_error_messages = models.TextField(
        blank=True,
        help_text="Describe common error messages a user might encounter when trying out your algorithm and provide solutions for them.",
    )
    editor_notes = models.TextField(
        blank=True,
        help_text="Add internal notes such as the deployed version number, code and data locations, etc. Only visible to editors.",
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        ordering = ("created",)
        permissions = [("execute_algorithm", "Can execute algorithm")]
        constraints = [
            models.UniqueConstraint(
                fields=["repo_name"],
                name="unique_repo_name",
                condition=~Q(repo_name=""),
            )
        ]

    def __str__(self):
        return f"{self.title}"

    def get_absolute_url(self):
        return reverse("algorithms:detail", kwargs={"slug": self.slug})

    @property
    def api_url(self) -> str:
        return reverse("api:algorithm-detail", kwargs={"pk": self.pk})

    @property
    def algorithm_interfaces_locked(self):
        return False

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()
            self.workstation_id = (
                self.workstation_id or self.default_workstation.pk
            )

        super().save(*args, **kwargs)

        self.assign_permissions()
        reassign_workstation_permissions(
            groups=(self.users_group, self.editors_group),
            workstation=self.workstation,
        )

    def create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.users_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_users"
        )

    def assign_permissions(self):
        # Editors and users can view this algorithm
        assign_perm("view_algorithm", self.editors_group, self)
        assign_perm("view_algorithm", self.users_group, self)
        # Editors and users can execute this algorithm
        assign_perm("execute_algorithm", self.editors_group, self)
        assign_perm("execute_algorithm", self.users_group, self)
        # Editors can change this algorithm
        assign_perm("change_algorithm", self.editors_group, self)

        reg_and_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        if self.public:
            assign_perm("view_algorithm", reg_and_anon, self)
        else:
            remove_perm("view_algorithm", reg_and_anon, self)

    @cached_property
    def active_image(self):
        """
        Returns
        -------
            The desired version for this algorithm or None
        """
        try:
            return (
                self.algorithm_container_images.executable_images()
                .filter(is_desired_version=True)
                .get()
            )
        except ObjectDoesNotExist:
            return None

    @cached_property
    def active_model(self):
        """
        Returns
        -------
            The desired model version for this algorithm or None
        """
        try:
            return self.algorithm_models.filter(is_desired_version=True).get()
        except ObjectDoesNotExist:
            return None

    @cached_property
    def credits_per_job(self):
        job = Job(
            algorithm_image=self.active_image,
            time_limit=self.time_limit,
            requires_gpu_type=self.job_requires_gpu_type,
            requires_memory_gb=self.job_requires_memory_gb,
        )
        job.init_credits_consumed()
        return job.credits_consumed

    @property
    def image_upload_in_progress(self):
        return self.algorithm_container_images.filter(
            import_status__in=(
                ImportStatusChoices.STARTED,
                ImportStatusChoices.QUEUED,
            )
        ).exists()

    @property
    def model_upload_in_progress(self):
        return self.algorithm_models.filter(
            import_status__in=(ImportStatusChoices.INITIALIZED,)
        ).exists()

    @cached_property
    def default_workstation(self):
        """
        Returns the default workstation, creating it if it does not already
        exist.
        """
        w, created = Workstation.objects.get_or_create(
            slug=settings.DEFAULT_WORKSTATION_SLUG
        )

        if created:
            w.title = settings.DEFAULT_WORKSTATION_SLUG
            w.save()

        return w

    @property
    def algorithm_interface_manager(self):
        return self.interfaces

    @property
    def algorithm_interface_through_model_manager(self):
        return AlgorithmAlgorithmInterface.objects.filter(algorithm=self)

    @property
    def additional_inputs_field(self):
        return None

    @property
    def additional_outputs_field(self):
        return None

    @property
    def algorithm_interface_create_url(self):
        return reverse(
            "algorithms:interface-create", kwargs={"slug": self.slug}
        )

    @property
    def algorithm_interface_delete_viewname(self):
        return "algorithms:interface-delete"

    @property
    def algorithm_interface_list_url(self):
        return reverse("algorithms:interface-list", kwargs={"slug": self.slug})

    def is_editor(self, user):
        return user.groups.filter(pk=self.editors_group.pk).exists()

    def add_editor(self, user):
        return user.groups.add(self.editors_group)

    def remove_editor(self, user):
        return user.groups.remove(self.editors_group)

    def is_user(self, user):
        return user.groups.filter(pk=self.users_group.pk).exists()

    def add_user(self, user):
        return user.groups.add(self.users_group)

    def remove_user(self, user):
        return user.groups.remove(self.users_group)

    @cached_property
    def linked_component_interfaces(self):
        return (
            ComponentInterface.objects.filter(
                Q(inputs__in=self.interfaces.all())
                | Q(outputs__in=self.interfaces.all())
            )
            .distinct()
            .order_by("pk")
        )

    @cached_property
    def user_statistics(self):
        return (
            get_user_model()
            .objects.select_related("verification", "user_profile")
            .annotate(
                job_count=Count(
                    "pk", filter=Q(job__algorithm_image__algorithm=self)
                )
            )
            .filter(job_count__gt=0)
            .order_by("-job_count")[:10]
        )

    @property
    def usage_chart_statuses(self):
        """What statuses should be included on the chart"""
        return [Job.SUCCESS, Job.CANCELLED, Job.FAILURE]

    @cached_property
    def usage_statistics(self):
        """The number of jobs for this algorithm faceted by month and status"""
        return (
            Job.objects.filter(
                algorithm_image__algorithm=self,
                status__in=self.usage_chart_statuses,
            )
            .values("status", "created__year", "created__month")
            .annotate(job_count=Count("status"))
            .order_by("created__year", "created__month", "status")
        )

    @cached_property
    def usage_chart(self):
        """Vega lite chart of the usage of this algorithm"""
        choices = dict(Job.status.field.choices)
        domain = {
            choice: choices[choice] for choice in self.usage_chart_statuses
        }

        return stacked_bar(
            values=[
                {
                    "Status": datum["status"],
                    "Month": datetime(
                        datum["created__year"], datum["created__month"], 1
                    ).isoformat(),
                    "Jobs Count": datum["job_count"],
                }
                for datum in self.usage_statistics
            ],
            lookup="Jobs Count",
            title="Algorithm Usage",
            facet="Status",
            domain=domain,
        )

    @cached_property
    def public_test_case(self):
        try:
            return self.active_image.job_set.filter(
                status=Job.SUCCESS,
                public=True,
                algorithm_model=self.active_model,
            ).exists()
        except AttributeError:
            return False

    def form_field_label(self):
        title = f"{self.title}"
        title += f" (Active image: {' - '.join(filter(None, [truncatechars(self.active_image_comment, 25), str(self.active_image_pk)]))})"
        if self.active_model_pk:
            title += f" (Active model: {' - '.join(filter(None, [truncatechars(self.active_model_comment, 25), str(self.active_model_pk)]))})"
        else:
            title += " (Active model: None)"
        return title


class AlgorithmAlgorithmInterface(models.Model):
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE)
    interface = models.ForeignKey(AlgorithmInterface, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["algorithm", "interface"],
                name="unique_algorithm_interface_combination",
            ),
        ]

    def __str__(self):
        return str(self.interface)


class AlgorithmUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Algorithm, on_delete=models.CASCADE)


class AlgorithmGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"view_algorithm", "execute_algorithm", "change_algorithm"}
    )

    content_object = models.ForeignKey(Algorithm, on_delete=models.CASCADE)


@receiver(post_delete, sender=Algorithm)
def delete_algorithm_groups_hook(*_, instance: Algorithm, using, **__):
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
        instance.users_group.delete(using=using)
    except ObjectDoesNotExist:
        pass


class AlgorithmUserCreditManager(models.QuerySet):
    def active_credits(self):
        today = now().date()
        return self.filter(
            valid_from__lte=today,
            valid_until__gte=today,
        )


class AlgorithmUserCredit(UUIDModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=False,
        on_delete=models.CASCADE,
        help_text="The user who these credits are applied to",
    )
    algorithm = models.ForeignKey(
        Algorithm,
        blank=False,
        on_delete=models.CASCADE,
        help_text="The algorithm that these credits can be used with",
    )
    credits = models.PositiveIntegerField(
        blank=False,
        help_text="The credits that a user can spend during the validity period on running this algorithm",
    )
    valid_from = models.DateField(
        blank=False,
        help_text="Inclusive date from which these credits are valid",
    )
    valid_until = models.DateField(
        blank=False,
        help_text="Inclusive date until these credits are valid",
    )
    comment = models.TextField(
        blank=False,
        help_text="Who agreed to these credits have been assigned and where the costs are coming from",
    )

    objects = AlgorithmUserCreditManager.as_manager()

    class Meta:
        unique_together = ("user", "algorithm")

    def __str__(self):
        return f"Credits for {self.user} for {self.algorithm}"

    @property
    def is_active(self):
        today = now().date()
        return self.valid_from <= today and self.valid_until >= today

    def clean(self):
        super().clean()

        try:
            if self.user.username == settings.ANONYMOUS_USER_NAME:
                raise ValidationError(
                    {"user": "The anonymous user cannot be assigned credits"}
                )
        except ObjectDoesNotExist:
            raise ValidationError("The user must be set")

        try:
            if self.valid_until < self.valid_from:
                raise ValidationError(
                    {
                        "valid_from": "This must be less than or equal to Valid Until",
                        "valid_until": "This must be greater than or equal to Valid From",
                    }
                )
        except TypeError:
            raise ValidationError("The validity period must be set")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AlgorithmImage(UUIDModel, ComponentImage):
    algorithm = models.ForeignKey(
        Algorithm,
        on_delete=models.PROTECT,
        related_name="algorithm_container_images",
    )

    class Meta(UUIDModel.Meta, ComponentImage.Meta):
        ordering = ("created",)
        permissions = [
            ("download_algorithmimage", "Can download algorithm image")
        ]

    def get_absolute_url(self):
        return reverse(
            "algorithms:image-detail",
            kwargs={"slug": self.algorithm.slug, "pk": self.pk},
        )

    @property
    def import_status_url(self) -> str:
        return reverse(
            "algorithms:image-import-status-detail",
            kwargs={"slug": self.algorithm.slug, "pk": self.pk},
        )

    @property
    def build_status_url(self) -> str:
        return reverse(
            "algorithms:image-build-status-detail",
            kwargs={"slug": self.algorithm.slug, "pk": self.pk},
        )

    @property
    def api_url(self) -> str:
        return reverse("api:algorithms-image-detail", kwargs={"pk": self.pk})

    def get_remaining_complimentary_jobs(self, *, user):
        if self.algorithm.is_editor(user=user):
            return max(
                settings.ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS
                - Job.objects.filter(
                    algorithm_image=self, is_complimentary=True
                ).count(),
                0,
            )
        else:
            return 0

    def get_remaining_non_complimentary_jobs(self, *, user):
        try:
            credits_left = self.get_remaining_specific_credits(
                user=user, algorithm=self.algorithm
            )
        except ObjectDoesNotExist:
            credits_left = self.get_remaining_general_credits(user=user)

        return max(credits_left, 0) // max(self.algorithm.credits_per_job, 1)

    @staticmethod
    def get_remaining_specific_credits(*, user, algorithm):
        user_credit = AlgorithmUserCredit.objects.active_credits().get(
            user=user,
            algorithm=algorithm,
        )

        spent_credits = Job.objects.filter(
            creator=user_credit.user,
            is_complimentary=False,
            created__date__gte=user_credit.valid_from,
            created__date__lte=user_credit.valid_until,
            algorithm_image__algorithm=user_credit.algorithm,
        ).aggregate(
            total=Sum("credits_consumed", default=0),
        )

        return user_credit.credits - spent_credits["total"]

    @staticmethod
    def get_remaining_general_credits(*, user):
        if user.username == settings.ANONYMOUS_USER_NAME:
            return 0

        user_credits = settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER

        user_algorithms_with_active_credits = (
            AlgorithmUserCredit.objects.active_credits()
            .filter(
                user=user,
            )
            .values_list("algorithm__pk", flat=True)
        )

        spent_credits = (
            Job.objects.filter(
                creator=user,
                is_complimentary=False,
                created__gte=timezone.now() - relativedelta(months=1),
            )
            .exclude(
                algorithm_image__algorithm__pk__in=user_algorithms_with_active_credits
            )
            .aggregate(
                total=Sum("credits_consumed", default=0),
            )
        )

        return user_credits - spent_credits["total"]

    def get_remaining_jobs(self, *, user):
        return self.get_remaining_non_complimentary_jobs(
            user=user
        ) + self.get_remaining_complimentary_jobs(user=user)

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        # Editors and users can view this algorithm image
        assign_perm("view_algorithmimage", self.algorithm.editors_group, self)
        # Editors can change this algorithm image
        assign_perm(
            "change_algorithmimage", self.algorithm.editors_group, self
        )

    def get_peer_images(self):
        return AlgorithmImage.objects.filter(algorithm=self.algorithm)


class AlgorithmImageUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(
        AlgorithmImage, on_delete=models.CASCADE
    )


class AlgorithmImageGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {
            "change_algorithmimage",
            "download_algorithmimage",
            "view_algorithmimage",
        }
    )

    content_object = models.ForeignKey(
        AlgorithmImage, on_delete=models.CASCADE
    )


class JobManager(ComponentJobManager):
    def create(
        self,
        *,
        input_civ_set=None,
        extra_viewer_groups=None,
        extra_logs_viewer_groups=None,
        **kwargs,
    ):
        obj = super().create(**kwargs)

        if input_civ_set is not None:
            obj.inputs.set(input_civ_set)

        if extra_viewer_groups is not None:
            obj.viewer_groups.add(*extra_viewer_groups)

        if extra_logs_viewer_groups is not None:
            for group in extra_logs_viewer_groups:
                assign_perm("algorithms.view_logs", group, obj)

        return obj

    def get_jobs_with_same_inputs(
        self, *, inputs, algorithm_image, algorithm_model
    ):
        existing_civs = self.retrieve_existing_civs(civ_data_objects=inputs)
        unique_kwargs = {
            "algorithm_image": algorithm_image,
        }
        input_interface_count = len(inputs)

        if algorithm_model:
            unique_kwargs["algorithm_model"] = algorithm_model
        else:
            unique_kwargs["algorithm_model__isnull"] = True

        # annotate the number of inputs and the number of inputs that match
        # the existing civs and filter on both counts so as to not include jobs
        # with partially overlapping inputs
        # or jobs with more inputs than the existing civs
        annotated_qs = annotate_input_output_counts(
            queryset=Job.objects.filter(**unique_kwargs), inputs=existing_civs
        )
        existing_jobs = annotated_qs.filter(
            input_count=input_interface_count,
            relevant_input_count=input_interface_count,
        )

        return existing_jobs


def algorithm_models_path(instance, filename):
    return (
        f"models/"
        f"{instance._meta.app_label.lower()}/"
        f"{instance._meta.model_name.lower()}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )


class AlgorithmModel(Tarball):
    algorithm = models.ForeignKey(
        Algorithm, on_delete=models.PROTECT, related_name="algorithm_models"
    )
    model = models.FileField(
        blank=True,
        upload_to=algorithm_models_path,
        validators=[ExtensionValidator(allowed_extensions=(".tar.gz",))],
        help_text=(
            ".tar.gz file of the algorithm model that will be extracted to /opt/ml/model/ during inference"
        ),
        storage=protected_s3_storage,
    )

    class Meta(Tarball.Meta):
        permissions = [
            ("download_algorithmmodel", "Can download algorithm model")
        ]

    @property
    def linked_file(self):
        return self.model

    def assign_permissions(self):
        # Editors can view this algorithm model
        assign_perm("view_algorithmmodel", self.algorithm.editors_group, self)
        # Editors can change this algorithm model
        assign_perm(
            "change_algorithmmodel", self.algorithm.editors_group, self
        )

    def get_peer_tarballs(self):
        return AlgorithmModel.objects.filter(algorithm=self.algorithm).exclude(
            pk=self.pk
        )

    def get_absolute_url(self):
        return reverse(
            "algorithms:model-detail",
            kwargs={"slug": self.algorithm.slug, "pk": self.pk},
        )

    @property
    def import_status_url(self) -> str:
        return reverse(
            "algorithms:model-import-status-detail",
            kwargs={"slug": self.algorithm.slug, "pk": self.pk},
        )


class AlgorithmModelUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(
        AlgorithmModel, on_delete=models.CASCADE
    )


class AlgorithmModelGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {
            "change_algorithmmodel",
            "view_algorithmmodel",
            "download_algorithmmodel",
        }
    )

    content_object = models.ForeignKey(
        AlgorithmModel, on_delete=models.CASCADE
    )


class Job(CIVForObjectMixin, ComponentJob):
    objects = JobManager.as_manager()

    algorithm_image = models.ForeignKey(
        AlgorithmImage, on_delete=models.PROTECT
    )
    algorithm_model = models.ForeignKey(
        AlgorithmModel, on_delete=models.PROTECT, null=True, blank=True
    )
    algorithm_interface = models.ForeignKey(
        AlgorithmInterface, on_delete=models.PROTECT, null=True, blank=True
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    public = models.BooleanField(
        default=False,
        help_text=(
            "If True, allow anyone to download this result along "
            "with the input image. Otherwise, only the job creator "
            "will have permission to download and view "
            "this result."
        ),
    )
    comment = models.TextField(blank=True, default="")
    credits_consumed = models.PositiveSmallIntegerField(
        editable=False,
        help_text="The total credits consumed for this job",
    )
    is_complimentary = models.BooleanField(
        default=False,
        editable=False,
        help_text="If True, this job does not consume credits.",
    )

    viewer_groups = models.ManyToManyField(
        Group,
        help_text="Which groups should have permission to view this job?",
    )
    viewers = models.OneToOneField(
        Group,
        null=True,
        on_delete=models.SET_NULL,
        related_name="viewers_of_algorithm_job",
    )

    class Meta(UUIDModel.Meta, ComponentJob.Meta):
        ordering = ("created",)
        permissions = [("view_logs", "Can view the jobs logs")]

    def __str__(self):
        return f"Job {self.pk}"

    @property
    def container(self):
        return self.algorithm_image

    @property
    def output_interfaces(self):
        return self.algorithm_interface.outputs.all()

    @cached_property
    def inputs_complete(self):
        # check if all inputs are present and if they all have a value
        # interfaces that do not require a value will be considered complete regardless
        return {
            civ.interface
            for civ in self.inputs.all()
            if civ.has_value or not civ.interface.value_required
        } == {*self.algorithm_interface.inputs.all()}

    def get_absolute_url(self):
        return reverse(
            "algorithms:job-detail",
            kwargs={
                "slug": self.algorithm_image.algorithm.slug,
                "pk": self.pk,
            },
        )

    @property
    def status_url(self) -> str:
        return reverse(
            "algorithms:job-status-detail",
            kwargs={
                "slug": self.algorithm_image.algorithm.slug,
                "pk": self.pk,
            },
        )

    @property
    def api_url(self) -> str:
        return reverse("api:algorithms-job-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.init_viewers_group()
            self.init_is_complimentary()
            self.init_credits_consumed()

        super().save(*args, **kwargs)

        if adding:
            self.init_permissions()
            self.init_followers()

        if adding or self.has_changed("public"):
            self.update_viewer_groups_for_public()

        if self.has_changed("status") and self.status == self.SUCCESS:
            on_commit(
                update_algorithm_average_duration.signature(
                    kwargs={"algorithm_pk": self.algorithm_image.algorithm.pk}
                ).apply_async
            )

    def init_is_complimentary(self):
        self.is_complimentary = bool(
            self.creator
            and self.algorithm_image.get_remaining_complimentary_jobs(
                user=self.creator
            )
            > 0
        )

    def init_credits_consumed(self):
        overall_min_credits_per_job = (
            settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER
            / settings.ALGORITHMS_MAX_GENERAL_JOBS_PER_MONTH_PER_USER
        )

        executor = self.get_executor(
            backend=settings.COMPONENTS_DEFAULT_BACKEND
        )

        maximum_cents_per_job = (
            (self.time_limit / 3600)
            * executor.usd_cents_per_hour
            * settings.COMPONENTS_USD_TO_EUR
        )

        credits_per_job = max(
            int(
                round(
                    maximum_cents_per_job
                    * settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER
                    / settings.ALGORITHMS_GENERAL_CENTS_PER_MONTH_PER_USER,
                    -1,
                )
            ),
            overall_min_credits_per_job,
        )

        self.credits_consumed = max(
            self.algorithm_image.algorithm.minimum_credits_per_job,
            credits_per_job,
        )

    def init_viewers_group(self):
        if self.creator:
            # Only create the viewer group if there is a creator
            # as only they should have change_job
            self.viewers = Group.objects.create(
                name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_viewers"
            )

    def init_permissions(self):
        if self.creator:
            # If there is a creator they can view and change this job
            self.viewer_groups.set([self.viewers])
            self.viewers.user_set.add(self.creator)
            assign_perm("change_job", self.creator, self)

    def init_followers(self):
        if self.creator:
            if not is_following(
                user=self.creator,
                obj=self.algorithm_image.algorithm,
                flag="job-active",
            ) and not is_following(
                user=self.creator,
                obj=self.algorithm_image.algorithm,
                flag="job-inactive",
            ):
                follow(
                    user=self.creator,
                    obj=self.algorithm_image.algorithm,
                    actor_only=False,
                    send_action=False,
                    flag="job-active",
                )

    def update_viewer_groups_for_public(self):
        g = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        if self.public:
            self.viewer_groups.add(g)
        else:
            self.viewer_groups.remove(g)

    def add_viewer(self, user):
        return user.groups.add(self.viewers)

    def remove_viewer(self, user):
        return user.groups.remove(self.viewers)

    def add_civ(self, *, civ):
        super().add_civ(civ=civ)
        return self.inputs.add(civ)

    def remove_civ(self, *, civ):
        super().remove_civ(civ=civ)
        return self.inputs.remove(civ)

    def get_civ_for_interface(self, interface):
        return self.inputs.get(interface=interface)

    def validate_civ_data_objects_and_execute_linked_task(
        self, *, civ_data_objects, user, linked_task=None
    ):
        from grandchallenge.algorithms.tasks import (
            execute_algorithm_job_for_inputs,
        )

        linked_task = execute_algorithm_job_for_inputs.signature(
            kwargs={"job_pk": str(self.pk)}, immutable=True
        )

        return super().validate_civ_data_objects_and_execute_linked_task(
            civ_data_objects=civ_data_objects,
            user=user,
            linked_task=linked_task,
        )

    @property
    def is_editable(self):
        # staying with display set and archive item terminology here
        # since this property is checked in create_civ()
        if self.status == self.VALIDATING_INPUTS:
            return True
        else:
            return False

    @property
    def base_object(self):
        return self.algorithm_image.algorithm

    @property
    def executor_kwargs(self):
        executor_kwargs = super().executor_kwargs
        if self.algorithm_model:
            executor_kwargs["algorithm_model"] = self.algorithm_model.model
        return executor_kwargs

    @cached_property
    def slug_to_output(self):
        outputs = {}

        for output in self.outputs.all():
            outputs[output.interface.slug] = output

        return outputs

    def get_or_create_display_set(self, *, reader_study):
        """Get or create a display set from this job for a reader study"""
        if self.status != self.SUCCESS:
            raise RuntimeError(
                "Display sets can only be created from successful jobs"
            )

        values = {*self.inputs.all(), *self.outputs.all()}

        try:
            display_set = (
                reader_study.display_sets.filter(values__in=values)
                .annotate(
                    values_match_count=Count(
                        "values",
                        filter=Q(values__in=values),
                    )
                )
                .filter(values_match_count=len(values))
                .get()
            )
        except ObjectDoesNotExist:
            display_set = DisplaySet.objects.create(reader_study=reader_study)
            display_set.values.set(values)

        return display_set

    def create_utilization(self):
        JobUtilization.objects.create(job=self)

    @property
    def utilization(self):
        return self.job_utilization


class JobUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"change_job"})

    content_object = models.ForeignKey(Job, on_delete=models.CASCADE)


class JobGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"view_job", "view_logs"})

    content_object = models.ForeignKey(Job, on_delete=models.CASCADE)


@receiver(post_delete, sender=Job)
def delete_job_groups_hook(*_, instance: Job, using, **__):
    """
    Deletes the related group.

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
    if instance.viewers:
        try:
            instance.viewers.delete(using=using)
        except ObjectDoesNotExist:
            pass


class AlgorithmPermissionRequest(RequestBase):
    """
    When a user wants to view an algorithm, editors have the option of
    reviewing each user before accepting or rejecting them. This class records
    the needed info for that.
    """

    algorithm = models.ForeignKey(
        Algorithm,
        help_text="To which algorithm has the user requested access?",
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
        return self.algorithm

    @property
    def object_name(self):
        return self.base_object.title

    @property
    def add_method(self):
        return self.base_object.add_user

    @property
    def remove_method(self):
        return self.base_object.remove_user

    @property
    def permission_list_url(self):
        return reverse(
            "algorithms:permission-request-list",
            kwargs={"slug": self.base_object.slug},
        )

    def __str__(self):
        return f"{self.object_name} registration request by user {self.user.username}"

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            process_access_request(request_object=self)

    class Meta(RequestBase.Meta):
        unique_together = (("algorithm", "user"),)


class OptionalHangingProtocolAlgorithm(models.Model):
    # Through table for optional hanging protocols
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    algorithm = models.ForeignKey(Algorithm, on_delete=models.CASCADE)
    hanging_protocol = models.ForeignKey(
        "hanging_protocols.HangingProtocol", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("algorithm", "hanging_protocol"),)
