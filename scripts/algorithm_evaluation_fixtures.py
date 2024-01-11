import gzip
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.backends import docker_client
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.evaluation.models import Method, Phase
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import Invoice
from grandchallenge.workstations.models import Workstation


def run():
    print("👷 Creating Algorithm Evaluation Fixtures")

    users = _get_users()
    inputs = _get_inputs()
    outputs = _get_outputs()
    challenge_count = Challenge.objects.count()
    archive = _create_archive(
        creator=users["demo"], interfaces=inputs, suffix=challenge_count
    )
    _create_challenge(
        creator=users["demo"],
        participant=users["demop"],
        archive=archive,
        suffix=challenge_count,
        inputs=inputs,
        outputs=outputs,
    )
    _create_algorithm(
        creator=users["demop"],
        inputs=inputs,
        outputs=outputs,
        suffix=f"Image {challenge_count}",
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
    *, creator, participant, archive, suffix, inputs, outputs
):
    c = Challenge.objects.create(
        short_name=f"algorithm-evaluation-{suffix}",
        creator=creator,
        hidden=False,
        logo=create_uploaded_image(),
    )
    c.add_participant(participant)

    Invoice.objects.create(
        challenge=c,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=Invoice.PaymentStatusChoices.PAID,
    )

    p = Phase.objects.create(
        challenge=c, title="Phase 1", algorithm_time_limit=300
    )

    p.algorithm_inputs.set(inputs)
    p.algorithm_outputs.set(outputs)

    p.title = "Algorithm Evaluation"
    p.submission_kind = SubmissionKindChoices.ALGORITHM
    p.archive = archive
    p.score_jsonpath = "score"
    p.submissions_limit_per_user_per_period = 10
    p.save()

    m = Method(creator=creator, phase=p)

    with _gc_demo_algorithm() as container:
        m.image.save("algorithm_io.tar", container)


def _create_algorithm(*, creator, inputs, outputs, suffix):
    algorithm = Algorithm.objects.create(
        title=f"Test Algorithm Evaluation {suffix}",
        logo=create_uploaded_image(),
    )
    algorithm.inputs.set(inputs)
    algorithm.outputs.set(outputs)
    algorithm.add_editor(creator)

    algorithm_image = AlgorithmImage(creator=creator, algorithm=algorithm)

    with _gc_demo_algorithm() as container:
        algorithm_image.image.save("algorithm_io.tar", container)


@contextmanager
def _gc_demo_algorithm():
    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        repo_tag = "fixtures-algorithm-io:latest"
        demo_algorithm_path = (
            Path(__file__).parent.parent
            / "app"
            / "tests"
            / "resources"
            / "gc_demo_algorithm"
        )

        docker_client.build_image(
            path=str(demo_algorithm_path.absolute()), repo_tag=repo_tag
        )

        outfile = tmp_path / f"{repo_tag}.tar"
        output_gz = f"{outfile}.gz"

        docker_client.save_image(repo_tag=repo_tag, output=outfile)

        with open(outfile, "rb") as f_in:
            with gzip.open(output_gz, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        yield from _uploaded_file(path=output_gz)


@contextmanager
def _uploaded_image_file():
    path = Path(__file__).parent / "image10x10x10.mha"
    yield from _uploaded_file(path=path)


def _uploaded_file(*, path):
    with open(os.path.join(settings.SITE_ROOT, path), "rb") as f:
        with ContentFile(f.read()) as content:
            yield content
