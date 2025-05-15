from django.db import migrations
from django.db.models import F


def create_job_utilizations(apps, schema_editor):
    Job = apps.get_model("algorithms", "Job")  # noqa: N806
    JobUtilization = apps.get_model(  # noqa: N806
        "algorithms", "JobUtilization"
    )
    for job in (
        Job.objects.annotate(duration=F("completed_at") - F("started_at"))
        .filter(job_utilization__isnull=True)
        .iterator()
    ):
        JobUtilization.objects.create(
            job=job,
            duration=job.duration,
            compute_cost_euro_millicents=job.compute_cost_euro_millicents,
        )


def set_challenges_to_job_utilizations(apps, schema_editor):
    Job = apps.get_model("algorithms", "Job")  # noqa: N806
    Permission = apps.get_model("auth", "Permission")  # noqa: N806
    Challenge = apps.get_model("challenges", "Challenge")  # noqa: N806
    challenges = Challenge.objects.all()
    if challenges.exists():
        permission = Permission.objects.get(
            codename="view_job",
            content_type__app_label="algorithms",
            content_type__model="job",
        )
        for challenge in challenges:
            jobs = Job.objects.filter(
                jobgroupobjectpermission__group=challenge.admins_group,
                jobgroupobjectpermission__permission=permission,
            ).distinct()
            for job in jobs:
                job.update_utilization(challenge=challenge)


def set_phases_to_job_utilizations(apps, schema_editor):
    Job = apps.get_model("algorithms", "Job")  # noqa: N806
    Phase = apps.get_model("evaluation", "Phase")  # noqa: N806
    for phase in Phase.objects.all():
        jobs = Job.objects.filter(
            job_utilization__phase__isnull=False,
            inputs__archive_items__archive__phase=phase,
            algorithm_image__submission__phase=phase,
        ).distinct()
        for job in jobs:
            job.update_utilization(
                phase=phase,
                archive=phase.archive,
                external_evaluation=phase.external_evaluation,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("algorithms", "0075_jobutilization"),
        ("auth", "0012_alter_user_first_name_max_length"),
        (
            "challenges",
            "0053_challengeuserobjectpermission_challenges__user_id_7f9623_idx_and_more",
        ),
        ("evaluation", "0088_evaluationutilization"),
    ]

    operations = [
        migrations.RunPython(create_job_utilizations, elidable=True),
        migrations.RunPython(
            set_challenges_to_job_utilizations, elidable=True
        ),
        migrations.RunPython(set_phases_to_job_utilizations, elidable=True),
    ]
