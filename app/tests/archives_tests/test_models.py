import pytest
from django.db import IntegrityError, transaction

from grandchallenge.archives.models import Archive
from tests.algorithms_tests.factories import AlgorithmInterfaceFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import UserFactory


@pytest.mark.django_db
def test_str():
    model = ArchiveFactory()
    assert str(model) == f"{model.title}"


def create_archive_items_for_images(images, archive):
    for image in images:
        civ = ComponentInterfaceValueFactory(image=image)
        ai = ArchiveItemFactory(archive=archive)
        ai.values.add(civ)


@pytest.fixture(scope="function")
def archive_item_with_title(db):
    archive = ArchiveFactory()
    ai = ArchiveItemFactory(archive=archive)

    # Default
    assert ai.title == ""

    # Update
    ai.title = "An Archive Item Title"
    ai.save()

    return ai


@pytest.mark.django_db
def test_archive_item_duplicate_title_edit(archive_item_with_title):
    # Sanity
    ai = ArchiveItemFactory(
        archive=archive_item_with_title.archive,
        title="Another Archive Item",
    )

    ai.title = archive_item_with_title.title
    with pytest.raises(IntegrityError):
        ai.save()


@pytest.mark.django_db
def test_archive_item_duplicate_title_create(archive_item_with_title):
    with pytest.raises(IntegrityError):
        ArchiveItemFactory(
            archive=archive_item_with_title.archive,
            title=archive_item_with_title.title,
        )


@pytest.mark.django_db
def test_archive_item_duplicate_title_other_archive(
    archive_item_with_title,
):
    # Another archive is not a problem
    ArchiveItemFactory(
        archive=ArchiveFactory(),
        title=archive_item_with_title.title,
    )


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


@pytest.mark.django_db
def test_archive_item_editable():
    ai = ArchiveItemFactory()
    assert ai.is_editable


@pytest.mark.django_db
def test_archive_allowed_socket_slugs():
    archive = ArchiveFactory()
    phase = PhaseFactory(archive=archive)
    ci1, ci2, ci3, ci4, ci5 = ComponentInterfaceFactory.create_batch(5)
    int1 = AlgorithmInterfaceFactory(inputs=[ci1, ci2], outputs=[ci4])
    int2 = AlgorithmInterfaceFactory(inputs=[ci3], outputs=[ci5])
    phase.algorithm_interfaces.set([int1, int2])

    assert archive.allowed_socket_slugs == {ci1.slug, ci2.slug, ci3.slug}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "archive_editor",
    (True, False),
    ids=["editor", "not_editor"],
)
@pytest.mark.parametrize(
    "archive_uploader",
    (True, False),
    ids=["uploader", "not_uploader"],
)
@pytest.mark.parametrize(
    "archive_user",
    (True, False),
    ids=["user", "not_user"],
)
def test_archive_queryset_with_user_roles(
    archive_editor, archive_uploader, archive_user
):
    archive = ArchiveFactory()
    user = UserFactory()

    if archive_editor:
        archive.add_editor(user)
    if archive_uploader:
        archive.add_uploader(user)
    if archive_user:
        archive.add_user(user)

    qs = Archive.objects.with_user_roles(user=user)
    result = qs.get(pk=archive.pk)

    assert result.user_is_archive_editor is archive_editor
    assert result.user_is_archive_uploader is archive_uploader
    assert result.user_is_archive_user is archive_user


@pytest.mark.django_db
def test_archive_queryset_with_user_roles_multiple_archives():
    archive1 = ArchiveFactory()
    archive2 = ArchiveFactory()
    archive3 = ArchiveFactory()
    archive4 = ArchiveFactory()
    archive5 = ArchiveFactory()
    user = UserFactory()

    archive2.add_user(user)
    archive3.add_uploader(user)
    archive4.add_editor(user)
    archive5.add_user(user)
    archive5.add_uploader(user)
    archive5.add_editor(user)

    qs = Archive.objects.with_user_roles(user=user)
    assert qs.count() == 5

    result = {a.pk: a for a in qs}

    # Non-member
    assert result[archive1.pk].user_is_archive_editor is False
    assert result[archive1.pk].user_is_archive_uploader is False
    assert result[archive1.pk].user_is_archive_user is False

    # User
    assert result[archive2.pk].user_is_archive_editor is False
    assert result[archive2.pk].user_is_archive_uploader is False
    assert result[archive2.pk].user_is_archive_user is True

    # Uploader
    assert result[archive3.pk].user_is_archive_editor is False
    assert result[archive3.pk].user_is_archive_uploader is True
    assert result[archive3.pk].user_is_archive_user is False

    # Editor
    assert result[archive4.pk].user_is_archive_editor is True
    assert result[archive4.pk].user_is_archive_uploader is False
    assert result[archive4.pk].user_is_archive_user is False

    # All
    assert result[archive5.pk].user_is_archive_editor is True
    assert result[archive5.pk].user_is_archive_uploader is True
    assert result[archive5.pk].user_is_archive_user is True
