from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("forum_conversation", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Attachment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        upload_to="machina/attachments", verbose_name="File"
                    ),
                ),
                (
                    "comment",
                    models.CharField(
                        max_length=255,
                        null=True,
                        verbose_name="Comment",
                        blank=True,
                    ),
                ),
                (
                    "post",
                    models.ForeignKey(
                        related_name="attachments",
                        verbose_name="Post",
                        to="forum_conversation.Post",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "abstract": False,
                "verbose_name": "Attachment",
                "verbose_name_plural": "Attachments",
            },
        ),
    ]
