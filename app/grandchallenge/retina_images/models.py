import uuid
from PIL import Image as PILImage
import numpy as np
from pathlib import Path
import SimpleITK as sitk
from django.db import models
from django.contrib.postgres.fields import CICharField, ArrayField
from grandchallenge.core.models import UUIDModel
from grandchallenge.studies.models import Study
from grandchallenge.cases.models import Image


class RetinaImage(UUIDModel):
    """
    Model for a image. Child of Series
    """

    study = models.ForeignKey(Study, on_delete=models.CASCADE)

    # number = models.IntegerField()
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    # image = models.ImageField(
    #     max_length=255, upload_to="images/", height_field="height", width_field="width"
    # )
    # height = models.PositiveIntegerField(blank=True, null=True)
    # width = models.PositiveIntegerField(blank=True, null=True)

    MODALITY_CF = "CF"
    MODALITY_OCT = "OCT"
    MODALITY_FA = "FA"
    MODALITY_HRA = "HRA"
    MODALITY_FUN = "FUN"
    MODALITY_OBS = "OBS"
    MODALITY_TRC = "TRC"
    MODALITY_CHOICES = (
        (MODALITY_CF, "Color fundus"),
        (MODALITY_OCT, "Optical coherence tomography"),
        (MODALITY_FA, "Fluorescein angiography"),
        (MODALITY_HRA, "Heidelberg retinal angiography"),
        (MODALITY_FUN, "Color fundus"),
        (MODALITY_OBS, "OBS"),
        (MODALITY_TRC, "TRC"),
    )
    modality = CICharField(
        max_length=3, choices=MODALITY_CHOICES, blank=True, null=True
    )

    EYE_OD = "OD"
    EYE_OS = "OS"
    EYE_UNKNOWN = "U"
    EYE_CHOICES = (
        (EYE_OD, "Oculus Dexter (right eye)"),
        (EYE_OS, "Oculus Sinister (left eye)"),
        (EYE_UNKNOWN, "Unknown"),
    )
    eye_choice = CICharField(
        max_length=2,
        choices=EYE_CHOICES,
        default=EYE_UNKNOWN,
        help_text="The eye of which this image is from",
    )

    # Voxel size field. Order: [ axial, lateral, transversal ]
    voxel_size = ArrayField(
        models.FloatField(blank=True, null=True), size=3, blank=True, null=True
    )

    name = models.CharField(max_length=255)

    def __str__(self):
        return "<{} {} {}>".format(self.__class__.__name__, self.name, self.modality)

    def get_sitk_image(self):
        image_path = Path(self.image.files.first().file.path)
        if not Path.is_file(image_path):
            return None
        # TODO add try/catch for failing to load mhd file
        return sitk.ReadImage(str(image_path))

    @staticmethod
    def create_image_file_name(file):
        uuid_str = str(uuid.uuid4())
        # extension = imghdr.what('tmp/' + file.name) # remove tmp?
        extension = file.name.split(".")[-1]  # No file validation... unsafe?
        return "{}.{}".format(uuid_str, extension)

    def get_all_oct_images(self):
        # Returns all oct images that belong in the same series
        if self.modality == RetinaImage.MODALITY_OCT:
            return self.study.retinaimage_set.filter(modality=RetinaImage.MODALITY_OCT)
        else:
            # raise exception?
            return []

    def get_all_oct_images_as_npy(self):
        # Returns all oct images from one series as a numpy array
        npy = []
        for image in self.get_all_oct_images():
            npy.append(np.array(PILImage.open(image.image.path)))
        return npy

    class Meta(UUIDModel.Meta):
        unique_together = ("study", "name", "modality")
