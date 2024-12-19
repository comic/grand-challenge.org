from django.db import migrations

from grandchallenge.algorithms.models import (
    get_existing_interface_for_inputs_and_outputs,
)


def add_algorithm_interfaces_to_jobs(apps, _schema_editor):
    AlgorithmInterface = apps.get_model(  # noqa: N806
        "algorithms", "AlgorithmInterface"
    )
    Job = apps.get_model("algorithms", "Job")  # noqa: N806

    jobs = Job.objects.select_related("algorithm_image__algorithm").all()
    for job in jobs:
        interface = get_existing_interface_for_inputs_and_outputs(
            inputs=job.inputs.all(), outputs=job.outputs.all()
        )
        if not interface:
            interface = AlgorithmInterface.objects.create()
            interface.inputs.set(job.inputs.all())
            interface.outputs.set(job.outputs.all())

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
