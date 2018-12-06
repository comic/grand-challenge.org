from grandchallenge.retina_images.models import RetinaImage
from tests.archives_tests.factories import ArchiveFactory
from tests.patients_tests.factories import PatientFactory
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.studies_tests.factories import StudyFactory


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
