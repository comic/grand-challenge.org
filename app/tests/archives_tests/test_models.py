import pytest
from django.db import IntegrityError, transaction

from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import ComponentInterfaceValueFactory


@pytest.mark.django_db
def test_str():
    model = ArchiveFactory()
    assert str(model) == f"{model.title}"


def create_archive_items_for_images(images, archive):
    for image in images:
        civ = ComponentInterfaceValueFactory(image=image)
        ai = ArchiveItemFactory(archive=archive)
        ai.values.add(civ)


@pytest.mark.django_db
def test_archive_item_set_title():
    archive = ArchiveFactory()
    ai0 = ArchiveItemFactory(archive=archive)

    # Default
    assert ai0.title == ""

    # Update
    ai0.title = "An archive item title"
    ai0.save()

    # Sanity
    ai1 = ArchiveItemFactory(
        archive=ai0.archive,
        title="Another archive item title",
    )

    # Duplication attempt via edit
    ai1.title = ai0.title
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            ai1.save()

    # Duplication attempt via save
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            ArchiveItemFactory(
                archive=archive,
                title=ai1.title,
            )

    # Other archive no problem
    ArchiveItemFactory(
        archive=ArchiveFactory(),
        title=ai0.title,
    )
