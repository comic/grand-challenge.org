from django.db import migrations


def set_average_size_job_output_mb_for_tasks(apps, schema_editor):
    ChallengeRequest = apps.get_model(  # noqa: N806
        "challenges", "ChallengeRequest"
    )

    for challenge_request in ChallengeRequest.objects.all():
        challenge_request.average_size_job_output_mb_for_tasks = [
            0 for _ in challenge_request.task_ids
        ]
        challenge_request.save()


class Migration(migrations.Migration):

    dependencies = [
        (
            "challenges",
            "0072_challengerequest_average_size_output_mb_for_tasks",
        ),
    ]

    operations = [
        migrations.RunPython(
            set_average_size_job_output_mb_for_tasks, elidable=True
        ),
    ]
