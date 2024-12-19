from django.db import migrations

from grandchallenge.algorithms.models import (
    get_existing_interface_for_inputs_and_outputs,
)


def add_algorithm_interfaces_to_jobs(apps, _schema_editor):
    AlgorithmInterface = apps.get_model(  # noqa: N806
        "algorithms", "AlgorithmInterface"
    )
    Job = apps.get_model("algorithms", "Job")  # noqa: N806

    jobs = (
        Job.objects.select_related("algorithm_image__algorithm")
        .prefetch_related("inputs", "outputs")
        .all()
    )
    for job in jobs:
        inputs = [input.interface for input in job.inputs.all()]
        outputs = [output.interface for output in job.outputs.all()]

        interface = get_existing_interface_for_inputs_and_outputs(
            model=AlgorithmInterface, inputs=inputs, outputs=outputs
        )
        if not interface:
            interface = AlgorithmInterface.objects.create()
            interface.inputs.set(inputs)
            interface.outputs.set(outputs)

        job.algorithm_interface = interface
        job.algorithm_image.algorithm.interfaces.add(interface)

    jobs.bulk_update(jobs, ["algorithm_interface"])


class Migration(migrations.Migration):
    dependencies = [
        (
            "algorithms",
            "0064_create_algorithm_interfaces",
        ),
    ]

    operations = [
        migrations.RunPython(add_algorithm_interfaces_to_jobs, elidable=True),
    ]
