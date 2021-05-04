from unittest.mock import call

import pytest
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_archive
from grandchallenge.components.models import ComponentInterfaceValue
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.utils import TwoArchives
from tests.factories import ImageFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_user_can_download_images(client, reverse):  # noqa: C901
    arch_set = TwoArchives()

    im1, im2, im3, im4 = (
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
    )

    images = {im1, im2, im3, im4}

    if reverse:
        for im in [im1, im2, im3, im4]:
            im.archive_set.add(arch_set.arch1, arch_set.arch2)
        for im in [im3, im4]:
            im.archive_set.remove(arch_set.arch1, arch_set.arch2)
        for im in [im1, im2]:
            im.archive_set.remove(arch_set.arch2)
    else:
        # Test that adding images works
        arch_set.arch1.images.add(im1, im2, im3, im4)
        # Test that removing images works
        arch_set.arch1.images.remove(im3, im4)

    tests = (
        (None, 200, set()),
        (arch_set.editor1, 200, {im1.pk, im2.pk}),
        (arch_set.uploader1, 200, {im1.pk, im2.pk}),
        (arch_set.user1, 200, {im1.pk, im2.pk}),
        (arch_set.editor2, 200, set()),
        (arch_set.uploader2, 200, set()),
        (arch_set.user2, 200, set()),
        (arch_set.u, 200, set()),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:image-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        pks = [obj["pk"] for obj in response.json()["results"]]

        for pk in test[2]:
            assert str(pk) in pks

        for pk in images - test[2]:
            assert str(pk) not in pks

    # Test clearing
    if reverse:
        im1.archive_set.clear()
        im2.archive_set.clear()
    else:
        arch_set.arch1.images.clear()

    response = get_view_for_user(
        viewname="api:image-list",
        client=client,
        user=arch_set.user1,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


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
