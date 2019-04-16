import logging

from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel

logger = logging.getLogger(__name__)


def get_data_file_name(obj, filename=None):
    return 'data_files/'+str(obj.id)


class DataType(UUIDModel):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=40)
    description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of this data type in markdown.",
    )

    def __str__(self):
        return self.name


class DataFile(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="data_files",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=50, null=False, blank=False)
    file = models.FileField(blank=True, null=True, upload_to=get_data_file_name)
    sha = models.CharField(max_length=40, null=True, blank=True)

    short_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Short description of this file in plain text.",
    )
    long_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of this file in markdown.",
    )
    data_type = models.ForeignKey(DataType, on_delete=models.CASCADE)
    data_format = models.CharField(max_length=50, null=True, blank=True)
    data_size = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name


class DataSet(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="data_sets",
    )
    version = models.CharField(
        max_length=64,
        help_text="The Dataset version",
        blank=True,
        null=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255, null=False, blank=False)
    short_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Short description of this data set in plaintext.",
    )
    long_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Long description of this data set in markdown.",
    )
    card_image_url = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default="https://www.staging.eyrabenchmark.net/static/media/logo.3fc4ddae.png",
        help_text=(
            "DataSet image"
        ),
    )
    card_image_alttext = models.CharField(max_length=255, null=True, blank=True)
    banner_image_url = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default="https://www.staging.eyrabenchmark.net/static/media/logo.3fc4ddae.png",
        help_text=(
            "DataSet image"
        ),
    )
    banner_image_alttext = models.CharField(max_length=255, null=True, blank=True)

    related_datasets =  models.ManyToManyField(
        "grandchallenge.eyra_data.models.DataSet",
        blank = True,
    )

    additional_data_files = models.ManyToManyField(
        DataFile,
        related_name='data_sets',
        blank=True,
    )
    test_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    test_ground_truth_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    def __str__(self):
        return self.name