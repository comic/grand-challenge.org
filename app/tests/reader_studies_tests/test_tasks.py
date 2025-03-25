import pytest

from grandchallenge.components.models import ComponentInterface
from grandchallenge.reader_studies.tasks import (
    answers_from_ground_truth,
    create_display_sets_for_upload_session,
)
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)


@pytest.mark.django_db
def test_create_display_sets_for_upload_session():
    rs = ReaderStudyFactory()
    image = ImageFactory()
    ci = ComponentInterface.objects.get(slug="generic-medical-image")

    assert rs.display_sets.count() == 0

    create_display_sets_for_upload_session(
        upload_session_pk=image.origin.pk,
        reader_study_pk=rs.pk,
        interface_pk=ci.pk,
    )

    assert rs.display_sets.count() == 1
    assert rs.display_sets.first().values.first().image == image

    create_display_sets_for_upload_session(
        upload_session_pk=image.origin.pk,
        reader_study_pk=rs.pk,
        interface_pk=ci.pk,
    )

    assert rs.display_sets.count() == 1
    assert rs.display_sets.first().values.first().image == image


@pytest.mark.django_db
def test_answers_from_ground_truth_with_existing_answers():
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    q = QuestionFactory(reader_study=rs)

    user = UserFactory()
    rs.add_editor(user)

    answers_from_ground_truth(
        reader_study_pk=rs.pk, target_user_pk=user.pk
    )  # NOOP

    AnswerFactory(creator=user, question=q, display_set=ds)

    with pytest.raises(ValueError) as error:
        answers_from_ground_truth(
            reader_study_pk=rs.pk, target_user_pk=user.pk
        )
    assert "User already has answers" in str(error)
