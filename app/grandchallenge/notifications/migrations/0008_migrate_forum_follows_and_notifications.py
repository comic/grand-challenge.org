from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        (
            "notifications",
            "0007_followgroupobjectpermission_notificatio_group_i_cc45cf_idx_and_more",
        ),
        ("discussion_forums", "0002_migrate_old_forums"),
    ]

    operations = []
