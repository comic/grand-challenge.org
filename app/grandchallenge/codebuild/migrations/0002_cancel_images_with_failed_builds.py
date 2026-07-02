from django.db import migrations


def cancel_initialized_images_with_failed_builds(apps, schema_editor):
    from grandchallenge.codebuild.models import BuildStatusChoices
    from grandchallenge.components.models import ImportStatusChoices

    Build = apps.get_model("codebuild", "Build")  # noqa: N806
    AlgorithmImage = apps.get_model(  # noqa: N806
        "algorithms", "AlgorithmImage"
    )

    failed_statuses = {
        BuildStatusChoices.FAILED,
        BuildStatusChoices.FAULT,
        BuildStatusChoices.TIMED_OUT,
        BuildStatusChoices.STOPPED,
    }

    algorithm_image_pks = Build.objects.filter(
        status__in=failed_statuses,
        algorithm_image__isnull=False,
        algorithm_image__import_status=ImportStatusChoices.INITIALIZED,
    ).values_list("algorithm_image_id", flat=True)

    AlgorithmImage.objects.filter(pk__in=algorithm_image_pks).update(
        import_status=ImportStatusChoices.CANCELLED
    )


class Migration(migrations.Migration):
    dependencies = [
        ("codebuild", "0001_initial"),
        ("algorithms", "0102_alter_endpoint_options_alter_job_options"),
    ]

    operations = [
        migrations.RunPython(
            cancel_initialized_images_with_failed_builds,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
    ]
