from django.contrib.auth import get_user_model
from django.db import transaction
from guardian.shortcuts import assign_perm

from grandchallenge.cases.models import DICOMImageSet, Image


@transaction.atomic
def run():
    user = get_user_model().objects.get(username="demop")

    images = {
        # TODO fill in
    }

    for image in images:
        im, created = Image.objects.get_or_create(pk=image["pk"])

        if created:
            im.dicom_image_set = DICOMImageSet.objects.create(
                image_set_id=image["dicom_image_set"]["image_set_id"],
                image_frame_ids=image["dicom_image_set"]["image_frame_ids"],
            )
            im.save()

        assign_perm("view_image", user, im)
