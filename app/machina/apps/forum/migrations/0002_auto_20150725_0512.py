from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("forum", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="forum",
            options={
                "ordering": ["tree_id", "lft"],
                "verbose_name": "Forum",
                "verbose_name_plural": "Forums",
            },
        ),
    ]
