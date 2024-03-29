# Generated by Django 3.1.1 on 2020-12-02 13:08

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import grandchallenge.cases.models
import grandchallenge.core.storage


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("modalities", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Image",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=4096)),
                ("width", models.IntegerField()),
                ("height", models.IntegerField()),
                ("depth", models.IntegerField(null=True)),
                ("voxel_width_mm", models.FloatField(null=True)),
                ("voxel_height_mm", models.FloatField(null=True)),
                ("voxel_depth_mm", models.FloatField(null=True)),
                ("timepoints", models.IntegerField(null=True)),
                ("resolution_levels", models.IntegerField(null=True)),
                ("window_center", models.FloatField(null=True)),
                ("window_width", models.FloatField(null=True)),
                (
                    "color_space",
                    models.CharField(
                        choices=[
                            ("GRAY", "GRAY"),
                            ("RGB", "RGB"),
                            ("RGBA", "RGBA"),
                            ("YCBCR", "YCBCR"),
                        ],
                        max_length=5,
                    ),
                ),
                (
                    "eye_choice",
                    models.CharField(
                        choices=[
                            ("OD", "Oculus Dexter (right eye)"),
                            ("OS", "Oculus Sinister (left eye)"),
                            ("U", "Unknown"),
                            ("NA", "Not applicable"),
                        ],
                        default="NA",
                        help_text="Is this (retina) image from the right or left eye?",
                        max_length=2,
                    ),
                ),
                (
                    "stereoscopic_choice",
                    models.CharField(
                        choices=[
                            ("L", "Left"),
                            ("R", "Right"),
                            ("U", "Unknown"),
                            (None, "Not applicable"),
                        ],
                        default=None,
                        help_text="Is this the left or right image of a stereoscopic pair?",
                        max_length=1,
                        null=True,
                    ),
                ),
                (
                    "field_of_view",
                    models.CharField(
                        choices=[
                            ("F1M", "F1M"),
                            ("F2", "F2"),
                            ("F3M", "F3M"),
                            ("F4", "F4"),
                            ("F5", "F5"),
                            ("F6", "F6"),
                            ("F7", "F7"),
                            ("U", "Unknown"),
                            (None, "Not applicable"),
                        ],
                        default=None,
                        help_text="What is the field of view of this image?",
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "modality",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="modalities.imagingmodality",
                    ),
                ),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.CreateModel(
            name="RawImageUploadSession",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Queued"),
                            (1, "Started"),
                            (2, "Re-Queued"),
                            (3, "Failed"),
                            (4, "Succeeded"),
                            (5, "Cancelled"),
                        ],
                        default=0,
                    ),
                ),
                ("error_message", models.TextField(default=None, null=True)),
                (
                    "creator",
                    models.ForeignKey(
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="RawImageFile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("filename", models.CharField(max_length=4096)),
                ("staged_file_id", models.UUIDField(blank=True, null=True)),
                ("error", models.TextField(default=None, null=True)),
                ("consumed", models.BooleanField(default=False)),
                (
                    "upload_session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="cases.rawimageuploadsession",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="ImageFile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "image_type",
                    models.CharField(
                        choices=[
                            ("MHD", "MHD"),
                            ("TIFF", "TIFF"),
                            ("DZI", "DZI"),
                        ],
                        default="MHD",
                        max_length=4,
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        storage=grandchallenge.core.storage.ProtectedS3Storage(),
                        upload_to=grandchallenge.cases.models.image_file_path,
                    ),
                ),
                (
                    "image",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="files",
                        to="cases.image",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.AddField(
            model_name="image",
            name="origin",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="cases.rawimageuploadsession",
            ),
        ),
    ]
