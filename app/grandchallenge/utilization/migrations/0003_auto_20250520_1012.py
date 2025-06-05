from django.db import migrations


def create_evaluation_utilizations(apps, schema_editor):
    Evaluation = apps.get_model("evaluation", "Evaluation")  # noqa: N806
    EvaluationUtilization = apps.get_model(  # noqa: N806
        "utilization", "EvaluationUtilization"
    )

    evaluations_to_create = []
    n_created = 0

    if not Evaluation.objects.exists():
        return

    for evaluation in (
        Evaluation.objects.filter(evaluation_utilization__isnull=True)
        .only(
            "completed_at",
            "started_at",
            "compute_cost_euro_millicents",
            "submission",
            "submission__algorithm_image",
            "submission__phase",
            "submission__phase__external_evaluation",
            "submission__phase__archive",
            "submission__phase__challenge",
            "submission__creator",
        )
        .order_by("created")
        .iterator(chunk_size=1000)
    ):
        if evaluation.completed_at and evaluation.started_at:
            duration = evaluation.completed_at - evaluation.started_at
        else:
            duration = None

        kwargs = dict(
            duration=duration,
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

        evaluations_to_create.append(EvaluationUtilization(**kwargs))

        if len(evaluations_to_create) >= 1000:
            EvaluationUtilization.objects.bulk_create(evaluations_to_create)
            n_created += len(evaluations_to_create)
            evaluations_to_create = []

    if evaluations_to_create:
        EvaluationUtilization.objects.bulk_create(evaluations_to_create)
        n_created += len(evaluations_to_create)

    print(f"Created {n_created} Evaluation Utilizations")


def create_job_utilizations(apps, schema_editor):
    Job = apps.get_model("algorithms", "Job")  # noqa: N806
    JobUtilization = apps.get_model(  # noqa: N806
        "utilization", "JobUtilization"
    )

    job_utlizations_to_create = []
    n_created = 0

    if not Job.objects.exists():
        return

    for job in (
        Job.objects.filter(job_utilization__isnull=True)
        .only(
            "completed_at",
            "started_at",
            "compute_cost_euro_millicents",
            "algorithm_image",
            "algorithm_image__algorithm",
            "creator",
        )
        .order_by("created")
        .iterator(chunk_size=1000)
    ):
        if job.completed_at and job.started_at:
            duration = job.completed_at - job.started_at
        else:
            duration = None

        job_utlizations_to_create.append(
            JobUtilization(
                duration=duration,
                compute_cost_euro_millicents=job.compute_cost_euro_millicents,
                algorithm=job.algorithm_image.algorithm,
                algorithm_image=job.algorithm_image,
                creator=job.creator,
                job=job,
            )
        )

        if len(job_utlizations_to_create) >= 1000:
            JobUtilization.objects.bulk_create(job_utlizations_to_create)
            n_created += len(job_utlizations_to_create)
            job_utlizations_to_create = []

    if job_utlizations_to_create:
        JobUtilization.objects.bulk_create(job_utlizations_to_create)
        n_created += len(job_utlizations_to_create)

    print(f"Created {n_created} Job Utilizations")


def set_challenges_to_job_utilizations(apps, schema_editor):
    JobUtilization = apps.get_model(  # noqa: N806
        "utilization", "JobUtilization"
    )
    Permission = apps.get_model("auth", "Permission")  # noqa: N806
    Challenge = apps.get_model("challenges", "Challenge")  # noqa: N806

    if not Challenge.objects.exists():
        return

    permission = Permission.objects.get(
        codename="view_job",
        content_type__app_label="algorithms",
        content_type__model="job",
    )

    for challenge in Challenge.objects.all():
        job_utilizations = JobUtilization.objects.filter(
            job__jobgroupobjectpermission__group=challenge.admins_group,
            job__jobgroupobjectpermission__permission=permission,
        ).distinct()
        job_utilizations.update(challenge=challenge)


def set_phases_and_archive_to_job_utilizations(apps, schema_editor):
    JobUtilization = apps.get_model(  # noqa: N806
        "utilization", "JobUtilization"
    )
    Phase = apps.get_model("evaluation", "Phase")  # noqa: N806

    if not Phase.objects.exists():
        return

    for phase in Phase.objects.all():
        job_utilizations = JobUtilization.objects.filter(
            job__inputs__archive_items__archive__phase=phase,
            job__algorithm_image__submission__phase=phase,
        ).distinct()
        job_utilizations.update(phase=phase, archive=phase.archive)


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
