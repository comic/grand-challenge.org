from datetime import timedelta

from django.contrib.auth.models import Permission
from django.db.models import Count, Sum

from grandchallenge.algorithms.models import (
    AlgorithmImage,
    AlgorithmModel,
    Job,
)
from grandchallenge.cases.models import ImageFile
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.evaluation.models import (
    Evaluation,
    EvaluationGroundTruth,
    Method,
)


def annotate_job_duration_and_compute_costs(*, phase):
    algorithm_jobs = Job.objects.filter(
        inputs__archive_items__archive__phase=phase,
        algorithm_image__submission__phase=phase,
    ).distinct()
    evaluation_jobs = Evaluation.objects.filter(
        submission__phase=phase, submission__phase__external_evaluation=False
    ).distinct()

    update_average_algorithm_job_duration(
        phase=phase, algorithm_jobs=algorithm_jobs
    )
    update_compute_cost_euro_millicents(
        obj=phase,
        algorithm_jobs=algorithm_jobs,
        evaluation_jobs=evaluation_jobs,
    )


def annotate_compute_costs_and_storage_size(*, challenge):
    permission = Permission.objects.get(
        codename="view_job",
        content_type__app_label="algorithms",
        content_type__model="job",
    )
    algorithm_jobs = Job.objects.filter(
        jobgroupobjectpermission__group=challenge.admins_group,
        jobgroupobjectpermission__permission=permission,
    ).distinct()

    evaluation_jobs = Evaluation.objects.filter(
        submission__phase__challenge=challenge,
        submission__phase__external_evaluation=False,
    ).distinct()

    update_size_in_storage_and_registry(
        challenge=challenge,
        algorithm_jobs=algorithm_jobs,
        evaluation_jobs=evaluation_jobs,
    )
    update_compute_cost_euro_millicents(
        obj=challenge,
        algorithm_jobs=algorithm_jobs,
        evaluation_jobs=evaluation_jobs,
    )


def update_size_in_storage_and_registry(
    *, challenge, algorithm_jobs, evaluation_jobs
):
    archive_image_storage = (
        ImageFile.objects.filter(
            image__componentinterfacevalue__archive_items__archive__phase__challenge=challenge
        )
        .distinct()
        .aggregate(Sum("size_in_storage"))
    )
    archive_file_storage = (
        ComponentInterfaceValue.objects.filter(
            archive_items__archive__phase__challenge=challenge
        )
        .distinct()
        .aggregate(Sum("size_in_storage"))
    )

    non_archive_input_image_storage = (
        ImageFile.objects.filter(
            image__componentinterfacevalue__algorithms_jobs_as_input__in=algorithm_jobs
        )
        .exclude(
            image__componentinterfacevalue__archive_items__archive__phase__challenge=challenge
        )
        .distinct()
        .aggregate(Sum("size_in_storage"))
    )
    non_archive_input_file_storage = (
        ComponentInterfaceValue.objects.filter(
            algorithms_jobs_as_input__in=algorithm_jobs
        )
        .exclude(archive_items__archive__phase__challenge=challenge)
        .distinct()
        .aggregate(Sum("size_in_storage"))
    )

    output_image_storage = (
        ImageFile.objects.filter(
            image__componentinterfacevalue__evaluation_evaluations_as_input__in=evaluation_jobs
        )
        .distinct()
        .aggregate(Sum("size_in_storage"))
    )
    output_file_storage = (
        ComponentInterfaceValue.objects.filter(
            evaluation_evaluations_as_input__in=evaluation_jobs
        )
        .distinct()
        .aggregate(Sum("size_in_storage"))
    )

    algorithm_storage = (
        AlgorithmImage.objects.filter(job__in=algorithm_jobs)
        .distinct()
        .aggregate(Sum("size_in_storage"), Sum("size_in_registry"))
    )

    algorithm_model_storage = (
        AlgorithmModel.objects.filter(job__in=algorithm_jobs)
        .distinct()
        .aggregate(Sum("size_in_storage"))
    )

    method_storage = (
        Method.objects.filter(phase__challenge=challenge)
        .distinct()
        .aggregate(Sum("size_in_storage"), Sum("size_in_registry"))
    )

    ground_truth_storage = (
        EvaluationGroundTruth.objects.filter(phase__challenge=challenge)
        .distinct()
        .aggregate(Sum("size_in_storage"))
    )

    items = [
        archive_image_storage,
        archive_file_storage,
        non_archive_input_image_storage,
        non_archive_input_file_storage,
        output_image_storage,
        output_file_storage,
        algorithm_storage,
        algorithm_model_storage,
        method_storage,
        ground_truth_storage,
    ]

    challenge.size_in_storage = sum(
        item["size_in_storage__sum"] or 0 for item in items
    )
    challenge.size_in_registry = sum(
        item.get("size_in_registry__sum") or 0 for item in items
    )


def update_compute_cost_euro_millicents(
    *, obj, algorithm_jobs, evaluation_jobs
):
    algorithm_job_costs = algorithm_jobs.aggregate(
        Sum("compute_cost_euro_millicents")
    )

    evaluation_costs = evaluation_jobs.aggregate(
        Sum("compute_cost_euro_millicents")
    )

    items = [algorithm_job_costs, evaluation_costs]

    obj.compute_cost_euro_millicents = sum(
        item["compute_cost_euro_millicents__sum"] or 0 for item in items
    )


def update_average_algorithm_job_duration(*, phase, algorithm_jobs):
    aggregates = algorithm_jobs.filter(
        status=Job.SUCCESS, job_utilization__duration__gt=timedelta(seconds=0)
    ).aggregate(
        total_job_duration=Sum("job_utilization__duration"),
        job_count=Count("pk", distinct=True),
    )

    if all(aggregates.values()):
        phase.average_algorithm_job_duration = (
            aggregates["total_job_duration"] / aggregates["job_count"]
        )
    else:
        phase.average_algorithm_job_duration = None
