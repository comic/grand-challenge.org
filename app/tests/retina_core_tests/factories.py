from django.conf import settings

from tests.archives_tests.factories import ArchiveFactory
from tests.cases_tests.factories import ImageFactoryWithImageFile
from tests.patients_tests.factories import PatientFactory
from tests.studies_tests.factories import StudyFactory


def create_some_datastructure_data(archive_pars=None,):
    patient_pars = {}
    study_pars = {}
    image_cf_pars = {}
    oct_study_pars = {}
    image_obs_pars = {}
    image_oct_pars = {}

    if archive_pars is None:
        archive_pars = {}

    # Create datastructures
    patient = PatientFactory(**patient_pars)
    study = StudyFactory(patient=patient, **study_pars)
    image_cf = ImageFactoryWithImageFile(
        study=study, modality__modality=settings.MODALITY_CF, **image_cf_pars
    )
    study_oct = StudyFactory(patient=patient, **oct_study_pars)
    # oct/obs image name has to end with OCT.fds for obs image recognition
    oct_obs_fake_name = "OBS_OCT.fds"
    image_obs = ImageFactoryWithImageFile(
        study=study_oct,
        modality__modality=settings.MODALITY_CF,
        name=oct_obs_fake_name,
        **image_obs_pars,
    )
    image_oct = ImageFactoryWithImageFile(
        study=study_oct,
        modality__modality=settings.MODALITY_OCT,
        name=oct_obs_fake_name,  # OCT image name has to be equal to OBS image name
        **image_oct_pars,
    )
    archive = ArchiveFactory.create(
        images=(image_oct, image_cf, image_obs), **archive_pars
    )
    return {
        "archive": archive,
        "patient": patient,
        "study": study,
        "image_cf": image_cf,
        "study_oct": study_oct,
        "image_obs": image_obs,
        "image_oct": image_oct,
    }
