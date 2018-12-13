import random
import factory
from grandchallenge.retina_images.models import RetinaImage
from tests.studies_tests.factories import StudyFactory


class RetinaImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = RetinaImage

    name = factory.Sequence(lambda n: "RetinaImage {}".format(n))
    image = factory.SubFactory(ImageFactoryWithImageFile)
    study = factory.SubFactory(StudyFactory)
    modality = factory.Iterator([x[0] for x in RetinaImage.MODALITY_CHOICES])
    eye_choice = factory.Iterator(
        [x[0] for x in RetinaImage.EYE_CHOICES]
    )
    voxel_size = [
        random.uniform(0.0, 500.0),
        random.uniform(0.0, 500.0),
        random.uniform(0.0, 500.0),
    ]


