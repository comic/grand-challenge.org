from django.contrib.auth import get_user_model
from django.db import transaction
from guardian.shortcuts import assign_perm

from grandchallenge.cases.models import DICOMImageSet, Image


@transaction.atomic
def run():
    user = get_user_model().objects.get(username="demop")

    data = {
        # TODO fill in
    }

    for pk, image_set_id in data.items():
        im, created = Image.objects.get_or_create(pk=pk)

        if created:
            im.dicom_image_set = DICOMImageSet.objects.create(
                image_set_id=image_set_id
            )
            im.save()

        assign_perm("view_image", user, im)
