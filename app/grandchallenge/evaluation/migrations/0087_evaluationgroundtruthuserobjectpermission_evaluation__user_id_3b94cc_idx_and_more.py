# Generated by Django 4.2.21 on 2025-05-15 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "evaluation",
            "0086_evaluationgroundtruthgroupobjectpermission_evaluation__group_i_1bed7d_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddIndex(
            model_name="evaluationgroundtruthuserobjectpermission",
            index=models.Index(
                fields=["user", "permission"],
                name="evaluation__user_id_3b94cc_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="evaluationuserobjectpermission",
            index=models.Index(
                fields=["user", "permission"],
                name="evaluation__user_id_7c6d20_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="methoduserobjectpermission",
            index=models.Index(
                fields=["user", "permission"],
                name="evaluation__user_id_6f8311_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="phaseuserobjectpermission",
            index=models.Index(
                fields=["user", "permission"],
                name="evaluation__user_id_e9d186_idx",
            ),
        ),
    ]
