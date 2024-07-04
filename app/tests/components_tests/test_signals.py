import pytest

from grandchallenge.algorithms.models import AlgorithmImage, AlgorithmModel
from grandchallenge.core.storage import (
    private_s3_storage,
    protected_s3_storage,
)
from grandchallenge.evaluation.models import EvaluationGroundTruth, Method
from grandchallenge.workstations.models import WorkstationImage
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmModelFactory,
)
from tests.evaluation_tests.factories import (
    EvaluationGroundTruthFactory,
    MethodFactory,
)
from tests.factories import WorkstationImageFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory, lookup, object_class, storage",
    [
        (AlgorithmImageFactory, "image", AlgorithmImage, protected_s3_storage),
        (AlgorithmModelFactory, "model", AlgorithmModel, protected_s3_storage),
        (MethodFactory, "image", Method, private_s3_storage),
        (
            EvaluationGroundTruthFactory,
            "ground_truth",
            EvaluationGroundTruth,
            private_s3_storage,
        ),
        (
            WorkstationImageFactory,
            "image",
            WorkstationImage,
            private_s3_storage,
        ),
    ],
)
def test_delete_linked_file(
    algorithm_io_image, factory, lookup, object_class, storage
):
    factory.create_batch(2, **{f"{lookup}__from_path": algorithm_io_image})
    file_names = []
    for obj in object_class.objects.all():
        assert obj.linked_file.file is not None
        file_names.append(obj.linked_file.file.name)
        assert storage.exists(obj.linked_file.file.name)

    object_class.objects.all().delete()
    assert object_class.objects.count() == 0
    for file_name in file_names:
        assert not storage.exists(file_name)
