import os
from contextlib import contextmanager

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.evaluation.models import Method
from grandchallenge.workstations.models import Workstation
from tests.fixtures import create_uploaded_image


def run():
    print("👷 Creating Algorithm Evaluation Fixtures")

    users = _get_users()
    inputs = _get_inputs()
    outputs = _get_outputs()
    suffix = Challenge.objects.count()
    archive = _create_archive(
        creator=users["demo"], interfaces=inputs, suffix=suffix
    )
    _create_challenge(
        creator=users["demo"],
        participant=users["demop"],
        archive=archive,
        suffix=suffix,
        inputs=inputs,
        outputs=outputs,
    )
    _create_algorithm(
        creator=users["demop"], inputs=inputs, outputs=outputs, suffix=suffix
    )


def _get_users():
    users = get_user_model().objects.filter(username__in=["demo", "demop"])
    return {u.username: u for u in users}


def _get_inputs():
    return ComponentInterface.objects.filter(
        slug__in=["generic-medical-image"]
    )


def _get_outputs():
    return ComponentInterface.objects.filter(
        slug__in=["generic-medical-image", "results-json-file"]
    )


def _create_archive(*, creator, interfaces, suffix, items=5):
    a = Archive.objects.create(
        title=f"Algorithm Evaluation {suffix} Test Set",
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
                name=f"Test Image {n}", width=10, height=10,
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
    *, creator, participant, archive, suffix, inputs, outputs
):
    c = Challenge.objects.create(
        short_name=f"algorithm-evaluation-{suffix}",
        creator=creator,
        hidden=False,
        logo=create_uploaded_image(),
    )
    c.add_participant(participant)

    p = c.phase_set.first()

    p.algorithm_inputs.set(inputs)
    p.algorithm_outputs.set(outputs)

    p.title = "Algorithm Evaluation"
    p.submission_kind = p.SubmissionKind.ALGORITHM
    p.archive = archive
    p.score_jsonpath = "score"
    p.save()

    m = Method(creator=creator, phase=p)

    with _uploaded_container_image() as container:
        m.image.save("algorithm_io.tar", container)


def _create_algorithm(*, creator, inputs, outputs, suffix):
    algorithm = Algorithm.objects.create(
        title=f"Test Algorithm Evaluation {suffix}",
        logo=create_uploaded_image(),
        use_flexible_inputs=True,
    )
    algorithm.inputs.set(inputs)
    algorithm.outputs.set(outputs)
    algorithm.add_editor(creator)

    algorithm_image = AlgorithmImage(creator=creator, algorithm=algorithm)

    with _uploaded_container_image() as container:
        algorithm_image.image.save("algorithm_io.tar", container)


@contextmanager
def _uploaded_container_image():
    path = "scripts/algorithm_io.tar"
    yield from _uploaded_file(path=path)


@contextmanager
def _uploaded_image_file():
    path = "scripts/image10x10x10.mha"
    yield from _uploaded_file(path=path)


def _uploaded_file(*, path):
    with open(os.path.join(settings.SITE_ROOT, path), "rb",) as f:
        with ContentFile(f.read()) as content:
            yield content
