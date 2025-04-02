from django.db import migrations


def migrate_evaluation_inputs_and_outputs(apps, _schema_editor):
    Phase = apps.get_model("evaluation", "Phase")  # noqa: N806
    PhaseAdditionalEvaluationInput = apps.get_model(  # noqa: N806
        "evaluation", "PhaseAdditionalEvaluationInput"
    )
    PhaseEvaluationOutput = apps.get_model(  # noqa: N806
        "evaluation", "PhaseEvaluationOutput"
    )

    for phase in Phase.objects.prefetch_related("inputs", "outputs").all():
        inputs = phase.inputs.all()
        outputs = phase.outputs.all()

        for input in inputs:
            PhaseAdditionalEvaluationInput.objects.create(
                phase=phase, socket=input
            )

        for output in outputs:
            PhaseEvaluationOutput.objects.create(phase=phase, socket=output)


class Migration(migrations.Migration):
    dependencies = [
        (
            "evaluation",
            "0076_add_evaluation_input_and_output_throughmodels",
        ),
    ]

    operations = [
        migrations.RunPython(
            migrate_evaluation_inputs_and_outputs, elidable=True
        ),
    ]
