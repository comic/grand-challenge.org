import pytest
from django.core.management import call_command

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.components.models import ComponentInterfaceValue
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory


@pytest.mark.django_db
def test_remove_duplicate_civs():
    images = [ImageFactory() for x in range(3)]
    cis = [ComponentInterfaceFactory() for x in range(3)]
    archive = ArchiveFactory()

    for im in images:
        for ci in cis:
            n = 1 if images.index(im) == 0 and cis.index(ci) == 0 else 3
            for _ in range(n):
                civ = ComponentInterfaceValueFactory(interface=ci, image=im)
                ai = ArchiveItemFactory(archive=archive)
                ai.values.add(civ)
            assert (
                ComponentInterfaceValue.objects.filter(
                    interface=ci, image=im
                ).count()
                == n
            )
            assert (
                ArchiveItem.objects.filter(
                    values__image=im, values__interface=ci
                ).count()
                == n
            )

    call_command("remove_duplicate_civs")
    for im in images:
        for ci in cis:
            n = 1 if images.index(im) == 0 and cis.index(ci) == 0 else 3
            assert (
                ComponentInterfaceValue.objects.filter(
                    interface=ci, image=im
                ).count()
                == 1
            )
            assert (
                ArchiveItem.objects.filter(
                    values__image=im, values__interface=ci
                ).count()
                == n
            )
