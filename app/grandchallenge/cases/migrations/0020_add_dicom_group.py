from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cases", "0019_auto_20200120_0604"),
    ]

    operations = [
        # Non-elidable migration moved to post_migrate signal
    ]
