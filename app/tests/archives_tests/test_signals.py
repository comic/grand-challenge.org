import pytest

from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.evaluation_tests.test_permissions import get_groups_with_set_perms
from tests.factories import ImageFactory


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_archive_item_permissions_signal(reverse):
    ai1, ai2 = ArchiveItemFactory.create_batch(2)
    im1, im2, im3, im4 = ImageFactory.create_batch(4)

    civ1, civ2, civ3, civ4 = (
        ComponentInterfaceValueFactory(image=im1),
        ComponentInterfaceValueFactory(image=im2),
        ComponentInterfaceValueFactory(image=im3),
        ComponentInterfaceValueFactory(image=im4),
    )

    if reverse:
        for civ in [civ1, civ2, civ3, civ4]:
            civ.archive_items.add(ai1, ai2)
        for civ in [civ3, civ4]:
            civ.archive_items.remove(ai1, ai2)
        for civ in [civ1, civ2]:
            civ.archive_items.remove(ai2)
    else:
        # Test that adding images works
        ai1.values.add(civ1, civ2, civ3, civ4)
        # Test that removing images works
        ai1.values.remove(civ3, civ4)

    assert get_groups_with_set_perms(im1) == {
        ai1.archive.editors_group: {"view_image"},
        ai1.archive.uploaders_group: {"view_image"},
        ai1.archive.users_group: {"view_image"},
    }
    assert get_groups_with_set_perms(im2) == {
        ai1.archive.editors_group: {"view_image"},
        ai1.archive.uploaders_group: {"view_image"},
        ai1.archive.users_group: {"view_image"},
    }
    assert get_groups_with_set_perms(im3) == {}
    assert get_groups_with_set_perms(im4) == {}

    # Test clearing
    if reverse:
        civ1.archive_items.clear()
        civ2.archive_items.clear()
    else:
        ai1.values.clear()

    assert get_groups_with_set_perms(im1) == {}
    assert get_groups_with_set_perms(im2) == {}


@pytest.mark.django_db
def test_deleting_archive_item_removes_permissions():
    ai1, ai2 = ArchiveItemFactory.create_batch(2)
    im = ImageFactory()
    civ = ComponentInterfaceValueFactory(image=im)

    ai1.values.set([civ])
    ai2.values.set([civ])

    assert get_groups_with_set_perms(im) == {
        ai1.archive.editors_group: {"view_image"},
        ai1.archive.uploaders_group: {"view_image"},
        ai1.archive.users_group: {"view_image"},
        ai2.archive.editors_group: {"view_image"},
        ai2.archive.uploaders_group: {"view_image"},
        ai2.archive.users_group: {"view_image"},
    }

    ai1.delete()

    assert get_groups_with_set_perms(im) == {
        ai2.archive.editors_group: {"view_image"},
        ai2.archive.uploaders_group: {"view_image"},
        ai2.archive.users_group: {"view_image"},
    }


@pytest.mark.django_db
def test_changing_archive_updates_permissions():
    ai = ArchiveItemFactory()
    im = ImageFactory()
    civ = ComponentInterfaceValueFactory(image=im)

    ai.values.set([civ])

    assert get_groups_with_set_perms(im) == {
        ai.archive.editors_group: {"view_image"},
        ai.archive.uploaders_group: {"view_image"},
        ai.archive.users_group: {"view_image"},
    }

    a2 = ArchiveFactory()

    ai.archive = a2

    ai.save()

    assert get_groups_with_set_perms(im) == {
        a2.editors_group: {"view_image"},
        a2.uploaders_group: {"view_image"},
        a2.users_group: {"view_image"},
    }
