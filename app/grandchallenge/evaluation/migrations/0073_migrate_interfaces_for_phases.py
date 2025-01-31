from django.db import migrations

from grandchallenge.algorithms.models import (
    get_existing_interface_for_inputs_and_outputs,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices


def add_algorithm_interfaces_for_phases(apps, _schema_editor):
    Phase = apps.get_model("evaluation", "Phase")  # noqa: N806
    AlgorithmInterface = apps.get_model(  # noqa: N806
        "algorithms", "AlgorithmInterface"
    )

    for phase in (
        Phase.objects.filter(submission_kind=SubmissionKindChoices.ALGORITHM)
        .prefetch_related("algorithm_inputs", "algorithm_outputs")
        .all()
    ):
        inputs = phase.algorithm_inputs.all()
        outputs = phase.algorithm_outputs.all()

        if not inputs or not outputs:
            raise RuntimeError(f"{phase} is improperly configured.")

        io = get_existing_interface_for_inputs_and_outputs(
            model=AlgorithmInterface, inputs=inputs, outputs=outputs
        )
        if not io:
            io = AlgorithmInterface.objects.create()
            io.inputs.set(inputs)
            io.outputs.set(outputs)

        phase.algorithm_interfaces.add(
            io, through_defaults={"is_default": True}
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "evaluation",
            "0072_phasealgorithminterface_phase_algorithm_interfaces_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            add_algorithm_interfaces_for_phases, elidable=True
        ),
    ]
