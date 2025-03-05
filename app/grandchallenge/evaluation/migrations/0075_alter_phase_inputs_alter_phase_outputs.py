from django.db import migrations, models


def remove_phase_inputs(apps, _schema_editor):
    Phase = apps.get_model("evaluation", "Phase")  # noqa: N806

    for phase in Phase.objects.all():
        phase.inputs.clear()


class Migration(migrations.Migration):
    dependencies = [
        ("components", "0024_alter_componentinterface_kind_and_more"),
        ("evaluation", "0074_alter_phase_algorithm_inputs_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="phase",
            name="inputs",
            field=models.ManyToManyField(
                blank=True,
                related_name="evaluation_inputs",
                to="components.componentinterface",
            ),
        ),
        migrations.RunPython(remove_phase_inputs, elidable=True),
    ]
