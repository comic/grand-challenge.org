from django.db import migrations

from grandchallenge.algorithms.models import (
    get_existing_interface_for_inputs_and_outputs,
)


def create_algorithm_interfaces(apps, _schema_editor):
    Algorithm = apps.get_model("algorithms", "Algorithm")  # noqa: N806
    AlgorithmInterface = apps.get_model(  # noqa: N806
        "algorithms", "AlgorithmInterface"
    )

    for algorithm in Algorithm.objects.prefetch_related(
        "inputs", "outputs"
    ).all():
        inputs = algorithm.inputs.all()
        outputs = algorithm.outputs.all()

        io = get_existing_interface_for_inputs_and_outputs(
            model=AlgorithmInterface, inputs=inputs, outputs=outputs
        )
        if not io:
            io = AlgorithmInterface.objects.create()
            io.inputs.set(inputs)
            io.outputs.set(outputs)

        algorithm.interfaces.add(io)


class Migration(migrations.Migration):
    dependencies = [
        (
            "algorithms",
            "0064_algorithminterface_algorithminterfaceoutput_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(create_algorithm_interfaces, elidable=True),
    ]
