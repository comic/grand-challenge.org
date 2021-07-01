from unittest.mock import call

import pytest
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_archive
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.archives_tests.utils import TwoArchives
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.evaluation_tests.test_permissions import get_groups_with_set_perms
from tests.factories import ImageFactory


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_archive_item_permissions_signal(client, reverse):  # noqa: C901
    ai1, ai2 = ArchiveItemFactory.create_batch(2)
    im1, im2, im3, im4 = ImageFactory.create_batch(4)

    civ1, civ2, civ3, civ4 = (
        ComponentInterfaceValueFactory(image=im1),
        ComponentInterfaceValueFactory(image=im2),
        ComponentInterfaceValueFactory(image=im3),
        ComponentInterfaceValueFactory(image=im4),
    )

    with capture_on_commit_callbacks(execute=True):
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
    with capture_on_commit_callbacks(execute=True):
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

    with capture_on_commit_callbacks(execute=True):
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

    with capture_on_commit_callbacks(execute=True):
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

    with capture_on_commit_callbacks(execute=True):
        ai.values.set([civ])

    assert get_groups_with_set_perms(im) == {
        ai.archive.editors_group: {"view_image"},
        ai.archive.uploaders_group: {"view_image"},
        ai.archive.users_group: {"view_image"},
    }

    a2 = ArchiveFactory()

    ai.archive = a2

    with capture_on_commit_callbacks(execute=True):
        ai.save()

    assert get_groups_with_set_perms(im) == {
        a2.editors_group: {"view_image"},
        a2.uploaders_group: {"view_image"},
        a2.users_group: {"view_image"},
    }


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_adding_images_triggers_task(reverse, mocker):
    mocker.patch(
        "grandchallenge.algorithms.tasks.create_algorithm_jobs_for_archive.apply_async"
    )
    create_algorithm_jobs_for_archive.apply_async.assert_not_called()

    arch_set = TwoArchives()

    with capture_on_commit_callbacks(execute=True):
        ai1, ai2 = (
            ArchiveItemFactory(archive=arch_set.arch1),
            ArchiveItemFactory(archive=arch_set.arch2),
        )
        ai1.values.set([ComponentInterfaceValueFactory()])
        ai2.values.set([ComponentInterfaceValueFactory()])
    create_algorithm_jobs_for_archive.apply_async.assert_has_calls(
        [
            call(
                kwargs={
                    "archive_pks": [arch_set.arch1.pk],
                    "archive_item_pks": [ai1.pk],
                }
            ),
            call(
                kwargs={
                    "archive_pks": [arch_set.arch2.pk],
                    "archive_item_pks": [ai2.pk],
                }
            ),
        ]
    )
    create_algorithm_jobs_for_archive.apply_async.reset_mock()
    ai1, ai2, ai3, ai4 = (
        ArchiveItemFactory(archive=arch_set.arch1),
        ArchiveItemFactory(archive=arch_set.arch1),
        ArchiveItemFactory(archive=arch_set.arch1),
        ArchiveItemFactory(archive=arch_set.arch1),
    )
    civ1, civ2, civ3, civ4 = (
        ComponentInterfaceValueFactory(),
        ComponentInterfaceValueFactory(),
        ComponentInterfaceValueFactory(),
        ComponentInterfaceValueFactory(),
    )

    if not reverse:
        for ai, civ in [(ai1, civ1), (ai2, civ2), (ai3, civ3), (ai4, civ4)]:
            with capture_on_commit_callbacks(execute=True):
                ai.values.set([civ])

            kwargs = create_algorithm_jobs_for_archive.apply_async.call_args.kwargs[
                "kwargs"
            ]
            create_algorithm_jobs_for_archive.apply_async.assert_called_once()
            assert {*kwargs["archive_pks"]} == {arch_set.arch1.pk}
            assert {*kwargs["archive_item_pks"]} == {ai.pk}
            create_algorithm_jobs_for_archive.apply_async.reset_mock()

            with capture_on_commit_callbacks(execute=True):
                ai.values.remove(civ)
                ai.values.clear()

            create_algorithm_jobs_for_archive.apply_async.assert_not_called()
    else:
        for ai in [ai1, ai2, ai3, ai4]:
            with capture_on_commit_callbacks(execute=True):
                civ = ComponentInterfaceValueFactory()
                civ.archive_items.add(ai)

            kwargs = create_algorithm_jobs_for_archive.apply_async.call_args.kwargs[
                "kwargs"
            ]
            create_algorithm_jobs_for_archive.apply_async.assert_called_once()
            assert {*kwargs["archive_pks"]} == {arch_set.arch1.pk}
            assert {*kwargs["archive_item_pks"]} == {ai.pk}
            create_algorithm_jobs_for_archive.apply_async.reset_mock()

        with capture_on_commit_callbacks(execute=True):
            civ3.archive_items.remove(ai3)
            civ1.archive_items.clear()

        create_algorithm_jobs_for_archive.apply_async.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_adding_algorithms_triggers_task(reverse, mocker):
    mocker.patch(
        "grandchallenge.algorithms.tasks.create_algorithm_jobs_for_archive.apply_async"
    )
    create_algorithm_jobs_for_archive.apply_async.assert_not_called()

    arch_set = TwoArchives()

    with capture_on_commit_callbacks(execute=True):
        arch_set.arch1.algorithms.add(AlgorithmFactory())
        arch_set.arch2.algorithms.add(AlgorithmFactory())

    create_algorithm_jobs_for_archive.apply_async.assert_has_calls(
        [
            call(
                kwargs={
                    "archive_pks": [arch_set.arch1.pk],
                    "algorithm_pks": [arch_set.arch1.algorithms.first().pk],
                }
            ),
            call(
                kwargs={
                    "archive_pks": [arch_set.arch2.pk],
                    "algorithm_pks": [arch_set.arch2.algorithms.first().pk],
                }
            ),
        ]
    )
    create_algorithm_jobs_for_archive.apply_async.reset_mock()
    algorithms = (
        AlgorithmFactory(),
        AlgorithmFactory(),
        AlgorithmFactory(),
        AlgorithmFactory(),
    )

    if not reverse:
        with capture_on_commit_callbacks(execute=True):
            arch_set.arch1.algorithms.add(*algorithms)

        kwargs = create_algorithm_jobs_for_archive.apply_async.call_args.kwargs[
            "kwargs"
        ]
        create_algorithm_jobs_for_archive.apply_async.assert_called_once()
        assert {*kwargs["archive_pks"]} == {arch_set.arch1.pk}
        assert {*kwargs["algorithm_pks"]} == {a.pk for a in algorithms}
        create_algorithm_jobs_for_archive.apply_async.reset_mock()

        with capture_on_commit_callbacks(execute=True):
            arch_set.arch1.algorithms.remove(algorithms[0], algorithms[1])
            arch_set.arch1.algorithms.clear()

        create_algorithm_jobs_for_archive.apply_async.assert_not_called()
    else:
        for alg in algorithms:
            with capture_on_commit_callbacks(execute=True):
                alg.archive_set.add(arch_set.arch1, arch_set.arch2)

            kwargs = create_algorithm_jobs_for_archive.apply_async.call_args.kwargs[
                "kwargs"
            ]
            create_algorithm_jobs_for_archive.apply_async.assert_called_once()
            assert {*kwargs["archive_pks"]} == {
                arch_set.arch1.pk,
                arch_set.arch2.pk,
            }
            assert {*kwargs["algorithm_pks"]} == {alg.pk}
            create_algorithm_jobs_for_archive.apply_async.reset_mock()

        with capture_on_commit_callbacks(execute=True):
            for im in algorithms[-2:]:
                im.archive_set.remove(arch_set.arch1, arch_set.arch2)
            for im in algorithms[:2]:
                im.archive_set.remove(arch_set.arch2)
            algorithms[0].archive_set.clear()

        create_algorithm_jobs_for_archive.apply_async.assert_not_called()
