import logging
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm, get_objects_for_group, remove_perm

from grandchallenge.algorithms.emails import send_failed_job_email
from grandchallenge.cases.models import RawImageFile, RawImageUploadSession
from grandchallenge.challenges.models import get_logo_path
from grandchallenge.container_exec.backends.docker import (
    Executor,
    cleanup,
    get_file,
)
from grandchallenge.container_exec.models import (
    ContainerExecJobModel,
    ContainerImageModel,
)
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.storage import public_s3_storage
from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Workstation

logger = logging.getLogger(__name__)


class Algorithm(UUIDModel, TitleSlugDescriptionModel):
    editors_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name=f"editors_of_algorithm",
    )
    users_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name=f"users_of_algorithm",
    )
    logo = models.ImageField(
        upload_to=get_logo_path, storage=public_s3_storage
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
    visible_to_public = models.BooleanField(
        default=False,
        help_text=(
            "Should this algorithm be visible to all users on the algorithm "
            "overview page? This does not grant all users permission to use "
            "this algorithm. Users will still need to be added to the "
            "algorithm users group in order to do that."
        ),
    )
    contact_information = models.TextField(
        blank=True,
        help_text=(
            "Who should users contact with any questions regarding "
            "this algorithm? This information is only displayed on the "
            "algorithm's detail page."
        ),
    )
    info_url = models.URLField(
        blank=True,
        help_text=(
            "A URL to a page containing more information about "
            "the algorithm."
        ),
    )
    additional_information = models.TextField(
        blank=True,
        help_text=(
            "Any additional information that might be relevant to "
            "users for this algorithm. This is only displayed on the "
            "algorithm's detail page."
        ),
    )
    additional_terms = models.TextField(
        blank=True,
        help_text=(
            "By using this algortihm, users agree to the site wide "
            "terms of service. If your algorithm has any additional "
            "terms of usage, define them here."
        ),
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        ordering = ("created",)

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
            self.assign_permissions()

        self.assign_workstation_permissions()

    def create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.users_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_users"
        )

    def assign_permissions(self):
        # Editors and users can view this algorithm
        assign_perm(f"view_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"view_{self._meta.model_name}", self.users_group, self)
        # Editors can change this algorithm
        assign_perm(
            f"change_{self._meta.model_name}", self.editors_group, self
        )

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

    @property
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

    @property
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

    def is_editor(self, user):
        return user.groups.filter(pk=self.editors_group.pk).exists()

    def add_editor(self, user):
        # using .pk is required here as it is called from a data migration
        return user.groups.add(self.editors_group.pk)

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


class AlgorithmImage(UUIDModel, ContainerImageModel):
    algorithm = models.ForeignKey(
        Algorithm,
        on_delete=models.CASCADE,
        related_name="algorithm_container_images",
    )

    class Meta(UUIDModel.Meta, ContainerImageModel.Meta):
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


class Result(UUIDModel):
    job = models.OneToOneField("Job", null=True, on_delete=models.CASCADE)
    images = models.ManyToManyField(
        to="cases.Image", related_name="algorithm_results"
    )
    output = JSONField(default=dict)

    def get_absolute_url(self):
        return reverse("algorithms:results-detail", kwargs={"pk": self.pk})

    @property
    def api_url(self):
        return reverse("api:algorithms-result-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        # Algorithm editors and job creators can view this result
        assign_perm(
            f"view_{self._meta.model_name}",
            self.job.algorithm_image.algorithm.editors_group,
            self,
        )
        assign_perm(f"view_{self._meta.model_name}", self.job.creator, self)


class AlgorithmExecutor(Executor):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, results_file=Path("/output/results.json"), **kwargs
        )
        self.output_images_dir = Path("/output/images/")

    def _get_result(self):
        """Read all of the images in /output/ & convert to an UploadSession."""
        try:
            with cleanup(
                self._client.containers.run(
                    image=self._io_image,
                    volumes={
                        self._output_volume: {"bind": "/output/", "mode": "ro"}
                    },
                    name=f"{self._job_label}-reader",
                    detach=True,
                    tty=True,
                    labels=self._labels,
                    **self._run_kwargs,
                )
            ) as reader:
                self._copy_output_files(
                    container=reader, base_dir=Path(self.output_images_dir)
                )
        except Exception as exc:
            raise RuntimeError(str(exc))

        return super()._get_result()

    def _copy_output_files(self, *, container, base_dir: Path):
        found_files = container.exec_run(f"find {base_dir} -type f")

        if found_files.exit_code != 0:
            logger.warning(f"Error listing {base_dir}")
            return

        output_files = [
            base_dir / Path(f)
            for f in found_files.output.decode().splitlines()
        ]

        if not output_files:
            logger.warning("Output directory is empty")
            return

        # TODO: This thing should not interact with the database
        result = Result.objects.create(job_id=self._job_id)

        # Create the upload session but do not save it until we have the
        # files
        upload_session = RawImageUploadSession(algorithm_result=result)

        images = []

        for file in output_files:
            new_uuid = uuid.uuid4()

            django_file = File(get_file(container=container, src=file))

            staged_file = StagedFile(
                user_pk_str="staging_conversion_user_pk",
                client_id=self._job_id,
                client_filename=file.name,
                file_id=new_uuid,
                timeout=timezone.now() + timedelta(hours=24),
                start_byte=0,
                end_byte=django_file.size - 1,
                total_size=django_file.size,
            )
            staged_file.file.save(f"{uuid.uuid4()}", django_file)
            staged_file.save()

            staged_ajax_file = StagedAjaxFile(new_uuid)

            images.append(
                RawImageFile(
                    upload_session=upload_session,
                    filename=staged_ajax_file.name,
                    staged_file_id=staged_ajax_file.uuid,
                )
            )

        upload_session.save()
        RawImageFile.objects.bulk_create(images)
        upload_session.process_images()


class Job(UUIDModel, ContainerExecJobModel):
    algorithm_image = models.ForeignKey(
        AlgorithmImage, on_delete=models.CASCADE
    )
    image = models.ForeignKey("cases.Image", on_delete=models.CASCADE)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )

    @property
    def container(self):
        return self.algorithm_image

    @property
    def input_files(self):
        return [c.file for c in self.image.files.all()]

    @property
    def executor_cls(self):
        return AlgorithmExecutor

    def create_result(self, *, result: dict):
        instance, _ = Result.objects.get_or_create(job_id=self.pk)
        instance.output = result
        instance.save()

    def get_absolute_url(self):
        return reverse("algorithms:jobs-detail", kwargs={"pk": self.pk})

    @property
    def api_url(self):
        return reverse("api:algorithms-job-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        # Editors and creators can view this job and the related image
        assign_perm(
            f"view_{self._meta.model_name}",
            self.algorithm_image.algorithm.editors_group,
            self,
        )
        assign_perm(
            f"view_{self.image._meta.model_name}",
            self.algorithm_image.algorithm.editors_group,
            self.image,
        )
        if self.creator:
            assign_perm(f"view_{self._meta.model_name}", self.creator, self)
            assign_perm(
                f"view_{self.image._meta.model_name}", self.creator, self.image
            )

    def update_status(self, *args, **kwargs):
        res = super().update_status(*args, **kwargs)

        if self.status == self.FAILURE:
            send_failed_job_email(self)

        return res


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
    def object_name(self):
        return self.algorithm.title

    def __str__(self):
        return f"{self.algorithm.title} registration request by user {self.user.username}"

    class Meta:
        unique_together = (("algorithm", "user"),)
