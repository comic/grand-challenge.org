from django.contrib.auth.models import Permission
from django.db.models import Sum

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
from grandchallenge.utilization.models import (
    EvaluationUtilization,
    JobUtilization,
    JobWarmPoolUtilization,
)


def annotate_compute_costs(*, challenge):
    algorithm_job_utilizations = JobUtilization.objects.filter(
        challenge=challenge
    )
    job_warm_pool_utilizations = JobWarmPoolUtilization.objects.filter(
        challenge=challenge
    )
    evaluation_job_utilizations = EvaluationUtilization.objects.filter(
        challenge=challenge
    )

    update_compute_cost_euro_millicents(
        obj=challenge,
        algorithm_job_utilizations=algorithm_job_utilizations,
        job_warm_pool_utilizations=job_warm_pool_utilizations,
        evaluation_job_utilizations=evaluation_job_utilizations,
    )


def annotate_job_duration_and_compute_costs(*, phase):
    algorithm_job_utilizations = JobUtilization.objects.filter(phase=phase)
    job_warm_pool_utilizations = JobWarmPoolUtilization.objects.filter(
        phase=phase
    )
    evaluation_job_utilizations = EvaluationUtilization.objects.filter(
        phase=phase, external_evaluation=False
    )

    phase.average_algorithm_job_duration = algorithm_job_utilizations.filter(
        job__status=Job.SUCCESS
    ).average_duration()

    update_compute_cost_euro_millicents(
        obj=phase,
        algorithm_job_utilizations=algorithm_job_utilizations,
        job_warm_pool_utilizations=job_warm_pool_utilizations,
        evaluation_job_utilizations=evaluation_job_utilizations,
    )


def update_compute_cost_euro_millicents(
    *,
    obj,
    algorithm_job_utilizations,
    job_warm_pool_utilizations,
    evaluation_job_utilizations,
):
    algorithm_job_costs = algorithm_job_utilizations.aggregate(
        Sum("compute_cost_euro_millicents")
    )
    job_warm_pool_costs = job_warm_pool_utilizations.aggregate(
        Sum("compute_cost_euro_millicents")
    )
    evaluation_costs = evaluation_job_utilizations.aggregate(
        Sum("compute_cost_euro_millicents")
    )

    items = [algorithm_job_costs, job_warm_pool_costs, evaluation_costs]

    obj.compute_cost_euro_millicents = sum(
        item["compute_cost_euro_millicents__sum"] or 0 for item in items
    )


def annotate_storage_size(*, challenge):
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
