import logging
from datetime import timedelta

from actstream.actions import follow, is_following
from actstream.models import Follow
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Min, Q, Sum
from django.db.models.signals import post_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property
from django_deprecate_fields import deprecate_field
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm, get_objects_for_group, remove_perm
from jinja2 import sandbox
from jinja2.exceptions import TemplateError
from stdimage import JPEGField

from grandchallenge.anatomy.models import BodyStructure
from grandchallenge.components.models import (
    ComponentImage,
    ComponentInterface,
    ComponentJob,
)
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.storage import (
    get_logo_path,
    get_social_image_path,
    public_s3_storage,
)
from grandchallenge.core.templatetags.bleach import md2html
from grandchallenge.evaluation.utils import get
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.organizations.models import Organization
from grandchallenge.publications.models import Publication
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Workstation

logger = logging.getLogger(__name__)

DEFAULT_INPUT_INTERFACE_SLUG = "generic-medical-image"
DEFAULT_OUTPUT_INTERFACE_SLUG = "generic-overlay"

JINJA_ENGINE = sandbox.ImmutableSandboxedEnvironment()


class Algorithm(UUIDModel, TitleSlugDescriptionModel):
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
    logo = JPEGField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        variations=settings.STDIMAGE_LOGO_VARIATIONS,
    )
    social_image = JPEGField(
        upload_to=get_social_image_path,
        storage=public_s3_storage,
        blank=True,
        help_text="An image for this algorithm which is displayed when you post the link for this algorithm on social media. Should have a resolution of 640x320 px (1280x640 px for best display).",
        variations=settings.STDIMAGE_SOCIAL_VARIATIONS,
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
    public = models.BooleanField(
        default=False,
        help_text=(
            "Should this algorithm be visible to all users on the algorithm "
            "overview page? This does not grant all users permission to use "
            "this algorithm. Users will still need to be added to the "
            "algorithm users group in order to do that."
        ),
    )
    detail_page_markdown = models.TextField(blank=True)
    job_create_page_markdown = models.TextField(blank=True)
    additional_terms_markdown = models.TextField(
        blank=True,
        help_text=(
            "By using this algortihm, users agree to the site wide "
            "terms of service. If your algorithm has any additional "
            "terms of usage, define them here."
        ),
    )
    result_template = models.TextField(
        blank=True,
        default="<pre>{{ results|tojson(indent=2) }}</pre>",
        help_text=(
            "Define the jinja template to render the content of the "
            "results.json to html. For example, the following template will "
            "print out all the keys and values of the result.json. "
            "Use results to access the json root. "
            "{% for key, value in results.metrics.items() -%}"
            "{{ key }}  {{ value }}"
            "{% endfor %}"
        ),
    )
    inputs = models.ManyToManyField(
        to=ComponentInterface, related_name="algorithm_inputs"
    )
    outputs = models.ManyToManyField(
        to=ComponentInterface, related_name="algorithm_outputs"
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
    credits_per_job = models.PositiveIntegerField(
        default=0,
        help_text=(
            "The number of credits that are required for each execution of this algorithm."
        ),
    )
    average_duration = models.DurationField(
        null=True,
        default=None,
        editable=False,
        help_text="The average duration of successful jobs.",
    )
    use_flexible_inputs = models.BooleanField(default=True)
    repo_name = models.CharField(blank=True, max_length=512)
    image_requires_gpu = models.BooleanField(default=True)
    image_requires_memory_gb = models.PositiveIntegerField(default=15)
    recurse_submodules = models.BooleanField(
        default=False,
        help_text="Do a recursive git pull when a GitHub repo is linked to this algorithm.",
    )
    highlight = models.BooleanField(
        default=False,
        help_text="Should this algorithm be advertised on the home page?",
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        ordering = ("created",)
        permissions = [("execute_algorithm", "Can execute algorithm")]
        constraints = [
            models.UniqueConstraint(
                fields=["repo_name"],
                name="unique_repo_name",
                condition=~Q(repo_name=""),
            ),
        ]

    def __str__(self):
        return f"{self.title}"

    def get_absolute_url(self):
        return reverse("algorithms:detail", kwargs={"slug": self.slug})

    @property
    def api_url(self):
        return reverse("api:algorithm-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()
            self.workstation_id = (
                self.workstation_id or self.default_workstation.pk
            )

        super().save(*args, **kwargs)

        if adding:
            self.set_default_interfaces()

        self.assign_permissions()
        self.assign_workstation_permissions()

    def delete(self, *args, **kwargs):
        ct = ContentType.objects.filter(
            app_label=self._meta.app_label, model=self._meta.model_name
        ).get()
        Follow.objects.filter(object_id=self.pk, content_type=ct).delete()
        super().delete(*args, **kwargs)

    def create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.users_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_users"
        )

    def set_default_interfaces(self):
        if not self.inputs.exists():
            self.inputs.set(
                [
                    ComponentInterface.objects.get(
                        slug=DEFAULT_INPUT_INTERFACE_SLUG
                    )
                ]
            )
        if not self.outputs.exists():
            self.outputs.set(
                [
                    ComponentInterface.objects.get(slug="results-json-file"),
                    ComponentInterface.objects.get(
                        slug=DEFAULT_OUTPUT_INTERFACE_SLUG
                    ),
                ]
            )

    def assign_permissions(self):
        # Editors and users can view this algorithm
        assign_perm(f"view_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"view_{self._meta.model_name}", self.users_group, self)
        # Editors and users can execute this algorithm
        assign_perm(
            f"execute_{self._meta.model_name}", self.editors_group, self
        )
        assign_perm(f"execute_{self._meta.model_name}", self.users_group, self)
        # Editors can change this algorithm
        assign_perm(
            f"change_{self._meta.model_name}", self.editors_group, self
        )

        reg_and_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        if self.public:
            assign_perm(f"view_{self._meta.model_name}", reg_and_anon, self)
        else:
            remove_perm(f"view_{self._meta.model_name}", reg_and_anon, self)

    def assign_workstation_permissions(self):
        """Allow the editors and users group to view the workstation."""
        perm = f"view_{Workstation._meta.model_name}"

        for group in [self.users_group, self.editors_group]:
            workstations = get_objects_for_group(
                group=group, perms=perm, klass=Workstation
            )

            if (
                self.workstation not in workstations
            ) or workstations.count() > 1:
                remove_perm(perm=perm, user_or_group=group, obj=workstations)
                assign_perm(
                    perm=perm, user_or_group=group, obj=self.workstation
                )

    @cached_property
    def latest_ready_image(self):
        """
        Returns
        -------
            The most recent container image for this algorithm
        """
        return (
            self.algorithm_container_images.filter(ready=True)
            .order_by("-created")
            .first()
        )

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

    def update_average_duration(self):
        """Store the duration of successful jobs for this algorithm"""
        self.average_duration = Job.objects.filter(
            algorithm_image__algorithm=self, status=Job.SUCCESS
        ).average_duration()
        self.save(update_fields=("average_duration",))

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


class AlgorithmImage(UUIDModel, ComponentImage):
    algorithm = models.ForeignKey(
        Algorithm,
        on_delete=models.PROTECT,
        related_name="algorithm_container_images",
    )
    queue_override = deprecate_field(
        models.CharField(max_length=128, blank=True)
    )

    class Meta(UUIDModel.Meta, ComponentImage.Meta):
        ordering = ("created", "creator")

    def get_absolute_url(self):
        return reverse(
            "algorithms:image-detail",
            kwargs={"slug": self.algorithm.slug, "pk": self.pk},
        )

    @property
    def api_url(self):
        return reverse("api:algorithms-image-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        # Editors and users can view this algorithm image
        assign_perm(
            f"view_{self._meta.model_name}", self.algorithm.editors_group, self
        )
        # Editors can change this algorithm image
        assign_perm(
            f"change_{self._meta.model_name}",
            self.algorithm.editors_group,
            self,
        )


class JobQuerySet(models.QuerySet):
    def spent_credits(self, user):
        now = timezone.now()
        period = timedelta(days=30)
        user_groups = Group.objects.filter(user=user)

        return (
            self.filter(creator=user, created__range=[now - period, now])
            .distinct()
            .order_by("created")
            .select_related("algorithm_image__algorithm")
            .exclude(algorithm_image__algorithm__editors_group__in=user_groups)
            .aggregate(
                total=Sum("algorithm_image__algorithm__credits_per_job"),
                oldest=Min("created"),
            )
        )


class Job(UUIDModel, ComponentJob):
    algorithm_image = models.ForeignKey(
        AlgorithmImage, on_delete=models.PROTECT
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    public = models.BooleanField(
        default=False,
        help_text=(
            "If True, allow anyone to download this result along "
            "with the input image. Otherwise, only the job creator and "
            "algorithm editor(s) will have permission to download and view "
            "this result."
        ),
    )
    comment = models.TextField(blank=True, default="")

    viewer_groups = models.ManyToManyField(
        Group,
        help_text="Which groups should have permission to view this job?",
    )
    viewers = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        related_name="viewers_of_algorithm_job",
    )
    credits_set = JobQuerySet.as_manager()

    class Meta(UUIDModel.Meta, ComponentJob.Meta):
        ordering = ("created",)
        permissions = [("view_logs", "Can view the jobs logs")]

    def __str__(self):
        return f"Job {self.pk}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._public_orig = self.public
        self._status_orig = self.status

    @property
    def container(self):
        return self.algorithm_image

    @property
    def output_interfaces(self):
        return self.algorithm_image.algorithm.outputs

    @cached_property
    def rendered_result_text(self):
        try:
            results = get(
                [
                    o.value
                    for o in self.outputs.all()
                    if o.interface.slug == "results-json-file"
                ]
            )
        except ObjectDoesNotExist:
            return ""

        try:
            template_output = JINJA_ENGINE.from_string(
                self.algorithm_image.algorithm.result_template
            ).render(results=results)
        except (TemplateError, TypeError, ValueError):
            return "Jinja template is invalid"

        return md2html(template_output)

    def get_absolute_url(self):
        return reverse(
            "algorithms:job-detail",
            kwargs={
                "slug": self.algorithm_image.algorithm.slug,
                "pk": self.pk,
            },
        )

    @property
    def api_url(self):
        return reverse("api:algorithms-job-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.init_viewers_group()

        super().save(*args, **kwargs)

        if adding:
            self.init_permissions()
            followers = list(
                self.algorithm_image.algorithm.editors_group.user_set.all()
            )
            if self.creator:
                followers.append(self.creator)
            for follower in set(followers):
                if not is_following(
                    user=follower,
                    obj=self.algorithm_image.algorithm,
                    flag="job-active",
                ) and not is_following(
                    user=follower,
                    obj=self.algorithm_image.algorithm,
                    flag="job-inactive",
                ):
                    follow(
                        user=follower,
                        obj=self.algorithm_image.algorithm,
                        actor_only=False,
                        send_action=False,
                        flag="job-active",
                    )

        if adding or self._public_orig != self.public:
            self.update_viewer_groups_for_public()
            self._public_orig = self.public

        if self._status_orig != self.status and self.status == self.SUCCESS:
            self.algorithm_image.algorithm.update_average_duration()

    def init_viewers_group(self):
        self.viewers = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_viewers"
        )

    def init_permissions(self):
        # By default, only the viewers can view this job
        self.viewer_groups.set([self.viewers])

        # If there is a creator they can view and change this job
        if self.creator:
            self.viewers.user_set.add(self.creator)
            assign_perm("change_job", self.creator, self)

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

    def run_job(self, upload_pks=None):
        # Local import to avoid circular dependency
        from grandchallenge.algorithms.tasks import (
            run_algorithm_job_for_inputs,
        )

        run_job = run_algorithm_job_for_inputs.signature(
            kwargs={"job_pk": self.pk, "upload_pks": upload_pks},
            immutable=True,
        )
        on_commit(run_job.apply_async)


@receiver(post_delete, sender=Job)
def delete_job_groups_hook(*_, instance: Job, using, **__):
    """
    Deletes the related group.

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
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
            follow(
                user=self.user, obj=self, actor_only=False, send_action=False,
            )
            Notification.send(
                type=NotificationType.NotificationTypeChoices.ACCESS_REQUEST,
                message="requested access to",
                actor=self.user,
                target=self.base_object,
            )

    def delete(self):
        ct = ContentType.objects.filter(
            app_label=self._meta.app_label, model=self._meta.model_name
        ).get()
        Follow.objects.filter(object_id=self.pk, content_type=ct).delete()
        super().delete()

    class Meta(RequestBase.Meta):
        unique_together = (("algorithm", "user"),)
