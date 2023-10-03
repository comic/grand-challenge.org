from django.db.models import Sum

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.cases.models import ImageFile
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.evaluation.models import Evaluation, Method


def annotate_compute_costs_and_storage_size(*, challenge):
    algorithm_jobs = get_algorithm_jobs_for_challenge(challenge=challenge)
    evaluation_jobs = get_evaluation_jobs_for_challenge(challenge=challenge)

    update_size_in_storage_and_registry(
        challenge=challenge,
        algorithm_jobs=algorithm_jobs,
        evaluation_jobs=evaluation_jobs,
    )
    update_compute_cost_euro_millicents(
        challenge=challenge,
        algorithm_jobs=algorithm_jobs,
        evaluation_jobs=evaluation_jobs,
    )


def get_algorithm_jobs_for_challenge(*, challenge):
    return Job.objects.filter(
        inputs__archive_items__archive__phase__challenge=challenge
    ).distinct()


def get_evaluation_jobs_for_challenge(*, challenge):
    return Evaluation.objects.filter(
        submission__phase__challenge=challenge
    ).distinct()


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

    method_storage = (
        Method.objects.filter(phase__challenge=challenge)
        .distinct()
        .aggregate(Sum("size_in_storage"), Sum("size_in_registry"))
    )

    items = [
        archive_image_storage,
        archive_file_storage,
        output_image_storage,
        output_file_storage,
        algorithm_storage,
        method_storage,
    ]

    challenge.size_in_storage = sum(
        item["size_in_storage__sum"] or 0 for item in items
    )
    challenge.size_in_registry = sum(
        item.get("size_in_registry__sum") or 0 for item in items
    )


def update_compute_cost_euro_millicents(
    *, challenge, algorithm_jobs, evaluation_jobs
):
    algorithm_job_costs = algorithm_jobs.aggregate(
        Sum("compute_cost_euro_millicents")
    )

    evaluation_costs = evaluation_jobs.aggregate(
        Sum("compute_cost_euro_millicents")
    )

    items = [algorithm_job_costs, evaluation_costs]

    challenge.compute_cost_euro_millicents = sum(
        item["compute_cost_euro_millicents__sum"] or 0 for item in items
    )
