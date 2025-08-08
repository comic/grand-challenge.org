from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("forum_polls", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="topicpollvote",
            name="anonymous_key",
            field=models.CharField(
                max_length=100,
                null=True,
                verbose_name="Anonymous user forum key",
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="topicpollvote",
            name="voter",
            field=models.ForeignKey(
                related_name="poll_votes",
                verbose_name="Voter",
                blank=True,
                to=settings.AUTH_USER_MODEL,
                null=True,
                on_delete=models.CASCADE,
            ),
        ),
    ]
