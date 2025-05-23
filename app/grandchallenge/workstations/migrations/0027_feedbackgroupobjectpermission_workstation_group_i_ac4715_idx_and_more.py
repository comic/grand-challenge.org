# Generated by Django 4.2.21 on 2025-05-15 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "workstations",
            "0026_feedbackuserobjectpermission_workstation_user_id_f2985d_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddIndex(
            model_name="feedbackgroupobjectpermission",
            index=models.Index(
                fields=["group", "permission"],
                name="workstation_group_i_ac4715_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="workstationimageuserobjectpermission",
            index=models.Index(
                fields=["user", "permission"],
                name="workstation_user_id_508b8b_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="workstationuserobjectpermission",
            index=models.Index(
                fields=["user", "permission"],
                name="workstation_user_id_726a64_idx",
            ),
        ),
    ]
