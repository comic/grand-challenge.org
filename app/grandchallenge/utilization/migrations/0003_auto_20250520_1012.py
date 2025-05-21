from django.db import migrations
from django.db.models import F


def create_evaluation_utilizations(apps, schema_editor):
    Evaluation = apps.get_model("evaluation", "Evaluation")  # noqa: N806
    EvaluationUtilization = apps.get_model(  # noqa: N806
        "utilization", "EvaluationUtilization"
    )
    for evaluation in (
        Evaluation.objects.annotate(
            duration=F("completed_at") - F("started_at")
        )
        .filter(evaluationutilization__isnull=True)
        .iterator()
    ):
        kwargs = dict(
            created=evaluation.created,
            duration=evaluation.duration,
            compute_cost_euro_millicents=evaluation.compute_cost_euro_millicents,
            external_evaluation=evaluation.submission.phase.external_evaluation,
            algorithm_image=evaluation.submission.algorithm_image,
            archive=evaluation.submission.phase.archive,
            challenge=evaluation.submission.phase.challenge,
            creator=evaluation.submission.creator,
            evaluation=evaluation,
            phase=evaluation.submission.phase,
        )
        if evaluation.submission.algorithm_image is not None:
            kwargs.update(
                algorithm=evaluation.submission.algorithm_image.algorithm,
            )
        EvaluationUtilization.objects.create(**kwargs)


def create_job_utilizations(apps, schema_editor):
    Job = apps.get_model("algorithms", "Job")  # noqa: N806
    JobUtilization = apps.get_model(  # noqa: N806
        "utilization", "JobUtilization"
    )
    for job in (
        Job.objects.annotate(duration=F("completed_at") - F("started_at"))
        .filter(jobutilization__isnull=True)
        .iterator()
    ):
        JobUtilization.objects.create(
            created=job.created,
            duration=job.duration,
            compute_cost_euro_millicents=job.compute_cost_euro_millicents,
            algorithm=job.algorithm_image.algorithm,
            algorithm_image=job.algorithm_image,
            creator=job.creator,
            job=job,
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


def set_phases_and_archive_to_job_utilizations(apps, schema_editor):
    Job = apps.get_model("algorithms", "Job")  # noqa: N806
    Phase = apps.get_model("evaluation", "Phase")  # noqa: N806
    for phase in Phase.objects.all():
        jobs = Job.objects.filter(
            jobutilization__phase__isnull=False,
            inputs__archive_items__archive__phase=phase,
            algorithm_image__submission__phase=phase,
        ).distinct()
        for job in jobs:
            job.update_utilization(
                phase=phase,
                archive=phase.archive,
            )


class Migration(migrations.Migration):

    dependencies = [
        (
            "algorithms",
            "0074_algorithmimageuserobjectpermission_algorithms__user_id_ba5ee9_idx_and_more",
        ),
        ("auth", "0012_alter_user_first_name_max_length"),
        (
            "challenges",
            "0053_challengeuserobjectpermission_challenges__user_id_7f9623_idx_and_more",
        ),
        (
            "evaluation",
            "0087_evaluationgroundtruthuserobjectpermission_evaluation__user_id_3b94cc_idx_and_more",
        ),
        ("utilization", "0002_jobutilization_evaluationutilization"),
    ]

    operations = [
        migrations.RunPython(create_evaluation_utilizations, elidable=True),
        migrations.RunPython(create_job_utilizations, elidable=True),
        migrations.RunPython(
            set_challenges_to_job_utilizations, elidable=True
        ),
        migrations.RunPython(
            set_phases_and_archive_to_job_utilizations, elidable=True
        ),
    ]
