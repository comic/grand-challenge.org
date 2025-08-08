from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("forum", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Post",
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
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Creation date"
                    ),
                ),
                (
                    "updated",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Update date"
                    ),
                ),
                (
                    "poster_ip",
                    models.GenericIPAddressField(
                        default="2002::0",
                        null=True,
                        verbose_name="Poster IP address",
                        blank=True,
                    ),
                ),
                (
                    "subject",
                    models.CharField(max_length=255, verbose_name="Subject"),
                ),
                ("content", models.TextField(verbose_name="Content")),
                (
                    "username",
                    models.CharField(
                        max_length=155,
                        null=True,
                        verbose_name="Username",
                        blank=True,
                    ),
                ),
                (
                    "approved",
                    models.BooleanField(default=True, verbose_name="Approved"),
                ),
                (
                    "update_reason",
                    models.CharField(
                        max_length=255,
                        null=True,
                        verbose_name="Update reason",
                        blank=True,
                    ),
                ),
                (
                    "updates_count",
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name="Updates count",
                        editable=False,
                        blank=True,
                    ),
                ),
                (
                    "_content_rendered",
                    models.TextField(null=True, editable=False, blank=True),
                ),
                (
                    "poster",
                    models.ForeignKey(
                        related_name="posts",
                        verbose_name="Poster",
                        blank=True,
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "ordering": ["created"],
                "abstract": False,
                "get_latest_by": "created",
                "verbose_name": "Post",
                "verbose_name_plural": "Posts",
            },
        ),
        migrations.CreateModel(
            name="Topic",
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
                    "created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Creation date"
                    ),
                ),
                (
                    "updated",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Update date"
                    ),
                ),
                (
                    "subject",
                    models.CharField(max_length=255, verbose_name="Subject"),
                ),
                (
                    "slug",
                    models.SlugField(max_length=255, verbose_name="Slug"),
                ),
                (
                    "type",
                    models.PositiveSmallIntegerField(
                        db_index=True,
                        verbose_name="Topic type",
                        choices=[
                            (0, "Default topic"),
                            (1, "Sticky"),
                            (2, "Announce"),
                        ],
                    ),
                ),
                (
                    "status",
                    models.PositiveIntegerField(
                        db_index=True,
                        verbose_name="Topic status",
                        choices=[
                            (0, "Topic unlocked"),
                            (1, "Topic locked"),
                            (2, "Topic moved"),
                        ],
                    ),
                ),
                (
                    "approved",
                    models.BooleanField(default=True, verbose_name="Approved"),
                ),
                (
                    "posts_count",
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name="Posts count",
                        editable=False,
                        blank=True,
                    ),
                ),
                (
                    "views_count",
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name="Views count",
                        editable=False,
                        blank=True,
                    ),
                ),
                (
                    "last_post_on",
                    models.DateTimeField(
                        null=True,
                        verbose_name="Last post added on",
                        blank=True,
                    ),
                ),
                (
                    "forum",
                    models.ForeignKey(
                        related_name="topics",
                        verbose_name="Topic forum",
                        to="forum.Forum",
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "poster",
                    models.ForeignKey(
                        verbose_name="Poster",
                        blank=True,
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "subscribers",
                    models.ManyToManyField(
                        related_name="subscriptions",
                        verbose_name="Subscribers",
                        to=settings.AUTH_USER_MODEL,
                        blank=True,
                    ),
                ),
            ],
            options={
                "ordering": ["-type", "-last_post_on"],
                "abstract": False,
                "get_latest_by": "last_post_on",
                "verbose_name": "Topic",
                "verbose_name_plural": "Topics",
            },
        ),
        migrations.AddField(
            model_name="post",
            name="topic",
            field=models.ForeignKey(
                related_name="posts",
                verbose_name="Topic",
                to="forum_conversation.Topic",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="post",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                to=settings.AUTH_USER_MODEL,
                null=True,
                verbose_name="Lastly updated by",
                on_delete=models.SET_NULL,
            ),
        ),
    ]
