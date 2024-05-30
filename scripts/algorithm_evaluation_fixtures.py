import gzip
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.challenges.models import Challenge
from grandchallenge.components.backends import docker_client
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKindChoices,
)
from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.evaluation.models import Evaluation, Method, Phase
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

    _create_civ_rich_algorithm_job(
        creator=users["demo"],
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
            settings.SITE_ROOT / "tests" / "resources" / "gc_demo_algorithm"
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


def _create_civ_rich_algorithm_job(creator):
    interfaces = _get_or_create_additional_component_interfaces()

    algorithm_job = Job.objects.create(
        creator=creator,
        algorithm_image=AlgorithmImage.objects.filter(creator=creator).first(),
        status=Evaluation.SUCCESS,
    )

    # String
    algorithm_job.inputs.add(
        interfaces["string-ci"].create_instance(
            value="Lorem inputsum dolor sit amet, consectetur adipiscing elit, sed do"
        )
    )

    algorithm_job.outputs.add(
        interfaces["string-ci"].create_instance(
            value="Lorem outputsum dolor sit amet, consectetur adipiscing elit, sed do"
        )
    )

    # Value float
    algorithm_job.inputs.add(
        interfaces["value-float-ci"].create_instance(value=42)
    )

    algorithm_job.outputs.add(
        interfaces["value-float-ci"].create_instance(value=43)
    )

    # File float
    ffc_in = ComponentInterfaceValue.objects.create(
        interface=interfaces["file-float-ci"],
    )
    ffc_in.file.save(
        "float_file_name.json", ContentFile(json.dumps(42).encode("utf-8"))
    )
    algorithm_job.inputs.add(ffc_in)

    ffc_out = ComponentInterfaceValue.objects.create(
        interface=interfaces["file-float-ci"],
    )
    ffc_out.file.save(
        "float_file_name.json", ContentFile(json.dumps(43).encode("utf-8"))
    )
    algorithm_job.outputs.add(ffc_out)

    # Chart
    with open(
        settings.SITE_ROOT / "tests" / "resources" / "bar_chart.json"
    ) as f:
        chart_spec = json.loads(f.read())
        algorithm_job.inputs.add(
            interfaces["chart-ci"].create_instance(value=chart_spec)
        )
        algorithm_job.outputs.add(
            interfaces["chart-ci"].create_instance(value=chart_spec)
        )

    # Thumbnail
    thumb_in = ComponentInterfaceValue.objects.create(
        interface=interfaces["thumbnail-jpg-ci"],
    )
    thumb_in.file.save("thumbnail_image_name.jpg", create_uploaded_image())
    algorithm_job.inputs.add(thumb_in)

    thumb_out = ComponentInterfaceValue.objects.create(
        interface=interfaces["thumbnail-jpg-ci"],
    )
    thumb_out.file.save("thumbnail_image_name.jpg", create_uploaded_image())
    algorithm_job.outputs.add(thumb_out)


def _get_or_create_additional_component_interfaces():
    interfaces = [
        {
            "title": "Chart CI",
            "kind": InterfaceKindChoices.CHART,
            "store_in_database": True,
            "relative_path": "chart.json",
        },
        {
            "title": "Thumbnail JPG CI",
            "kind": InterfaceKindChoices.THUMBNAIL_JPG,
            "store_in_database": False,
            "relative_path": "images/thumbnail.jpg",
        },
        {
            "title": "File Float CI",
            "kind": InterfaceKindChoices.FLOAT,
            "store_in_database": False,
            "relative_path": "float.json",
        },
        {
            "title": "Value Float CI",
            "kind": InterfaceKindChoices.FLOAT,
            "store_in_database": True,
            "relative_path": "float_value.json",
        },
        {
            "title": "String CI",
            "kind": InterfaceKindChoices.STRING,
            "store_in_database": True,
            "relative_path": "string.json",
        },
    ]

    return {
        i.slug: i
        for i in [
            ComponentInterface.objects.get_or_create(**kwargs)[0]
            for kwargs in interfaces
        ]
    }
