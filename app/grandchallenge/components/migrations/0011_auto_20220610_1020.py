# Generated by Django 3.2.13 on 2022-06-10 10:20

from django.db import migrations, models

import grandchallenge.components.models
import grandchallenge.core.storage
import grandchallenge.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("components", "0010_auto_20220602_0902"),
    ]

    operations = [
        migrations.AlterField(
            model_name="componentinterface",
            name="kind",
            field=models.CharField(
                choices=[
                    ("STR", "String"),
                    ("INT", "Integer"),
                    ("FLT", "Float"),
                    ("BOOL", "Bool"),
                    ("JSON", "Anything"),
                    ("CHART", "Chart"),
                    ("2DBB", "2D bounding box"),
                    ("M2DB", "Multiple 2D bounding boxes"),
                    ("DIST", "Distance measurement"),
                    ("MDIS", "Multiple distance measurements"),
                    ("POIN", "Point"),
                    ("MPOI", "Multiple points"),
                    ("POLY", "Polygon"),
                    ("MPOL", "Multiple polygons"),
                    ("LINE", "Line"),
                    ("MLIN", "Multiple lines"),
                    ("CHOI", "Choice"),
                    ("MCHO", "Multiple choice"),
                    ("IMG", "Image"),
                    ("SEG", "Segmentation"),
                    ("HMAP", "Heat Map"),
                    ("PDF", "PDF file"),
                    ("SQREG", "SQREG file"),
                    ("JPEG", "Thumbnail jpg"),
                    ("PNG", "Thumbnail png"),
                    ("OBJ", "OBJ file"),
                    ("MP4", "MP4 file"),
                    ("CSV", "CSV file"),
                    ("ZIP", "ZIP file"),
                ],
                help_text="What is the type of this interface? Used to validate interface values and connections between components.",
                max_length=5,
            ),
        ),
        migrations.AlterField(
            model_name="componentinterfacevalue",
            name="file",
            field=models.FileField(
                blank=True,
                null=True,
                storage=grandchallenge.core.storage.ProtectedS3Storage(),
                upload_to=grandchallenge.components.models.component_interface_value_path,
                validators=[
                    grandchallenge.core.validators.ExtensionValidator(
                        allowed_extensions=(
                            ".json",
                            ".zip",
                            ".csv",
                            ".png",
                            ".jpg",
                            ".jpeg",
                            ".pdf",
                            ".sqreg",
                            ".obj",
                            ".mp4",
                        )
                    ),
                    grandchallenge.core.validators.MimeTypeValidator(
                        allowed_types=(
                            "application/json",
                            "application/zip",
                            "text/plain",
                            "application/csv",
                            "text/csv",
                            "application/pdf",
                            "image/png",
                            "image/jpeg",
                            "application/octet-stream",
                            "application/x-sqlite3",
                            "application/vnd.sqlite3",
                            "video/mp4",
                        )
                    ),
                ],
            ),
        ),
    ]
