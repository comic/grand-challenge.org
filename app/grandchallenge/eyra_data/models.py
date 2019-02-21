import logging

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.core.models import UUIDModel

logger = logging.getLogger(__name__)


def get_data_file_name(obj, filename):
    return 'data_files/'+str(obj.id)


class DataType(UUIDModel):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=40)
    description = models.TextField(
        default="",
        blank=True,
        help_text="Description of this data type in markdown.",
    )

    def __str__(self):
        return self.name


class DataFile(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="_datasets",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=50, null=False, blank=False)
    description = models.TextField(
        default="",
        blank=True,
        help_text="Description of this dataset in markdown.",
    )
    type = models.ForeignKey(DataType, on_delete=models.CASCADE)
    frozen = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    file = models.FileField(blank=True, upload_to=get_data_file_name)
    sha = models.CharField(max_length=40, null=True, blank=True)
    original_file_name = models.CharField(null=True, blank=True, max_length=150)

    # benchmarks = models.ManyToManyField(Benchmark, related_name='datasets')

    # def get_readonly_fields(self, request, obj=None):
    #     if obj:  # editing an existing object
    #         return ( 'type', 'name')
    #     return ()

#
# class FileType(UUIDModel):
#     dataset_type = models.ForeignKey('grandchallenge.eyra_data.models.DataType', on_delete=models.CASCADE, related_name='files')
#     name = models.CharField(max_length=40)
#     required = models.BooleanField(default=False)
#     description = models.TextField(
#         default="",
#         blank=True,
#         help_text="Description of this what this file represents.",
#     )

#
#
#
#
# class DataSetFile(UUIDModel):
#     created = models.DateTimeField(auto_now_add=True)
#     modified = models.DateTimeField(auto_now=True)
#     dataset = models.ForeignKey(
#         to=DataFile, on_delete=models.CASCADE, related_name="files"
#     )
#     description = models.TextField(
#         default="",
#         blank=True,
#         help_text="Description of this file.",
#     )
#     file_type = models.ForeignKey(FileType, on_delete=models.CASCADE)
