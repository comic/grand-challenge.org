import sys
import tempfile
from io import BytesIO
from pathlib import Path

import SimpleITK as Sitk
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile

from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study

TEMP_SAVE_LOCATION = "tmp.mha"


def create_archive(name, user):
    a = Archive.objects.get_or_create(title=name)[0]
    a.add_editor(user)
    return a


def load_as_bytes_io(fp):
    """
    Load file in filepath (fp) to BytesIO object
    :param fp: filepath
    :return: BytesIO object
    """
    fh = open(fp, "rb")
    bio = BytesIO()
    bio.name = fh.name
    bio.write(fh.read())
    fh.close()
    bio.seek(0)
    return bio


def create_image_set_for_study(archive, study):
    image_set = {
        "oct16bit": [
            {
                "sitk_image": Sitk.Image([256, 128, 128], Sitk.sitkUInt16),
                "modality": ImagingModality.objects.get_or_create(
                    modality="OCT"
                )[0],
                "color_space": Image.COLOR_SPACE_GRAY,
            }
            for _ in range(2)
        ],
        "oct8bit": [
            {
                "sitk_image": Sitk.Image([256, 128, 128], Sitk.sitkUInt8),
                "modality": ImagingModality.objects.get_or_create(
                    modality="OCT"
                )[0],
                "color_space": Image.COLOR_SPACE_GRAY,
            }
            for _ in range(2)
        ],
        "enface_rgb": [
            {
                "sitk_image": Sitk.Image(
                    [1024, 1024], Sitk.sitkVectorUInt8, 3
                ),
                "modality": ImagingModality.objects.get_or_create(
                    modality="Fundus Photography"
                )[0],
                "color_space": Image.COLOR_SPACE_RGB,
            }
            for _ in range(5)
        ],
        "enface_grey": [
            {
                "sitk_image": Sitk.Image([1024, 1024], Sitk.sitkUInt8),
                "modality": ImagingModality.objects.get_or_create(
                    modality="Infrared Reflectance Imaging"
                )[0],
                "color_space": Image.COLOR_SPACE_GRAY,
            }
            for _ in range(5)
        ],
    }
    for name, images in image_set.items():
        for index, image_dict in enumerate(images):
            image = Image.objects.create(
                name=f"{name} {index}",
                study=study,
                modality=image_dict["modality"],
                width=image_dict["sitk_image"].GetWidth(),
                height=image_dict["sitk_image"].GetHeight(),
                depth=image_dict["sitk_image"].GetDepth(),
                color_space=image_dict["color_space"],
                eye_choice=Image.EYE_CHOICES[index % len(Image.EYE_CHOICES)][
                    0
                ],
                stereoscopic_choice=Image.STEREOSCOPIC_CHOICES[
                    index % len(Image.STEREOSCOPIC_CHOICES)
                ][0]
                if "enface" in name
                else Image.STEREOSCOPIC_EMPTY,
                field_of_view=Image.FOV_CHOICES[
                    index % len(Image.FOV_CHOICES)
                ][0]
                if name == "enface_rgb"
                else Image.FOV_EMPTY,
            )

            mha_bio = None
            with tempfile.TemporaryDirectory() as dirname:
                file = Path(dirname, "tmp.mha")
                Sitk.WriteImage(image_dict["sitk_image"], str(file), True)
                mha_bio = load_as_bytes_io(file)

            file = InMemoryUploadedFile(
                mha_bio,
                "ImageField",
                "test.mha",
                "application/octet-stream",
                None,
                sys.getsizeof(mha_bio),
            )

            image_file = ImageFile.objects.create(
                image=image, image_type=ImageFile.IMAGE_TYPE_MHD,
            )
            image_file.file.save(f"{image_file.pk}.mha", file, save=True)

            # Link images to archive
            interface = ComponentInterface.objects.get(
                slug="generic-medical-image"
            )
            civ = ComponentInterfaceValue.objects.get_or_create(
                interface=interface, image=image
            )[0]
            item = ArchiveItem.objects.create(archive=archive)
            item.values.set([civ])


def create_archive_patient_study_structure(
    user, num_archives, num_patients, num_studies
):
    archive_structure_dict = {}
    for a in range(num_archives):
        archive = create_archive(f"Archive {a}", user)
        patients = {}
        for p in range(num_patients):
            patient = Patient.objects.get_or_create(name=f"Patient {p}")[0]
            studies = []
            for s in range(num_studies):
                study = Study.objects.get_or_create(
                    name=f"Study {s}", patient=patient
                )[0]
                create_image_set_for_study(archive, study)
                studies.append(study)
                print(
                    f"A={a}/{num_archives} P={p}/{num_patients} S={s}/{num_studies}"
                )

            patients[patient.name] = {
                "patient": patient,
                "studies": studies,
            }
        archive_structure_dict[archive.title] = {
            "archive": archive,
            "patients": patients,
        }
    return archive_structure_dict


def run():
    user = get_user_model().objects.get(username="retina")
    create_archive_patient_study_structure(user, 1, 1, 1)
