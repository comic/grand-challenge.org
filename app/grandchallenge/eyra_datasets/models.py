import logging

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_s3_storage.storage import S3Storage

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import UUIDModel

logger = logging.getLogger(__name__)


class DataSet(UUIDModel):
    # TYPES = {type.name: type for type in types}

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="_datasets",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=20, null=False, blank=False)
    type = models.ForeignKey('DataSetType', on_delete=models.CASCADE)
    frozen = models.BooleanField(default=False)
    challenges = models.ManyToManyField(Challenge, related_name='datasets')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return ( 'type', 'name')
        return ()


class DataSetType(UUIDModel):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=40)

    def __str__(self):
        return self.name


class DataSetTypeFile(UUIDModel):
    dataset_type = models.ForeignKey('DataSetType', on_delete=models.CASCADE, related_name='files')
    name = models.CharField(max_length=40)
    required = models.BooleanField(default=False)


# inject keys in the constructor, otherwise they'll end up in the migrations file
class CustomStorage(S3Storage):
    def __init__(self, **kwargs):
        kwargs['aws_access_key_id'] = settings.S3_ACCESS_KEY_ID
        kwargs['aws_secret_access_key'] = settings.S3_SECRET_ACCESS_KEY
        super().__init__(**kwargs)


storage = CustomStorage(
    aws_s3_bucket_name = 'eyra-datasets',
    aws_s3_endpoint_url = settings.S3_ENDPOINT_URL,
    aws_s3_file_overwrite = True,
)


def get_dataset_file_name(obj, filename):
    return 'dataset_files/'+str(obj.id)


class DataSetFile(UUIDModel):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    dataset = models.ForeignKey(
        to=DataSet, on_delete=models.CASCADE, related_name="files"
    )
    original_file_name = models.CharField(null=True, blank=True, max_length=150)
    dataset_type_file = models.ForeignKey(DataSetTypeFile, on_delete=models.CASCADE)
    file = models.FileField(storage=storage, blank=True, upload_to=get_dataset_file_name)
    sha = models.CharField(max_length=40, null=True, blank=True)
    is_public = models.BooleanField(default=False)


@receiver(post_save, sender=DataSet)
def create_draft_files(sender, instance, created, **kwargs):
    if created:
        for type_file in instance.type.files.all():
            new_file = DataSetFile(
                dataset=instance,
                dataset_type_file=type_file
            )
            new_file.save()
