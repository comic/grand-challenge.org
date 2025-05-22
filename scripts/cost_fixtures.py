import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmInterface,
    Job,
)
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.evaluation.models import (
    Evaluation,
    Method,
    Phase,
    Submission,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.workstations.models import Workstation
from scripts.algorithm_evaluation_fixtures import (
    _gc_demo_algorithm,
    _uploaded_image_file,
)


def run():
    print("Creating Cost Fixtures")

    users = _get_users()
    inputs = _get_inputs()
    outputs = _get_outputs()
    for i in range(4):
        archive = _create_archive(
            creator=users["demo"],
            interfaces=inputs,
            suffix=i,
            items=random.randint(3, 15),
        )
        challenge = _create_challenge(
            creator=users["demo"],
            participants=[users["demop"]],
            archive=archive,
            suffix=i,
            inputs=inputs,
            outputs=outputs,
        )
        for k in range(random.randint(2, 5)):
            algorithm = _create_algorithm(
                creator=users["demop"],
                inputs=inputs,
                outputs=outputs,
                suffix=f"Image {k}",
            )
            _create_submission(
                challenge=challenge,
                algorithm=algorithm,
                archive_items=archive.items.count(),
            )


def _get_users():
    users = get_user_model().objects.filter(username__in=["demo", "demop"])
    return {u.username: u for u in users}


def _get_inputs():
    return ComponentInterface.objects.filter(
        slug__in=["generic-medical-image"]
    )


def _get_json_file_inputs():
    return [
        ComponentInterface.objects.get_or_create(
            title="JSON File",
            relative_path="json-file",
            kind=ComponentInterface.Kind.ANY,
            store_in_database=False,
        )[0]
    ]


def _get_outputs():
    return ComponentInterface.objects.filter(slug__in=["results-json-file"])


def _create_archive(*, creator, interfaces, suffix, items):
    a = Archive.objects.create(
        title=f"Type 2 challenge {suffix} Test Set",
        logo=create_uploaded_image(),
        workstation=Workstation.objects.get(
            slug=settings.DEFAULT_WORKSTATION_SLUG
        ),
    )
    a.add_editor(creator)

    for n in range(items):
        ai = ArchiveItem.objects.create(archive=a)
        for interface in interfaces:
            v = ComponentInterfaceValue.objects.create(interface=interface)

            im = Image.objects.create(
                name=f"Test Image {n}", width=10, height=10
            )
            im_file = ImageFile.objects.create(image=im)

            with _uploaded_image_file() as f:
                im_file.file.save(f"test_image_{n}.mha", f)
                im_file.save()

            v.image = im
            v.save()

            ai.values.add(v)

    return a


def _create_challenge(
    *, creator, participants, archive, suffix, inputs, outputs
):
    c = Challenge.objects.create(
        short_name=f"type-2-{suffix}",
        creator=creator,
        hidden=False,
        logo=create_uploaded_image(),
    )
    for participant in participants:
        c.add_participant(participant)

    p = Phase.objects.create(challenge=c, title="Phase 1")
    interface = AlgorithmInterface.objects.create(
        inputs=inputs, outputs=outputs
    )
    p.algorithm_interfaces.set([interface])

    p.title = f"Type 2 {suffix}"
    p.submission_kind = SubmissionKindChoices.ALGORITHM
    p.archive = archive
    p.score_jsonpath = "score"
    p.submissions_limit_per_user_per_period = 10
    p.save()

    m = Method(creator=creator, phase=p)

    with _gc_demo_algorithm() as container:
        m.image.save("algorithm_io.tar", container)

    return c


def _create_algorithm(*, creator, inputs, outputs, suffix):
    algorithm = Algorithm.objects.create(
        title=f"Test Algorithm Type 2 {suffix}",
        logo=create_uploaded_image(),
    )
    interface = AlgorithmInterface.objects.create(
        inputs=inputs, outputs=outputs
    )
    algorithm.interfaces.set([interface])
    algorithm.add_editor(creator)

    algorithm_image = AlgorithmImage(creator=creator, algorithm=algorithm)

    with _gc_demo_algorithm() as container:
        algorithm_image.image.save("algorithm_io.tar", container)

    return algorithm


def _create_submission(algorithm, challenge, archive_items):
    ai = algorithm.algorithm_container_images.last()
    eval_inputs = []
    for _ in range(archive_items):
        job = Job.objects.create(
            algorithm_image=ai,
            algorithm_interface=algorithm.interfaces.first(),
            status=Job.SUCCESS,
            time_limit=ai.algorithm.time_limit,
            requires_gpu_type=ai.algorithm.job_requires_gpu_type,
            requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        )
        job.utilization.duration = timedelta(minutes=random.randint(5, 120))
        job.utilization.save()
        civ = ComponentInterfaceValue.objects.create(
            interface=ComponentInterface.objects.get(slug="results-json-file"),
        )
        civ.value = ({"foo": "bar"},)
        civ.save()
        eval_inputs.append(civ)
        job.outputs.add(civ)
    phase = challenge.phase_set.first()
    sub = Submission.objects.create(
        creator=algorithm.editors_group.user_set.get(),
        algorithm_image=ai,
        phase=phase,
    )
    e1 = Evaluation.objects.create(
        submission=sub,
        method=phase.method_set.last(),
        time_limit=sub.phase.evaluation_time_limit,
    )
    e1.inputs.add(*eval_inputs)
