import factory.fuzzy
import random
import datetime
import pytz
from grandchallenge.studies.models import Study
from grandchallenge.retina_images.models import RetinaImage
from tests.archives_tests.factories import ArchiveFactory
from tests.patients_tests.factories import PatientFactory


class StudyFactory(factory.DjangoModelFactory):
    class Meta:
        model = Study

    name = factory.Sequence(lambda n: "Study {}".format(n))
    patient = factory.SubFactory(PatientFactory)
    datetime = factory.fuzzy.FuzzyDateTime(
        datetime.datetime(1950, 1, 1, 0, 0, 0, 0, pytz.UTC)
    )
    # referring_physicians_name = factory.fuzzy.FuzzyText()
    # accession_number = factory.fuzzy.FuzzyText()


# class SeriesFactory(factory.DjangoModelFactory):
#     class Meta:
#         model = Series
#
#     identifier = factory.Sequence(lambda n: "Series {}".format(n))
#     study = factory.SubFactory(StudyFactory)
#     left_or_right_eye = factory.Iterator(
#         [x[0] for x in Series.LEFT_OR_RIGHT_EYE_CHOICES]
#     )
#     voxel_size = [
#         random.uniform(0.0, 500.0),
#         random.uniform(0.0, 500.0),
#         random.uniform(0.0, 500.0),
#     ]


class RetinaImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = RetinaImage

    name = factory.Sequence(lambda n: "RetinaImage {}".format(n))
    image = factory.django.ImageField()
    study = factory.SubFactory(StudyFactory)
    modality = factory.Iterator([x[0] for x in RetinaImage.MODALITY_CHOICES])
    number = factory.Sequence(lambda n: n)
    eye_choice = factory.Iterator(
        [x[0] for x in RetinaImage.EYE_CHOICES]
    )
    voxel_size = [
        random.uniform(0.0, 500.0),
        random.uniform(0.0, 500.0),
        random.uniform(0.0, 500.0),
    ]


def create_oct_series(**paremeters):
    study = StudyFactory(**paremeters)
    oct_slices = []
    for i in range(128):
        oct_slices.append(RetinaImageFactory(study=study, modality=RetinaImage.MODALITY_OCT, number=i))

    return study, oct_slices


def create_some_datastructure_data(
    archive_pars={},
    patient_pars={},
    study_pars={},
    image_cf_pars={},
    oct_study_pars={},
    image_obs_pars={},
):

    patient = PatientFactory(**patient_pars)
    study = StudyFactory(patient=patient, **study_pars)
    image_cf = RetinaImageFactory(study=study, modality=RetinaImage.MODALITY_CF, **image_cf_pars)
    study_oct, oct_slices = create_oct_series(patient=patient, **oct_study_pars)
    image_obs = RetinaImageFactory(study=study_oct, modality=RetinaImage.MODALITY_OBS, **image_obs_pars)
    archive = ArchiveFactory.create(images=(*oct_slices, image_cf, image_obs), **archive_pars)
    return {
        "archive": archive,
        "patient": patient,
        "study": study,
        "image_cf": image_cf,
        "study_oct": study_oct,
        "oct_slices": oct_slices,
        "image_obs": image_obs,
    }
