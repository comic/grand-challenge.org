from django.db import models
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from rest_framework.serializers import ValidationError
from grandchallenge.core.models import UUIDModel
from grandchallenge.cases.models import Image
# from retina_backend.users.models import User
from django.contrib.auth import get_user_model


class AbstractAnnotationModel(UUIDModel):
    """
    Abstract model for an annotation linking to a grader.
    Overrides the created attribute to allow the value to be changed.
    See: https://docs.djangoproject.com/en/2.1/ref/models/fields/#django.db.models.DateField.auto_now_add
    """
    grader = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    created = models.DateTimeField(default=timezone.now)  # Override inherited 'created' attribute

    class Meta(UUIDModel.Meta):
        abstract = True


class AbstractImageAnnotationModel(AbstractAnnotationModel):
    """
    Abstract model for annotation linking to a single image
    """
    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    def __str__(self):
        return "<{} by {} on {} for {}>".format(
            self.__class__.__name__,
            self.grader.username,
            self.created.strftime("%Y-%m-%d at %H:%M:%S"),
            self.image,
        )

    class Meta(UUIDModel.Meta):
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
    """
    Model for a measurement (=2 coordinates) on a 2D image
    """

    # Fields for start and end coordinates (x,y) of the voxel for the measurement
    start_voxel = ArrayField(models.FloatField(), size=2)
    end_voxel = ArrayField(models.FloatField(), size=2)

    class Meta(AbstractImageAnnotationModel.Meta):
        # Create unique together constraint to disallow duplicates
        unique_together = ("image", "grader", "created", "start_voxel", "end_voxel")


class BooleanClassificationAnnotation(AbstractNamedImageAnnotationModel):
    """
    General model for boolean image-level classification
    """
    value = models.BooleanField()


class IntegerClassificationAnnotation(AbstractNamedImageAnnotationModel):
    """
    General model for integer image-level classification
    """
    value = models.IntegerField()


class CoordinateListAnnotation(AbstractNamedImageAnnotationModel):
    """
    General model for list of coordinates annotation
    """
    # General form: [[x1,y1],[x2,y2],...]
    value = ArrayField(ArrayField(models.FloatField(), size=2))


class PolygonAnnotationSet(AbstractNamedImageAnnotationModel):
    """
    General model containing a set of specific polygon annotations.
    Contains only the fields from AbstractNamedImageAnnotationModel
    """


class SinglePolygonAnnotation(UUIDModel):
    """
    General model for a single polygon annotation (list of coordinates).
    Belongs to a PolygonAnnotationSet
    """
    annotation_set = models.ForeignKey(PolygonAnnotationSet, on_delete=models.CASCADE)

    # General form: [[x1,y1],[x2,y2],...]
    value = ArrayField(ArrayField(models.FloatField(), size=2))


class LandmarkAnnotationSet(AbstractAnnotationModel):
    """
    General model containing a set of specific landmark annotations.
    Contains only the fields from AbstractAnnotationModel
    """
    class Meta(AbstractAnnotationModel.Meta):
        unique_together = ("grader", "created")


class SingleLandmarkAnnotation(UUIDModel):
    """
    Model containing a set of landmarks (coordinates on an image) that represent the same locations as all the other
    LandmarkAnnotations in the LandmarkAnnotationSet it belongs to. This is used for image registration.
    """
    annotation_set = models.ForeignKey(LandmarkAnnotationSet, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)

    # General form: [[x1,y1],[x2,y2],...]
    landmarks = ArrayField(ArrayField(models.FloatField(), size=2))

    class Meta(UUIDModel.Meta):
        # Make sure there is only one LandmarkAnnotation for an image in a set
        unique_together = ("image", "annotation_set")


"""
Retina specific annotations
"""


class ETDRSGridAnnotation(AbstractImageAnnotationModel):
    """
    Model for the placement of an ETDRS grid on an retina image
    """

    # Fields for location of fovea and optic disk on the images: (x,y) coordinates
    fovea = ArrayField(models.FloatField(), size=2)
    optic_disk = ArrayField(models.FloatField(), size=2)

    class Meta(AbstractImageAnnotationModel.Meta):
        unique_together = ("image", "grader", "created")
