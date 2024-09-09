from unittest import mock

import pytest
from django.core.exceptions import ValidationError

import grandchallenge
from grandchallenge.participants.forms import RegistrationRequestForm
from grandchallenge.participants.models import (
    RegistrationQuestionAnswer,
    RegistrationRequest,
)
from tests.factories import (
    ChallengeFactory,
    RegistrationQuestionFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_registration_request_form_no_questions(
    django_capture_on_commit_callbacks,
):
    challenge = ChallengeFactory()
    user = UserFactory()

    assert not RegistrationRequest.objects.filter(
        user=user
    ).exists(), "Starts with no requests"  # Sanity
    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={},
    )
    form.full_clean()
    assert form.is_valid()
    with django_capture_on_commit_callbacks(execute=True):
        form.save()

    assert RegistrationRequest.objects.filter(
        user=user
    ).exists(), "Should have a registration request"


@pytest.mark.django_db
def test_registration_request_form_with_questions(
    django_capture_on_commit_callbacks,
):
    challenge = ChallengeFactory()
    user = UserFactory()

    assert not RegistrationRequest.objects.filter(
        user=user
    ).exists(), "Starts with no requests"  # Sanity

    rq1, rq2, rq3 = RegistrationQuestionFactory.create_batch(
        3,
        challenge=challenge,
    )

    form_data = {
        str(rq1.pk): "answer_1",
        str(rq2.pk): "answer_2",
        str(rq3.pk): "answer_3",
    }
    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data=form_data,
    )

    form.full_clean()
    assert form.is_valid()
    with django_capture_on_commit_callbacks(execute=True):
        rr = form.save()

    for rq in (rq1, rq2, rq3):
        rqa = RegistrationQuestionAnswer.objects.get(
            registration_request=rr, question=rq
        )
        assert (
            rqa.answer == form_data[str(rq.pk)]
        ), "Answer stored is the answer that was posted"


@pytest.mark.django_db
def test_registration_request_form_partial_data():
    challenge = ChallengeFactory()
    user = UserFactory()

    assert not RegistrationRequest.objects.filter(
        user=user
    ).exists(), "Starts with no requests"  # Sanity

    rq1 = RegistrationQuestionFactory(challenge=challenge)
    rq2 = RegistrationQuestionFactory(challenge=challenge)
    _ = RegistrationQuestionFactory(
        challenge=challenge,
        required=False,
    )

    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            str(rq1.pk): "answer_1",
            # Note, missing two questions
        },
    )

    form.full_clean()
    assert (
        not form.is_valid()
    ), "Form should not be valid with missing data of required answer"

    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            str(rq1.pk): "answer_1",
            str(rq2.pk): "answer_2",
            # Note, missing a non required question
        },
    )

    form.full_clean()

    assert (
        form.is_valid()
    ), "Form should be valid when only missing data of non-required answer"


@pytest.mark.django_db
def test_registration_request_form_incorrect_format(
    django_capture_on_commit_callbacks,
):
    challenge = ChallengeFactory()
    user = UserFactory()

    rq = RegistrationQuestionFactory(
        challenge=challenge, schema={"type": "integer"}
    )
    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            str(rq.pk): "answer",
        },
    )

    form.full_clean()

    assert (
        not form.is_valid()
    ), "Form should not be valid with incorrect formated answer"

    assert str(rq.pk) in form.errors, "Error should point towards the question"
    assert (
        "incorrect format" in form.errors[str(rq.pk)][0].lower()
    ), "Should be correct error about incorrect format"

    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            str(rq.pk): "1",
        },
    )

    form.full_clean()
    assert form.is_valid(), "With correct format, form should be valid"
    with django_capture_on_commit_callbacks(execute=True):
        rr = form.save()

    rqa = RegistrationQuestionAnswer.objects.get(
        registration_request=rr, question=rq
    )
    assert rqa.answer == 1, "Answer stored in correct format"


@pytest.mark.django_db
def test_registration_request_form_question_failure_removes_registration(
    django_capture_on_commit_callbacks,
):
    challenge = ChallengeFactory()
    user = UserFactory()

    rq = RegistrationQuestionFactory(challenge=challenge)
    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            str(rq.pk): "answer",
        },
    )

    form.full_clean()
    assert form.is_valid(), "Sanity: form is normally valid"

    def clean_with_error():
        raise ValidationError("Intentional Error")

    with mock.patch.object(
        grandchallenge.participants.forms.RegistrationQuestionAnswer,
        "clean",
        side_effect=clean_with_error,
    ):
        with pytest.raises(ValidationError):
            with django_capture_on_commit_callbacks(execute=True):
                form.save()

    assert (
        not RegistrationRequest.objects.exists()
    ), "No requests is made when saving questions goes wrong"
