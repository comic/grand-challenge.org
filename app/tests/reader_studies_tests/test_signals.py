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


@pytest.mark.django_db
def test_assign_score(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    q1 = QuestionFactory(reader_study=rs)
    q2 = QuestionFactory(
        reader_study=rs, answer_type=Question.AnswerType.MULTIPLE_CHOICE
    )
    e, r1, r2 = UserFactory(), UserFactory(), UserFactory()

    rs.add_editor(e)
    rs.add_reader(r1)
    rs.add_reader(r2)

    with capture_on_commit_callbacks(execute=True):
        a1 = AnswerFactory(
            question=q1, creator=r1, answer="foo", display_set=ds
        )
    assert a1.score is None

    with capture_on_commit_callbacks(execute=True):
        AnswerFactory(
            question=q1,
            creator=e,
            answer="foo",
            is_ground_truth=True,
            display_set=ds,
        )
    a1.refresh_from_db()
    assert a1.score == 1.0

    with capture_on_commit_callbacks(execute=True):
        a2 = AnswerFactory(
            question=q1, creator=r2, answer="foo", display_set=ds
        )
    a2.refresh_from_db()
    assert a2.score == 1.0

    with capture_on_commit_callbacks(execute=True):
        a1 = AnswerFactory(question=q2, creator=r1, answer=[], display_set=ds)
    a1.refresh_from_db()
    assert a1.score is None

    with capture_on_commit_callbacks(execute=True):
        AnswerFactory(
            question=q2,
            creator=e,
            answer=[],
            is_ground_truth=True,
            display_set=ds,
        )
    a1.refresh_from_db()
    assert a1.score == 1.0

    with capture_on_commit_callbacks(execute=True):
        a2 = AnswerFactory(question=q2, creator=r2, answer=[], display_set=ds)
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
