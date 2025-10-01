import json

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKindChoices,
)
from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.modalities.models import ImagingModality
from scripts.algorithm_evaluation_fixtures import _uploaded_image_file


def run():
    print("👷 Creating Component Interface Fixtures")
    user = get_user_model().objects.get(username="algorithm")
    interfaces = _get_or_create_component_interfaces()

    _create_civ_rich_algorithm_job(creator=user, interfaces=interfaces)


def _get_or_create_component_interfaces():
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
        {
            "title": "2D BB CI",
            "kind": InterfaceKindChoices.TWO_D_BOUNDING_BOX,
            "store_in_database": True,
            "relative_path": "2d_bb_ci.json",
        },
        {
            "title": "Broken Image CI",
            "kind": InterfaceKindChoices.PANIMG_IMAGE,
            "store_in_database": False,
            "relative_path": "images/broken-image",
        },
    ]

    return {
        i.slug: i
        for i in [
            ComponentInterface.objects.get_or_create(**kwargs)[0]
            for kwargs in interfaces
        ]
    }


def _create_civ_rich_algorithm_job(creator, interfaces):
    ai = AlgorithmImage.objects.filter(creator=creator).first()

    algorithm_job = Job.objects.create(
        creator=creator,
        algorithm_image=ai,
        status=Evaluation.SUCCESS,
        time_limit=ai.algorithm.time_limit,
        requires_gpu_type=ai.algorithm.job_requires_gpu_type,
        requires_memory_gb=ai.algorithm.job_requires_memory_gb,
    )

    chart_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "A simple bar chart with embedded data.",
        "data": {
            "values": [
                {"a": "A", "b": 28},
                {"a": "B", "b": 55},
                {"a": "C", "b": 43},
                {"a": "D", "b": 91},
                {"a": "E", "b": 81},
                {"a": "F", "b": 53},
                {"a": "G", "b": 19},
                {"a": "H", "b": 87},
                {"a": "I", "b": 52},
            ]
        },
        "mark": "bar",
        "encoding": {
            "x": {"field": "a", "type": "nominal", "axis": {"labelAngle": 0}},
            "y": {"field": "b", "type": "quantitative"},
        },
    }

    generic_image = ComponentInterface.objects.get(
        slug="generic-medical-image"
    )
    result_json = ComponentInterface.objects.get(slug="results-json-file")

    image = _create_image(
        name="test_image3.mha",
        modality=ImagingModality.objects.get(modality="MR"),
        width=128,
        height=128,
        color_space="RGB",
    )

    algorithm_job.inputs.add(
        # Generic image
        generic_image.create_instance(image=image),
        # A float
        interfaces["value-float-ci"].create_instance(value=42),
        # A float but in a file
        _create_file_ci_instance(
            interface=interfaces["file-float-ci"],
            name="float_file_name.input.json",
            content=ContentFile(json.dumps(42).encode("utf-8")),
        ),
        # A string, as value
        interfaces["string-ci"].create_instance(
            value="Lorem <b>inputsum</b> dolor sit amet, consectetur adipiscing elit, sed do"
        ),
        # Thumbnail image
        _create_file_ci_instance(
            interface=interfaces["thumbnail-jpg-ci"],
            name="thumbnail_image_name.input.jpg",
            content=create_uploaded_image(),
        ),
        # A chart
        interfaces["chart-ci"].create_instance(value=chart_spec),
        # Has no image
        ComponentInterfaceValue.objects.create(
            interface=interfaces["broken-image-ci"],
        ),
        # 2D bb
        interfaces["2d-bb-ci"].create_instance(
            value={
                "version": {"major": 1, "minor": 0},
                "type": "2D bounding box",
                "name": "output",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
                "probability": 0.2,
            }
        ),
    )

    algorithm_job.outputs.add(
        # Generic image
        generic_image.create_instance(image=image),
        # A float
        interfaces["value-float-ci"].create_instance(value=43),
        # A float but in a file
        _create_file_ci_instance(
            interface=interfaces["file-float-ci"],
            name="float_file_name.output.json",
            content=ContentFile(json.dumps(43).encode("utf-8")),
        ),
        # A string, as value
        interfaces["string-ci"].create_instance(
            value="Lorem <b>outputsum</b> dolor sit amet, consectetur adipiscing elit, sed do"
        ),
        # Thumbnail image
        _create_file_ci_instance(
            interface=interfaces["thumbnail-jpg-ci"],
            name="thumbnail_image_name.output.jpg",
            content=create_uploaded_image(),
        ),
        # A chart
        interfaces["chart-ci"].create_instance(value=chart_spec),
        # Broken: has no image
        ComponentInterfaceValue.objects.create(
            interface=interfaces["broken-image-ci"],
        ),
        # Results json
        result_json.create_instance(value={"score": 0.5}),
        # 2D bb
        interfaces["2d-bb-ci"].create_instance(
            value={
                "version": {"major": 1, "minor": 0},
                "type": "2D bounding box",
                "name": "output",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
                "probability": 0.2,
            }
        ),
    )


image_counter = 0


def _create_image(**kwargs):
    global image_counter

    im = Image.objects.create(**kwargs)
    im_file = ImageFile.objects.create(image=im)

    with _uploaded_image_file() as f:
        im_file.file.save(f"test_image_{image_counter}.mha", f)
        image_counter += 1
        im_file.save()

    return im


def _create_file_ci_instance(interface, name, content):
    v = ComponentInterfaceValue.objects.create(
        interface=interface,
    )
    v.file.save(name, content)

    return v
