from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from guardian.shortcuts import assign_perm

from grandchallenge.cases.models import Image
from grandchallenge.core.models import UUIDModel


class AbstractAnnotationModel(UUIDModel):
    """
    Abstract model for an annotation linking to a grader.
    Overrides the created attribute from UUIDModel to allow the value to be set to a specific value on save.
    See: https://docs.djangoproject.com/en/2.1/ref/models/fields/#django.db.models.DateField.auto_now_add
    """

    grader = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    # Override inherited 'created' attribute to allow setting of value
    created = models.DateTimeField(default=timezone.now)

    class Meta(UUIDModel.Meta):
        abstract = True
        get_latest_by = "created"
        ordering = ["-created"]

    def save(self, *args, **kwargs):
        """Override save method to enable setting of permissions for retina users."""
        created = self._state.adding

        super().save(*args, **kwargs)

        if not created:
            return

        if (
            self.grader.groups.filter(
                name=settings.RETINA_GRADERS_GROUP_NAME
            ).exists()
            or self.grader.groups.filter(
                name=settings.RETINA_ADMINS_GROUP_NAME
            ).exists()
        ):
            model_name = self._meta.model_name
            admins_group = Group.objects.get(
                name=settings.RETINA_ADMINS_GROUP_NAME
            )
            for permission_type in self._meta.default_permissions:
                permission_name = f"{permission_type}_{model_name}"
                assign_perm(permission_name, self.grader, self)
                assign_perm(permission_name, admins_group, self)


class AbstractSingleAnnotationModel(UUIDModel):
    def save(self, *args, **kwargs):
        """Override save method to enable setting of permissions for retina users."""
        created = self._state.adding

        super().save(*args, **kwargs)

        if not created:
            return

        if (
            self.annotation_set.grader.groups.filter(
                name=settings.RETINA_GRADERS_GROUP_NAME
            ).exists()
            or self.annotation_set.grader.groups.filter(
                name=settings.RETINA_ADMINS_GROUP_NAME
            ).exists()
        ):
            model_name = self._meta.model_name
            admins_group = Group.objects.get(
                name=settings.RETINA_ADMINS_GROUP_NAME
            )
            for permission_type in self._meta.default_permissions:
                permission_name = f"{permission_type}_{model_name}"
                assign_perm(permission_name, self.annotation_set.grader, self)
                assign_perm(permission_name, admins_group, self)

    class Meta(UUIDModel.Meta):
        abstract = True
        get_latest_by = "created"
        ordering = ["-created"]


class AbstractImageAnnotationModel(AbstractAnnotationModel):
    """Abstract model for annotation linking to a single image."""

    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    def __str__(self):
        return "<{} by {} on {} for {}>".format(
            self._meta.object_name,
            self.grader.username,
            self.created.strftime("%Y-%m-%d at %H:%M:%S"),
            self.image,
        )

    class Meta(AbstractAnnotationModel.Meta):
        abstract = True


class AbstractNamedImageAnnotationModel(AbstractImageAnnotationModel):
    """
    Abstract model for a unique named image annotation.
    Expands upon AbstractImageAnnotationModel and adds a name for the type of annotation
    """

    name = models.CharField(max_length=255)

    class Meta(AbstractImageAnnotationModel.Meta):
        # Create unique together constraint to disallow duplicates
        unique_together = ("image", "grader", "created", "name")
        abstract = True


class MeasurementAnnotation(AbstractImageAnnotationModel):
    """Model for a measurement (=2 coordinates) on a 2D image."""

    # Fields for start and end coordinates (x,y) of the voxel for the measurement
    start_voxel = ArrayField(models.FloatField(), size=2)
    end_voxel = ArrayField(models.FloatField(), size=2)

    class Meta(AbstractImageAnnotationModel.Meta):
        # Create unique together constraint to disallow duplicates
        unique_together = (
            "image",
            "grader",
            "created",
            "start_voxel",
            "end_voxel",
        )


class BooleanClassificationAnnotation(AbstractNamedImageAnnotationModel):
    """General model for boolean image-level classification."""

    value = models.BooleanField()


class IntegerClassificationAnnotation(AbstractNamedImageAnnotationModel):
    """General model for integer image-level classification."""

    value = models.IntegerField()


class CoordinateListAnnotation(AbstractNamedImageAnnotationModel):
    """General model for list of coordinates annotation."""

    # General form: [[x1,y1],[x2,y2],...]
    value = ArrayField(ArrayField(models.FloatField(), size=2))


class PolygonAnnotationSet(AbstractNamedImageAnnotationModel):
    """
    General model containing a set of specific polygon annotations.

    Looks empty because it only contains the fields from
    `AbstractNamedImageAnnotationModel`.
    """


def x_axis_orientation_default():
    return [1, 0, 0]


def y_axis_orientation_default():
    return [0, 1, 0]


class SinglePolygonAnnotation(AbstractSingleAnnotationModel):
    """
    General model for a single 2D in-plane polygon annotation (list of coordinates).
    Belongs as many-to-one to a PolygonAnnotationSet.
    Plane orientation is defined by x_axis_orientation and y_axis_orientation in a
    right-handed coordinate system. The location of the plane is defined by the value
    of z.
    """

    annotation_set = models.ForeignKey(
        PolygonAnnotationSet, on_delete=models.CASCADE
    )

    # General form: [[x1,y1],[x2,y2],...]
    value = ArrayField(ArrayField(models.FloatField(), size=2))

    x_axis_orientation = ArrayField(
        models.FloatField(), size=3, default=x_axis_orientation_default
    )
    y_axis_orientation = ArrayField(
        models.FloatField(), size=3, default=y_axis_orientation_default
    )
    z = models.FloatField(null=True, blank=True)


class LandmarkAnnotationSet(AbstractAnnotationModel):
    """
    General model containing a set of specific landmark annotations.
    Contains only the fields from AbstractAnnotationModel
    """

    class Meta(AbstractAnnotationModel.Meta):
        unique_together = ("grader", "created")


class SingleLandmarkAnnotation(AbstractSingleAnnotationModel):
    """
    Model containing a set of landmarks (coordinates on an image) that represent the same locations as all the other
    LandmarkAnnotations in the LandmarkAnnotationSet it belongs to. This is used for image registration.
    """

    annotation_set = models.ForeignKey(
        LandmarkAnnotationSet, on_delete=models.CASCADE
    )
    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    # General form: [[x1,y1],[x2,y2],...]
    landmarks = ArrayField(ArrayField(models.FloatField(), size=2))

    class Meta(AbstractSingleAnnotationModel.Meta):
        # Allow only one LandmarkAnnotation for a specific image in a set
        unique_together = ("image", "annotation_set")


class ETDRSGridAnnotation(AbstractImageAnnotationModel):
    """
    Retina specific annotation
    Model for the placement of an ETDRS grid on an retina image
    """

    # Fields for location of fovea and optic disk on the images: (x,y) coordinates
    fovea = ArrayField(models.FloatField(), size=2)
    optic_disk = ArrayField(
        models.FloatField(), size=2, default=list, blank=True
    )

    class Meta(AbstractImageAnnotationModel.Meta):
        unique_together = ("image", "grader", "created")


class ImageQualityAnnotation(AbstractImageAnnotationModel):
    """Model to annotate quality of an image."""

    QUALITY_UNGRADABLE = "U"
    QUALITY_FAIR = "F"
    QUALITY_GOOD = "G"
    QUALITY_CHOICES = (
        (QUALITY_UNGRADABLE, "Cannot grade"),
        (QUALITY_FAIR, "Fair"),
        (QUALITY_GOOD, "Good"),
    )

    QUALITY_REASON_BAD_PHOTO = "BP"
    QUALITY_REASON_CATARACT = "CA"
    QUALITY_REASON_POOR_MYDRIASIS = "PM"
    QUALITY_REASON_CHOICES = (
        (QUALITY_REASON_BAD_PHOTO, "Bad photo"),
        (QUALITY_REASON_CATARACT, "Cataract"),
        (QUALITY_REASON_POOR_MYDRIASIS, "Poor mydriasis"),
    )

    quality = models.CharField(
        max_length=1,
        choices=QUALITY_CHOICES,
        help_text="How do you rate the quality of the image?",
    )
    quality_reason = models.CharField(
        max_length=2,
        choices=QUALITY_REASON_CHOICES,
        null=True,
        blank=True,
        help_text="If the quality is not good, why not?",
    )


class ImagePathologyAnnotation(AbstractImageAnnotationModel):
    """Model to annotate if an pathology is present in an image."""

    PATHOLOGY_CANNOT_GRADE = "C"
    PATHOLOGY_ABSENT = "A"
    PATHOLOGY_QUESTIONABLE = "Q"
    PATHOLOGY_PRESENT = "P"
    PATHOLOGY_CHOICES = (
        (PATHOLOGY_CANNOT_GRADE, "Cannot grade"),
        (PATHOLOGY_ABSENT, "Absent"),
        (PATHOLOGY_QUESTIONABLE, "Questionable"),
        (PATHOLOGY_PRESENT, "Present"),
    )

    pathology = models.CharField(
        max_length=1,
        choices=PATHOLOGY_CHOICES,
        help_text="Is there a pathology present in the image?",
    )


class RetinaImagePathologyAnnotation(AbstractImageAnnotationModel):
    """Model to annotate presence of specific pathologies."""

    amd_present = models.BooleanField(
        help_text="Is Age-related Macular Degeneration present in this image?"
    )
    dr_present = models.BooleanField(
        help_text="Is Diabetic Retinopathy present in this image?"
    )
    oda_present = models.BooleanField(
        help_text="Are optic disc abnormalitites present in this image?"
    )
    myopia_present = models.BooleanField(
        help_text="Is myopia present in this image?"
    )
    cysts_present = models.BooleanField(
        help_text="Are cysts present in this image?"
    )
    other_present = models.BooleanField(
        help_text="Are other findings present in this image?"
    )


class ImageTextAnnotation(AbstractImageAnnotationModel):
    """Model to annotate a textual comment for an image."""

    text = models.TextField()
