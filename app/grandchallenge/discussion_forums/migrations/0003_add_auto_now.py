from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("discussion_forums", "0002_migrate_old_forums"),
    ]

    operations = [
        migrations.AlterField(
            model_name="Forum",
            name="modified",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="Forum",
            name="created",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="ForumTopic",
            name="modified",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="ForumTopic",
            name="created",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="ForumPost",
            name="modified",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="ForumPost",
            name="created",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="TopicReadRecord",
            name="modified",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="TopicReadRecord",
            name="created",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
