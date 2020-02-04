from celery import shared_task
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.archives.models import Archive
from grandchallenge.patients.models import Patient
from grandchallenge.retina_api.models import ArchiveDataModel


@shared_task
def cache_archive_data():
    archive_data = create_archive_data_object()
    ArchiveDataModel.objects.update_or_create(
        pk=1, defaults={"value": archive_data},
    )


def create_archive_data_object():
    archives = Archive.objects.all()
    patients = Patient.objects.prefetch_related(
        "study_set",
        "study_set__image_set",
        "study_set__image_set__modality",
        "study_set__image_set__obs_image",
        "study_set__image_set__oct_image",
        "study_set__image_set__archive_set",
    )

    return {
        "subfolders": dict(generate_archives(archives, patients)),
        "info": "level 2",
        "name": "Archives",
        "id": "none",
        "images": {},
    }


def generate_archives(archive_list, patients):
    for archive in archive_list:
        if archive.name == "kappadata":
            subfolders = {}
            images = dict(generate_images(archive.images))
        else:
            subfolders = dict(generate_patients(archive, patients))
            images = {}

        yield archive.name, {
            "subfolders": subfolders,
            "info": "level 3",
            "name": archive.name,
            "id": archive.id,
            "images": images,
        }


def generate_patients(archive, patients):
    patient_list = patients.filter(study__image__archive=archive).distinct()
    for patient in patient_list:
        if archive.name == settings.RETINA_EXCEPTION_ARCHIVE:
            image_set = {}
            for study in patient.study_set.all():
                image_set.update(dict(generate_images(study.image_set)))
            yield patient.name, {
                "subfolders": {},
                "info": "level 4",
                "name": patient.name,
                "id": patient.id,
                "images": image_set,
            }
        else:
            yield patient.name, {
                "subfolders": dict(generate_studies(patient.study_set)),
                "info": "level 4",
                "name": patient.name,
                "id": patient.id,
                "images": {},
            }


def generate_studies(study_list):
    for study in study_list.all():
        yield study.name, {
            "info": "level 5",
            "images": dict(generate_images(study.image_set)),
            "name": study.name,
            "id": study.id,
            "subfolders": {},
        }


def generate_images(image_list):
    for image in image_list.all():
        if image.modality.modality == settings.MODALITY_OCT:
            # oct image add info
            obs_image_id = "no info"
            try:
                oct_obs_registration = image.oct_image.get()
                obs_image_id = oct_obs_registration.obs_image.id
                obs_list = oct_obs_registration.registration_values
                obs_registration_flat = [
                    val for sublist in obs_list for val in sublist
                ]
            except ObjectDoesNotExist:
                obs_registration_flat = []

            # leave voxel_size always empty because this info is in mhd file
            voxel_size = [0, 0, 0]
            study_datetime = "Unknown"
            if image.study.datetime:
                study_datetime = image.study.datetime.strftime(
                    "%Y/%m/%d %H:%M:%S"
                )

            yield image.name, {
                "images": {
                    "trc_000": "no info",
                    "obs_000": obs_image_id,
                    "mot_comp": "no info",
                    "trc_001": "no info",
                    "oct": image.id,
                },
                "info": {
                    "voxel_size": {
                        "axial": voxel_size[0],
                        "lateral": voxel_size[1],
                        "transversal": voxel_size[2],
                    },
                    "date": study_datetime,
                    "registration": {
                        "obs": obs_registration_flat,
                        "trc": [0, 0, 0, 0],
                    },
                },
            }
        elif (
            image.modality.modality == settings.MODALITY_CF
            and image.name.endswith(".fds")
        ):
            # OBS image, skip because this is already in fds
            pass
        else:
            yield image.name, image.id
