from unittest.mock import call

import pytest
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_archive
from grandchallenge.components.models import ComponentInterfaceValue
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


@pytest.mark.xfail(reason="Archive.images deprecated")
@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_adding_images_triggers_task(reverse, mocker):
    mocker.patch(
        "grandchallenge.algorithms.tasks.create_algorithm_jobs_for_archive.apply_async"
    )
    create_algorithm_jobs_for_archive.apply_async.assert_not_called()

    arch_set = TwoArchives()

    with capture_on_commit_callbacks(execute=True):
        arch_set.arch1.images.add(ImageFactory())
        arch_set.arch2.images.add(ImageFactory())
    create_algorithm_jobs_for_archive.apply_async.assert_has_calls(
        [
            call(
                kwargs={
                    "archive_pks": [arch_set.arch1.pk],
                    "civ_pks": list(
                        arch_set.arch1.items.values_list("values", flat=True)
                    ),
                }
            ),
            call(
                kwargs={
                    "archive_pks": [arch_set.arch2.pk],
                    "civ_pks": list(
                        arch_set.arch2.items.values_list("values", flat=True)
                    ),
                }
            ),
        ]
    )
    create_algorithm_jobs_for_archive.apply_async.reset_mock()

    im1, im2, im3, im4 = (
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
    )

    if not reverse:
        with capture_on_commit_callbacks(execute=True):
            arch_set.arch1.images.add(im1, im2, im3, im4)

        kwargs = create_algorithm_jobs_for_archive.apply_async.call_args.kwargs[
            "kwargs"
        ]
        create_algorithm_jobs_for_archive.apply_async.assert_called_once()
        assert {*kwargs["archive_pks"]} == {arch_set.arch1.pk}
        assert {*kwargs["civ_pks"]} == set(
            list(
                ComponentInterfaceValue.objects.filter(
                    image__in=[im1, im2, im3, im4]
                ).values_list("pk", flat=True)
            )
        )
        create_algorithm_jobs_for_archive.apply_async.reset_mock()

        with capture_on_commit_callbacks(execute=True):
            arch_set.arch1.images.remove(im3, im4)
            arch_set.arch1.images.clear()

        create_algorithm_jobs_for_archive.apply_async.assert_not_called()
    else:
        for im in [im1, im2, im3, im4]:
            with capture_on_commit_callbacks(execute=True):
                im.archive_set.add(arch_set.arch1, arch_set.arch2)

            kwargs = create_algorithm_jobs_for_archive.apply_async.call_args.kwargs[
                "kwargs"
            ]
            create_algorithm_jobs_for_archive.apply_async.assert_called_once()
            assert {*kwargs["archive_pks"]} == {
                arch_set.arch1.pk,
                arch_set.arch2.pk,
            }
            assert {*kwargs["civ_pks"]} == set(
                list(
                    ComponentInterfaceValue.objects.filter(
                        image=im
                    ).values_list("pk", flat=True)
                )
            )
            create_algorithm_jobs_for_archive.apply_async.reset_mock()

        with capture_on_commit_callbacks(execute=True):
            for im in [im3, im4]:
                im.archive_set.remove(arch_set.arch1, arch_set.arch2)
            for im in [im1, im2]:
                im.archive_set.remove(arch_set.arch2)
            im1.archive_set.clear()

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
