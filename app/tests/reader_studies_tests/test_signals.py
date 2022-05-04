import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.components.models import InterfaceKind
from grandchallenge.reader_studies.models import Question
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.test_permissions import get_groups_with_set_perms
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.reader_studies_tests.utils import TwoReaderStudies
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_reader_can_download_images(client, reverse):
    rs_set = TwoReaderStudies()

    im1, im2, im3, im4 = (
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
        ImageFactory(),
    )

    if reverse:
        for im in [im1, im2, im3, im4]:
            im.readerstudies.add(rs_set.rs1, rs_set.rs2)
        for im in [im3, im4]:
            im.readerstudies.remove(rs_set.rs1, rs_set.rs2)
        for im in [im1, im2]:
            im.readerstudies.remove(rs_set.rs2)
    else:
        # Test that adding images works
        rs_set.rs1.images.add(im1, im2, im3, im4)
        # Test that removing images works
        rs_set.rs1.images.remove(im3, im4)

    tests = (
        (None, 200, []),
        (rs_set.creator, 200, []),
        (rs_set.editor1, 200, [im1.pk, im2.pk]),
        (rs_set.reader1, 200, [im1.pk, im2.pk]),
        (rs_set.editor2, 200, []),
        (rs_set.reader2, 200, []),
        (rs_set.u, 200, []),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:image-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        assert response.json()["count"] == len(test[2])

        pks = {obj["pk"] for obj in response.json()["results"]}
        assert {str(pk) for pk in test[2]} == pks

    # Test clearing
    if reverse:
        im1.readerstudies.clear()
        im2.readerstudies.clear()
    else:
        rs_set.rs1.images.clear()

    response = get_view_for_user(
        viewname="api:image-list",
        client=client,
        user=rs_set.reader1,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_assign_score(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    im = ImageFactory()
    q1 = QuestionFactory(reader_study=rs)
    q2 = QuestionFactory(
        reader_study=rs, answer_type=Question.AnswerType.MULTIPLE_CHOICE
    )
    e, r1, r2 = UserFactory(), UserFactory(), UserFactory()

    rs.images.add(im)
    rs.add_editor(e)
    rs.add_reader(r1)
    rs.add_reader(r2)

    with capture_on_commit_callbacks(execute=True):
        a1 = AnswerFactory(question=q1, creator=r1, answer="foo")
    a1.images.add(im)
    assert a1.score is None

    with capture_on_commit_callbacks(execute=True):
        gt = AnswerFactory(
            question=q1, creator=e, answer="foo", is_ground_truth=True
        )
        gt.images.add(im)
    a1.refresh_from_db()
    assert a1.score == 1.0

    with capture_on_commit_callbacks(execute=True):
        a2 = AnswerFactory(question=q1, creator=r2, answer="foo")
        a2.images.add(im)
    a2.refresh_from_db()
    assert a2.score == 1.0

    with capture_on_commit_callbacks(execute=True):
        a1 = AnswerFactory(question=q2, creator=r1, answer=[])
        a1.images.add(im)
    a1.refresh_from_db()
    assert a1.score is None

    with capture_on_commit_callbacks(execute=True):
        gt = AnswerFactory(
            question=q2, creator=e, answer=[], is_ground_truth=True
        )
        gt.images.add(im)
    a1.refresh_from_db()
    assert a1.score == 1.0

    with capture_on_commit_callbacks(execute=True):
        a2 = AnswerFactory(question=q2, creator=r2, answer=[])
        a2.images.add(im)
    a2.refresh_from_db()
    assert a2.score == 1.0


@pytest.mark.django_db
def test_assert_modification_allowed():
    rs = ReaderStudyFactory()
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
    civ = ComponentInterfaceValueFactory(interface=ci, value=True)
    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(civ)

    del ds.is_editable

    civ2 = ComponentInterfaceValueFactory(interface=ci, value=True)
    ds.values.remove(civ)
    ds.values.add(civ2)

    assert ds.values.count() == 1
    assert ds.values.first() == civ2

    q = QuestionFactory(reader_study=rs)
    AnswerFactory(question=q, display_set=ds)

    del ds.is_editable

    with pytest.raises(ValidationError):
        with transaction.atomic():
            ds.values.remove(civ2)

    assert ds.values.count() == 1
    assert ds.values.first() == civ2


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_display_set_permissions_signal(client, reverse):
    ds1, ds2 = DisplaySetFactory.create_batch(2)
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
                civ.display_sets.add(ds1, ds2)
            for civ in [civ3, civ4]:
                civ.display_sets.remove(ds1, ds2)
            for civ in [civ1, civ2]:
                civ.display_sets.remove(ds2)
        else:
            # Test that adding images works
            ds1.values.add(civ1, civ2, civ3, civ4)
            # Test that removing images works
            ds1.values.remove(civ3, civ4)

    assert get_groups_with_set_perms(im1) == {
        ds1.reader_study.editors_group: {"view_image"},
        ds1.reader_study.readers_group: {"view_image"},
    }
    assert get_groups_with_set_perms(im2) == {
        ds1.reader_study.editors_group: {"view_image"},
        ds1.reader_study.readers_group: {"view_image"},
    }
    assert get_groups_with_set_perms(im3) == {}
    assert get_groups_with_set_perms(im4) == {}

    # Test clearing
    with capture_on_commit_callbacks(execute=True):
        if reverse:
            civ1.display_sets.clear()
            civ2.display_sets.clear()
        else:
            ds1.values.clear()

    assert get_groups_with_set_perms(im1) == {}
    assert get_groups_with_set_perms(im2) == {}


@pytest.mark.django_db
def test_deleting_display_set_removes_permissions():
    ds1, ds2 = DisplaySetFactory.create_batch(2)
    im = ImageFactory()
    civ = ComponentInterfaceValueFactory(image=im)

    with capture_on_commit_callbacks(execute=True):
        ds1.values.set([civ])
        ds2.values.set([civ])

    assert get_groups_with_set_perms(im) == {
        ds1.reader_study.editors_group: {"view_image"},
        ds1.reader_study.readers_group: {"view_image"},
        ds2.reader_study.editors_group: {"view_image"},
        ds2.reader_study.readers_group: {"view_image"},
    }

    with capture_on_commit_callbacks(execute=True):
        ds1.delete()

    assert get_groups_with_set_perms(im) == {
        ds2.reader_study.editors_group: {"view_image"},
        ds2.reader_study.readers_group: {"view_image"},
    }


@pytest.mark.django_db
def test_changing_reader_study_updates_permissions():
    ds = DisplaySetFactory()
    im = ImageFactory()
    civ = ComponentInterfaceValueFactory(image=im)

    with capture_on_commit_callbacks(execute=True):
        ds.values.set([civ])

    assert get_groups_with_set_perms(im) == {
        ds.reader_study.editors_group: {"view_image"},
        ds.reader_study.readers_group: {"view_image"},
    }

    rs = ReaderStudyFactory()

    ds.reader_study = rs

    with capture_on_commit_callbacks(execute=True):
        ds.save()

    assert get_groups_with_set_perms(im) == {
        rs.editors_group: {"view_image"},
        rs.readers_group: {"view_image"},
    }
