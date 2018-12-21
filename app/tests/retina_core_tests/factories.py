from grandchallenge.challenges.models import ImagingModality
from tests.archives_tests.factories import ArchiveFactory
from tests.patients_tests.factories import PatientFactory
from tests.retina_images_tests.factories import ImageFactoryWithImageFile
from tests.studies_tests.factories import StudyFactory


def create_some_datastructure_data(
    archive_pars={},
    patient_pars={},
    study_pars={},
    image_cf_pars={},
    oct_study_pars={},
    image_obs_pars={},
    image_oct_pars={},
):
    # Create datastructures
    patient = PatientFactory(**patient_pars)
    study = StudyFactory(patient=patient, **study_pars)
    image_cf = ImageFactoryWithImageFile(
        study=study,
        modality__modality=ImagingModality.MODALITY_CF,
        **image_cf_pars,
    )
    study_oct = StudyFactory(patient=patient, **oct_study_pars)
    image_obs = ImageFactoryWithImageFile(
        study=study_oct,
        modality__modality=ImagingModality.MODALITY_CF,
        **image_obs_pars,
    )
    image_oct = ImageFactoryWithImageFile(
        study=study_oct,
        modality__modality=ImagingModality.MODALITY_OCT,
        name=image_obs.name,  # OCT image name has to be equal to OBS image name
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
