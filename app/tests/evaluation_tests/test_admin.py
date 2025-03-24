import pytest
from django.contrib.admin import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware

from grandchallenge.components.models import ComponentInterface
from grandchallenge.evaluation.admin import (
    NON_EVALUATION_SOCKET_SLUGS,
    PhaseAdmin,
    PhaseAdminForm,
    SubmissionAdmin,
    reevaluate_submissions,
)
from grandchallenge.evaluation.models import Evaluation, Submission
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.algorithms_tests.factories import AlgorithmInterfaceFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import (
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
    s1.phase.inputs.add(ComponentInterfaceFactory())

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
def test_disjoint_inputs_and_algorithm_sockets():
    ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
    interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
    phase.algorithm_interfaces.set([interface])

    form = PhaseAdminForm(
        instance=phase, data={"inputs": [ci1.pk, ci2.pk, ci3.pk, ci4.pk]}
    )

    assert not form.is_valid()
    assert (
        "The following sockets cannot be defined as evaluation inputs or "
        "outputs because they are already defined as algorithm inputs or "
        "outputs for this phase" in str(form.errors)
    )
    assert ci1.slug in str(form.errors)
    assert ci2.slug in str(form.errors)
    assert ci3.slug not in str(form.errors)
    assert ci4.slug not in str(form.errors)


@pytest.mark.parametrize("slug", NON_EVALUATION_SOCKET_SLUGS)
@pytest.mark.django_db
def test_non_evaluation_socket_slugs(slug):
    ci, _ = ComponentInterface.objects.get_or_create(slug=slug)

    form = PhaseAdminForm(instance=PhaseFactory(), data={"inputs": [ci.pk]})
    assert not form.is_valid()
    assert (
        form.errors["inputs"][0]
        == "Evaluation inputs cannot be of the following types: predictions-csv-file, predictions-json-file, predictions-zip-file, metrics-json-file, results-json-file"
    )
