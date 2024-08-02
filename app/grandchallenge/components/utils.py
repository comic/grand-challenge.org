from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.uploads.models import UserUpload


def retrieve_existing_civs(*, civ_data):
    """
    Checks if there are existing CIVs for the provided inputs and if so, returns those.

    Parameters
    ----------
    civ_data
        A dictionary with interface slugs as keys and CIV values as values.

    Returns
    -------
    A list of ComponentInterfaceValues

    """
    existing_civs = []
    for interface, value in civ_data.items():
        if isinstance(value, ComponentInterfaceValue):
            existing_civs.append(value)
        elif isinstance(value, Image):
            ci = ComponentInterface.objects.get(slug=interface)
            try:
                civ = ComponentInterfaceValue.objects.filter(
                    interface=ci, image=value
                ).get()
                existing_civs.append(civ)
            except ObjectDoesNotExist:
                continue
        elif isinstance(value, (RawImageUploadSession, UserUpload, QuerySet)):
            # uploads will create new CIVs, so ignore these
            continue
        else:
            # values can be of different types
            ci = ComponentInterface.objects.get(slug=interface)
            try:
                civ = ComponentInterfaceValue.objects.filter(
                    interface=ci, value=value
                ).get()
                existing_civs.append(civ)
            except ObjectDoesNotExist:
                continue

    return existing_civs


def reformat_inputs(*, serialized_civs):
    """
    Takes serialized CIV data and turns it into a dictionary:
    {
        "interface_slug_1": "value",
        "interface_slug_2": "value_2"
    }
    This representation of CIV data corresponds to how CIV data is stored in
    a form's cleaned_data.
    """
    possible_keys = ["image", "value", "file", "user_upload", "upload_session"]
    data = {}
    for civ in serialized_civs:
        interface_slug = civ["interface"].slug
        for key in possible_keys:
            if key in civ:
                data[interface_slug] = civ[key]
                break
    return data
