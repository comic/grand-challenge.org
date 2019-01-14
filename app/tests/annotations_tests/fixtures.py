import pytest
from typing import NamedTuple
from tests.factories import UserFactory, ImageFactory
from tests.annotations_tests.factories import (
    MeasurementAnnotationFactory,
    BooleanClassificationAnnotationFactory,
    PolygonAnnotationSetFactory,
    CoordinateListAnnotationFactory,
    LandmarkAnnotationSetFactory,
    ETDRSGridAnnotationFactory,
    SingleLandmarkAnnotationFactory,
    SinglePolygonAnnotationFactory,
)


class AnnotationSet(NamedTuple):
    grader: UserFactory
    measurement: MeasurementAnnotationFactory
    boolean: BooleanClassificationAnnotationFactory
    polygon: PolygonAnnotationSetFactory
    coordinatelist: CoordinateListAnnotationFactory
    landmark: LandmarkAnnotationSetFactory
    etdrs: ETDRSGridAnnotationFactory


def generate_annotation_set():
    grader = UserFactory()
    measurement = MeasurementAnnotationFactory(grader=grader)
    boolean = BooleanClassificationAnnotationFactory(grader=grader)
    polygon = PolygonAnnotationSetFactory(grader=grader)
    coordinatelist = CoordinateListAnnotationFactory(grader=grader)
    landmark = LandmarkAnnotationSetFactory(grader=grader)
    etdrs = ETDRSGridAnnotationFactory(grader=grader)

    # Create child models for polygon annotation set
    for i in range(10):
        SinglePolygonAnnotationFactory(annotation_set=polygon)

    # Create child models for landmark annotation set (3 per image)
    for i in range(5):
        image = ImageFactory()
        for j in range(3):
            SingleLandmarkAnnotationFactory(annotation_set=landmark, image=image)

    return AnnotationSet(
        grader=grader,
        measurement=measurement,
        boolean=boolean,
        polygon=polygon,
        coordinatelist=coordinatelist,
        etdrs=etdrs
    )


@pytest.fixture(name="AnnotationSet")
def annotation_set():
    """TODO"""
    return generate_annotation_set()
