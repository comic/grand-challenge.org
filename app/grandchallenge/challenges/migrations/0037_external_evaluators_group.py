import django.db.models.deletion
from django.db import migrations, models


def create_external_evaluators_groups(apps, schema_editor):
    Challenge = apps.get_model("challenges", "Challenge")  # noqa: N806
    Group = apps.get_model("auth", "Group")  # noqa: N806

    challenges = Challenge.objects.all()
    for challenge in challenges:
        external_evaluators_group = Group.objects.create(
            name=f"{challenge.short_name}_external_evaluators"
        )
        challenge.external_evaluators_group = external_evaluators_group
    challenges.bulk_update(challenges, ["external_evaluators_group"])


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("challenges", "0036_challenge_is_suspended"),
    ]

    operations = [
        migrations.AddField(
            model_name="challenge",
            name="external_evaluators_group",
            field=models.OneToOneField(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="external_evaluators_of_challenge",
                to="auth.group",
            ),
        ),
        migrations.RunPython(create_external_evaluators_groups, elidable=True),
    ]
