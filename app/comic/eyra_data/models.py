import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from comic.core.models import UUIDModel

logger = logging.getLogger(__name__)


def get_data_file_name(obj, filename=None):
    return 'data_files/'+str(obj.id)


class DataType(UUIDModel):
    """
    Type for a :class:`DataFile`. Could be a file type, but could be something more abstract.
    Also used for the input/output definitions of :class:`Interfaces <comic.eyra_algorithms.models.Interface>`.
    """
    name = models.CharField(
        max_length=40,
        help_text="Name of this type",
    )
    description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of this data type in markdown.",
    )

    def __str__(self):
        return self.name


class DataFile(UUIDModel):
    """
    Represents a file
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="data_files",
        help_text="Creator of this DataFile",
    )

    name = models.CharField(
        max_length=50,
        null=False,
        blank=False,
        help_text="Name of this file",
    )
    file = models.FileField(
        blank=True,
        null=True,
        upload_to=get_data_file_name,
        help_text="This files contents (the bits)",
    )
    sha = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text="Reserved for SHA checksum (currently not used)"
    )

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
    type = models.ForeignKey(
        DataType,
        on_delete=models.CASCADE,
        help_text="The type of this file",
    )
    size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="The size of this file in bytes",
    )

    def get_download_url(self):
        storage = self.file.storage
        if storage.bucket:  # s3 storage
            storage.bucket.meta.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': storage.bucket.name,
                    'Key': storage._encode_name(self.file.name),
                    'ResponseContentDisposition': f'attachment; filename="{self.name}"'
                })
        return self.file.url

    def __str__(self):
        return self.name


class DataSet(UUIDModel):
    """
    DataSets are used in :class:`Benchmarks <comic.eyra_benchmarks.models.Benchmark>`.
    """
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="data_sets",
        help_text="Creator of this DataSet",
    )
    version = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="The Dataset version",
    )
    name = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        help_text="The name of this dataset",
    )
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
        help_text="Image used in the DataSet card component",
    )
    card_image_alttext = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="alt attribute for image in DataSet card component",
    )
    banner_image_url = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        default="https://www.staging.eyrabenchmark.net/static/media/logo.3fc4ddae.png",
        help_text="(wide) image used as a banner in DataSet detail page",
    )
    banner_image_alttext = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="alt attribute for image in DataSet details header",
    )
    related_datasets = models.ManyToManyField(
        "eyra_data.DataSet",
        blank=True,
        related_name='related_data_sets',
        help_text="Other DataSets related to this one",
    )
    public_test_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="DataFile used as 'test_data' input in public submission container",
    )
    public_ground_truth_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="DataFile used as 'ground_truth' input in public evaluation container",
    )
    public_test_data_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of the test data.",
    )
    public_test_data_sampling_method = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Sampling method of the test data.",
    )

    private_test_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="DataFile used as 'test_data' input in private submission container",
    )
    private_ground_truth_data_file = models.ForeignKey(
        DataFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="DataFile used as 'ground_truth' input in private evaluation container",
    )
    private_test_data_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of the test data.",
    )
    private_test_data_sampling_method = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Sampling method of the test data.",
    )

    participant_data_files = models.ManyToManyField(
        DataFile,
        related_name='data_sets',
        blank=True,
        help_text="Other DataFiles downloadable by a participant.",
    )
    participant_data_description = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Description of the data.",
    )
    participant_data_sampling_method = models.TextField(
        default="",
        blank=True,
        null=True,
        help_text="Sampling method of the data.",
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        if self.public_test_data_file and self.private_test_data_file:
            if not self.public_test_data_file.type == self.private_test_data_file.type:
                raise ValidationError('Public & private test data should have same types.')

        if self.public_ground_truth_data_file and self.private_ground_truth_data_file:
            if not self.public_ground_truth_data_file.type == self.private_ground_truth_data_file.type:
                raise ValidationError('Public & private ground truth should have same types.')
