from django.db import migrations


def add_algorithm_interfaces_to_jobs(apps, _schema_editor):
    Algorithm = apps.get_model("algorithms", "Algorithm")  # noqa: N806
    Job = apps.get_model("algorithms", "Job")  # noqa: N806

    for algorithm in Algorithm.objects.prefetch_related("interfaces").all():
        Job.objects.filter(algorithm_image__algorithm=algorithm).update(
            algorithm_interface=algorithm.interfaces.get()
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "algorithms",
            "0065_create_algorithm_interfaces",
        ),
    ]

    operations = [
        migrations.RunPython(add_algorithm_interfaces_to_jobs, elidable=True),
    ]
