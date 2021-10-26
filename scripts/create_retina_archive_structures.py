import random
import string
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import SimpleITK as Sitk
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile

from config import settings
from grandchallenge.annotations.models import (
    LandmarkAnnotationSet,
    SingleLandmarkAnnotation,
)
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image, ImageFile
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.workstations.models import Workstation
from tests.fixtures import create_uploaded_image

TEMP_SAVE_LOCATION = "tmp.mha"


def create_archive(name, user):
    a = Archive.objects.get_or_create(
        title=name,
        defaults={
            "logo": create_uploaded_image(),
            "workstation": Workstation.objects.first(),
        },
    )[0]
    a.add_editor(user)
    return a


def generate_random_metadata():
    def generate_string(length=4):
        return "".join(
            random.choice(string.ascii_letters) for _ in range(length)
        )

    def generate_uid():
        return ".".join([str(random.randint(0, 100)) for _ in range(4)])

    def generate_lo(prefix="", suffix=""):
        rand_str = generate_string()
        return f"{prefix}{rand_str}{suffix}"

    def generate_da():
        return "-".join(
            [
                str(random.randint(t1, t2)).zfill(l)
                for t1, t2, l in ((1900, 2021, 4), (1, 12, 2), (1, 28, 2))
            ]
        )

    def generate_as():
        return str(random.randint(0, 999)).zfill(3) + random.choice(
            ("D", "W", "M", "Y")
        )

    def return_or_default(return_value, default=""):
        return return_value if random.random() < 0.5 else default

    return {
        "patient_name": return_or_default(generate_lo(prefix="Patient ")),
        "patient_birth_date": return_or_default(generate_da(), None),
        "patient_age": return_or_default(generate_as()),
        "patient_sex": return_or_default(random.choice(("F", "M", "O"))),
        "study_date": return_or_default(generate_da(), None),
        "study_instance_uid": return_or_default(generate_uid()),
        "series_instance_uid": return_or_default(generate_uid()),
        "series_description": return_or_default(generate_lo(prefix="Series ")),
    }


def generate_landmarks(img):
    def rand_x():
        return random.randint(0, img.width)

    def rand_y():
        return random.randint(0, img.height)

    return [[rand_x(), rand_y()], [rand_x(), rand_y()], [rand_x(), rand_y()]]


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


def create_image_set_for_study(archive, patient, study, nums):
    image_set = {
        "oct16bit": [
            {
                "sitk_image": Sitk.GaussianSource(
                    Sitk.sitkUInt16,
                    [256, 128, 128],
                    spacing=[0.25, 0.5, 0.5],
                    scale=2 ** 16 - 1,
                ),
                "modality": ImagingModality.objects.get_or_create(
                    modality="OCT"
                )[0],
                "color_space": Image.COLOR_SPACE_GRAY,
            }
            for _ in range(nums["oct16bit"])
        ],
        "oct8bit": [
            {
                "sitk_image": Sitk.GaussianSource(
                    Sitk.sitkUInt8, [256, 128, 128], spacing=[0.25, 0.5, 0.5]
                ),
                "modality": ImagingModality.objects.get_or_create(
                    modality="OCT"
                )[0],
                "color_space": Image.COLOR_SPACE_GRAY,
            }
            for _ in range(nums["oct8bit"])
        ],
        "enface_rgb": [
            {
                "sitk_image": (
                    Sitk.GetImageFromArray(
                        Sitk.GetArrayFromImage(
                            Sitk.GaussianSource(
                                Sitk.sitkUInt8,
                                [3, 128, 256],
                                spacing=[64 / 3, 0.5, 0.25],
                            )
                        ),
                        isVector=True,
                    )
                ),
                "modality": ImagingModality.objects.get_or_create(
                    modality="Fundus Photography"
                )[0],
                "color_space": Image.COLOR_SPACE_RGB,
            }
            for _ in range(nums["enface_rgb"])
        ],
        "enface_grey": [
            {
                "sitk_image": Sitk.GaussianSource(
                    Sitk.sitkUInt8, [1024, 1024], spacing=[0.0625, 0.0625]
                ),
                "modality": ImagingModality.objects.get_or_create(
                    modality="Infrared Reflectance Imaging"
                )[0],
                "color_space": Image.COLOR_SPACE_GRAY,
            }
            for _ in range(nums["enface_grey"])
        ],
    }
    created_images = []
    for name, images in image_set.items():
        for index, image_dict in enumerate(images):
            fields = {
                "name": f"{name} {index}",
                "patient_id": patient,
                "study_description": study,
            }
            if Image.objects.filter(
                **fields,
                componentinterfacevalue__archive_items__archive=archive,
            ).exists():
                continue

            image = Image.objects.create(
                **fields,
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
                **generate_random_metadata(),
            )
            created_images.append(image)

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

    return created_images


def create_landmark_annotations(user, images):
    images_2d = [i for i in images if i.depth in (1, None, 0)]
    annotations = []
    for i in range(len(images_2d) - 1):
        las = LandmarkAnnotationSet.objects.create(grader=user)
        for img_i in range(2):
            img = images_2d[img_i + i]
            SingleLandmarkAnnotation.objects.create(
                annotation_set=las,
                image=img,
                landmarks=generate_landmarks(img),
            )
        annotations.append(las)
    return annotations


def generate_images_and_annotations(
    user, nums, archive, patient, study, indentation="      "
):
    images = create_image_set_for_study(archive, patient, study, nums)
    print(f"{indentation}Created {len(images)} images.")
    annotations = create_landmark_annotations(user, images)
    print(f"{indentation}Created {len(annotations)} landmark annotations.")


def create_archive_patient_study_structure(user, nums):
    for a in range(nums["archives"]):
        archive = create_archive(f"Archive {a + 1}", user)
        print(archive.name)
        for p in range(nums["patients"]):
            patient = f"Patient {p + 1}"
            print(f"  {patient}")
            for s in range(nums["studies"]):
                study = f"Study {s + 1}"
                print(f"    {study}")
                generate_images_and_annotations(
                    user, nums, archive, patient, study
                )
            generate_images_and_annotations(
                user, nums, archive, patient, "", "    "
            )
        generate_images_and_annotations(user, nums, archive, "", "", "  ")


def remove_old_objects():
    LandmarkAnnotationSet.objects.all().delete()
    ArchiveItem.objects.all().delete()
    ComponentInterfaceValue.objects.all().delete()
    Image.objects.all().delete()
    Archive.objects.all().delete()


def run():
    if not settings.DEBUG:
        raise RuntimeError(
            "Skipping this command, server is not in DEBUG mode."
        )
    remove_old_objects()

    user = get_user_model().objects.get(username="retina")
    create_archive_patient_study_structure(
        user,
        nums={
            "archives": 3,
            "patients": 3,
            "studies": 3,
            "oct8bit": 2,
            "oct16bit": 2,
            "enface_rgb": 3,
            "enface_grey": 3,
        },
    )
