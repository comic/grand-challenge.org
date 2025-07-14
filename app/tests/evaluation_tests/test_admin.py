import pytest
from django.contrib.admin import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware

from grandchallenge.components.admin import requeue_jobs
from grandchallenge.evaluation.admin import (
    PhaseAdmin,
    SubmissionAdmin,
    reevaluate_submissions,
)
from grandchallenge.evaluation.models import Evaluation, Submission
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_read_only_fields_disabled():
    p1, p2 = PhaseFactory.create_batch(
        2,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        challenge=ChallengeFactory(),
    )
    p1.parent = p2
    p1.save()
    form = PhaseAdmin.form(
        instance=p1,
    )
    assert form.fields["submission_kind"].disabled

    p3, p4 = PhaseFactory.create_batch(
        2,
        submission_kind=SubmissionKindChoices.CSV,
        challenge=ChallengeFactory(),
    )
    p3.parent = p4
    p3.save()
    form = PhaseAdmin.form(
        instance=p3,
    )
    assert form.fields["submission_kind"].disabled


@pytest.mark.django_db
def test_selectable_gpu_type_choices_invalid():
    phase = PhaseFactory()
    form = PhaseAdmin.form(
        instance=phase,
        data={"evaluation_selectable_gpu_type_choices": '["invalid_choice"]'},
    )

    assert form.is_valid() is False
    assert (
        "JSON does not fulfill schema: instance &#x27;invalid_choice&#x27; is not "
        "one of " in str(form.errors)
    )


@pytest.mark.django_db
def test_reevaluate_submission_only_for_evaluations_without_inputs(rf):
    s1, s2 = SubmissionFactory.create_batch(2)
    s1.phase.additional_evaluation_inputs.add(ComponentInterfaceFactory())

    modeladmin = SubmissionAdmin(Submission, AdminSite)
    request = rf.get("/foo")

    # Add session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    # Add messages storage
    messages_storage = FallbackStorage(request)
    request.session["_messages"] = messages_storage
    request._messages = messages_storage

    reevaluate_submissions(
        request=request,
        modeladmin=modeladmin,
        queryset=Submission.objects.all(),
    )

    messages = [m.message for m in request._messages]
    assert len(messages) == 1
    assert (
        messages[0]
        == f"Submission {s1.pk} cannot be reevaluated in the admin because it requires additional inputs. Please reschedule through the challenge UI."
    )


@pytest.mark.django_db
def test_reevaluate_submission_idempotent(rf):
    submission = SubmissionFactory()
    MethodFactory(
        phase=submission.phase,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    modeladmin = SubmissionAdmin(Submission, AdminSite)
    request = rf.get("/foo")

    reevaluate_submissions(
        request=request,
        modeladmin=modeladmin,
        queryset=Submission.objects.all(),
    )

    reevaluate_submissions(
        request=request,
        modeladmin=modeladmin,
        queryset=Submission.objects.all(),
    )

    assert Evaluation.objects.count() == 1


@pytest.mark.django_db
def test_requeueing_external_evaluation_not_possible():
    phase_ext = PhaseFactory(external_evaluation=True)
    phase_int = PhaseFactory()

    eval_ext = EvaluationFactory(
        time_limit=60,
        status=Evaluation.FAILURE,
        submission__phase=phase_ext,
    )
    eval_int = EvaluationFactory(
        time_limit=60,
        status=Evaluation.FAILURE,
        submission__phase=phase_int,
    )
    evals = Evaluation.objects.all()

    assert len(evals) == 2

    requeue_jobs(None, None, evals)

    eval_ext.refresh_from_db()
    eval_int.refresh_from_db()

    # int evaluation has been requeued
    assert eval_int.status == Evaluation.RETRY
    # ext evaluation has not been requeued
    assert eval_ext.status == Evaluation.FAILURE


@pytest.mark.django_db
def test_rescheduling_external_evaluation_not_possible(rf):
    phase_ext = PhaseFactory(external_evaluation=True)
    phase_int = PhaseFactory()

    SubmissionFactory(phase=phase_ext)
    SubmissionFactory(phase=phase_int)

    modeladmin = SubmissionAdmin(Submission, AdminSite)
    request = rf.get("/foo")
    # Add session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    # Add messages storage
    messages_storage = FallbackStorage(request)
    request.session["_messages"] = messages_storage
    request._messages = messages_storage

    reevaluate_submissions(modeladmin, request, Submission.objects.all())

    messages = [m.message for m in request._messages]
    assert len(messages) == 1
    assert messages[0] == "External evaluations cannot be requeued."
