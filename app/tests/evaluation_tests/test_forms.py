import pytest
from factory.django import ImageField

from grandchallenge.algorithms.forms import AlgorithmForPhaseForm
from grandchallenge.algorithms.models import Job
from grandchallenge.evaluation.forms import (
    ConfigureAlgorithmPhasesForm,
    SubmissionForm,
)
from grandchallenge.evaluation.models import Evaluation, Phase, Submission
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import PaymentStatusChoices
from grandchallenge.uploads.models import UserUpload
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import (
    ChallengeFactory,
    UserFactory,
    WorkstationConfigFactory,
    WorkstationFactory,
)
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.invoices_tests.factories import InvoiceFactory
from tests.uploads_tests.factories import UserUploadFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestSubmissionForm:
    def test_setting_predictions_file(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(submission_kind=SubmissionKindChoices.CSV),
        )

        assert "algorithm_image" not in form.fields
        assert "user_upload" in form.fields

    def test_setting_algorithm(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
        )

        assert "algorithm_image" in form.fields
        assert "algorithm" in form.fields
        assert "algorithm_model" in form.fields
        assert "user_upload" not in form.fields

    def test_algorithm_queryset(self):
        editor = UserFactory()
        alg1, alg2, alg3, alg4 = AlgorithmFactory.create_batch(4)
        alg1.add_editor(editor)
        alg2.add_editor(editor)
        alg4.add_editor(editor)
        ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
        alg1.inputs.set([ci1, ci2])
        alg1.outputs.set([ci3, ci4])
        alg3.inputs.set([ci1, ci2])
        alg3.outputs.set([ci3, ci4])
        alg4.inputs.set([ci1, ci2])
        alg4.outputs.set([ci3, ci4])
        for alg in [alg1, alg2, alg3]:
            AlgorithmImageFactory(
                algorithm=alg,
                is_in_registry=True,
                is_desired_version=True,
                is_manifest_valid=True,
            )
        AlgorithmImageFactory(algorithm=alg4)
        p = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
        p.algorithm_inputs.set([ci1, ci2])
        p.algorithm_outputs.set([ci3, ci4])
        form = SubmissionForm(
            user=editor,
            phase=p,
        )

        assert alg1 in form.fields["algorithm"].queryset
        assert alg2 not in form.fields["algorithm"].queryset
        assert alg2 not in form.fields["algorithm"].queryset
        assert alg4 not in form.fields["algorithm"].queryset

    def test_algorithm_queryset_if_parent_phase_exists(self):
        editor = UserFactory()
        alg1, alg2, alg3, alg4 = AlgorithmFactory.create_batch(4)
        ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
        for alg in [alg1, alg2, alg3, alg4]:
            alg.add_editor(editor)
            alg.inputs.set([ci1, ci2])
            alg.outputs.set([ci3, ci4])
            AlgorithmImageFactory(
                algorithm=alg,
                is_in_registry=True,
                is_desired_version=True,
                is_manifest_valid=True,
            )

        p_parent, p_child = PhaseFactory.create_batch(
            2,
            submission_kind=SubmissionKindChoices.ALGORITHM,
            challenge=ChallengeFactory(),
        )
        for p in [p_parent, p_child]:
            p.algorithm_inputs.set([ci1, ci2])
            p.algorithm_outputs.set([ci3, ci4])
        p_child.parent = p_parent
        p_child.save()

        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg1.active_image,
            status=Evaluation.SUCCESS,
        )
        EvaluationFactory(
            submission__phase=PhaseFactory(),
            submission__algorithm_image=alg2.active_image,
            status=Evaluation.SUCCESS,
        )
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg3.active_image,
            status=Evaluation.FAILURE,
        )
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg4.active_image,
            status=Evaluation.SUCCESS,
        )
        AlgorithmJobFactory(
            algorithm_image=alg1.active_image, status=Job.SUCCESS
        )

        form = SubmissionForm(
            user=editor,
            phase=p,
        )

        assert alg1 in form.fields["algorithm"].queryset
        assert alg2 not in form.fields["algorithm"].queryset
        assert alg3 not in form.fields["algorithm"].queryset
        assert alg4 not in form.fields["algorithm"].queryset

    def test_no_algorithm_selection(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
            data={"algorithm": ""},
        )

        assert form.errors["algorithm"] == ["This field is required."]

    def test_algorithm_no_permission(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
            data={"algorithm": AlgorithmFactory()},
        )

        assert form.errors["algorithm"] == [
            "Select a valid choice. That choice is not one of the available choices."
        ]

    def test_algorithm_with_permission(self):
        user = UserFactory()
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ci1 = ComponentInterfaceFactory()
        ci2 = ComponentInterfaceFactory()
        alg.inputs.set([ci1])
        alg.outputs.set([ci2])
        archive = ArchiveFactory()
        p = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
            archive=archive,
        )
        p.algorithm_inputs.set([ci1])
        p.algorithm_outputs.set([ci2])
        civ = ComponentInterfaceValueFactory(interface=ci1)
        i = ArchiveItemFactory(archive=p.archive)
        i.values.add(civ)

        InvoiceFactory(
            challenge=p.challenge,
            compute_costs_euros=10,
            payment_status=PaymentStatusChoices.COMPLIMENTARY,
        )

        # Fetch from the db to get the cost annotations
        # Maybe this is solved with GeneratedField (Django 5)?
        p = Phase.objects.get(pk=p.pk)

        ai = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=alg,
        )
        AlgorithmJobFactory(algorithm_image=ai, status=4)

        form = SubmissionForm(
            user=user,
            phase=p,
            data={"algorithm": alg, "creator": user, "phase": p},
        )

        assert form.errors == {}
        assert "algorithm" not in form.errors
        assert form.is_valid()

    def test_algorithm_image_and_model_set(self):
        user = UserFactory()
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ci1 = ComponentInterfaceFactory()
        ci2 = ComponentInterfaceFactory()
        alg.inputs.set([ci1])
        alg.outputs.set([ci2])
        archive = ArchiveFactory()
        p = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
            archive=archive,
        )
        p.algorithm_inputs.set([ci1])
        p.algorithm_outputs.set([ci2])
        civ = ComponentInterfaceValueFactory(interface=ci1)
        i = ArchiveItemFactory(archive=p.archive)
        i.values.add(civ)

        InvoiceFactory(
            challenge=p.challenge,
            compute_costs_euros=10,
            payment_status=PaymentStatusChoices.COMPLIMENTARY,
        )

        # Fetch from the db to get the cost annotations
        # Maybe this is solved with GeneratedField (Django 5)?
        p = Phase.objects.get(pk=p.pk)

        ai = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=alg,
        )
        am = AlgorithmModelFactory(algorithm=alg, is_desired_version=True)
        AlgorithmJobFactory(algorithm_image=ai, status=4)

        form = SubmissionForm(
            user=user,
            phase=p,
            data={"algorithm": alg, "creator": user, "phase": p},
        )

        assert form.is_valid()
        assert ai == form.cleaned_data["algorithm_image"]
        assert am == form.cleaned_data["algorithm_model"]

    def test_user_no_verification(self):
        user = UserFactory()

        form = SubmissionForm(
            user=user,
            phase=PhaseFactory(creator_must_be_verified=True),
            data={"creator": user},
        )

        assert form.errors["creator"] == [
            "You must verify your account before you can make a "
            "submission to this phase. Please "
            '<a href="https://testserver/verifications/create/"> '
            "request verification here</a>."
        ]

    @pytest.mark.parametrize("is_verified", (True, False))
    def test_user_with_verification(self, is_verified):
        user = UserFactory()
        VerificationFactory(user=user, is_verified=is_verified)

        phase = PhaseFactory(
            creator_must_be_verified=True,
            submissions_limit_per_user_per_period=10,
        )
        InvoiceFactory(
            challenge=phase.challenge,
            compute_costs_euros=10,
            payment_status=PaymentStatusChoices.COMPLIMENTARY,
        )

        # Fetch from the db to get the cost annotations
        # Maybe this is solved with GeneratedField (Django 5)?
        phase = Phase.objects.get(pk=phase.pk)

        form = SubmissionForm(
            user=user,
            phase=phase,
            data={"creator": user},
        )
        assert bool("creator" in form.errors) is not is_verified

    def test_no_valid_archive_items(self):
        user = UserFactory()
        p_pred = PhaseFactory(
            submission_kind=SubmissionKindChoices.CSV,
            submissions_limit_per_user_per_period=10,
        )
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ci1 = ComponentInterfaceFactory()
        ci2 = ComponentInterfaceFactory()
        alg.inputs.set([ci1])
        alg.outputs.set([ci2])
        archive = ArchiveFactory()
        p_alg = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
            archive=archive,
        )
        p_alg.algorithm_inputs.set([ci1])
        p_alg.algorithm_outputs.set([ci2])

        for p in [p_alg, p_pred]:
            InvoiceFactory(
                challenge=p.challenge,
                compute_costs_euros=10,
                payment_status=PaymentStatusChoices.COMPLIMENTARY,
            )
        # Fetch from the db to get the cost annotations
        # Maybe this is solved with GeneratedField (Django 5)?
        p_alg = Phase.objects.get(pk=p_alg.pk)
        p_pred = Phase.objects.get(pk=p_pred.pk)

        ai = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=alg,
        )
        AlgorithmJobFactory(algorithm_image=ai, status=4)

        upload = UserUploadFactory(creator=user)
        upload.status = UserUpload.StatusChoices.COMPLETED
        upload.save()
        form1 = SubmissionForm(
            user=user,
            phase=p_pred,
            data={"creator": user, "phase": p_pred, "user_upload": upload},
        )
        assert form1.is_valid()

        form2 = SubmissionForm(
            user=user,
            phase=p_alg,
            data={"algorithm": alg, "creator": user, "phase": p_alg},
        )

        assert (
            "This phase is not ready for submissions yet. There are no valid archive items in the archive linked to this phase."
            in form2.errors["__all__"]
        )
        assert not form2.is_valid()

        civ = ComponentInterfaceValueFactory(interface=ci1)
        i = ArchiveItemFactory(archive=p_alg.archive)
        i.values.add(civ)

        form3 = SubmissionForm(
            user=user,
            phase=p_alg,
            data={"algorithm": alg, "creator": user, "phase": p_alg},
        )
        assert form3.is_valid()

    def test_submission_or_eval_exists_for_image(self):
        user = UserFactory()
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ci1 = ComponentInterfaceFactory()
        ci2 = ComponentInterfaceFactory()
        alg.inputs.set([ci1])
        alg.outputs.set([ci2])
        archive = ArchiveFactory()
        p = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
            archive=archive,
        )
        p.algorithm_inputs.set([ci1])
        p.algorithm_outputs.set([ci2])
        civ = ComponentInterfaceValueFactory(interface=ci1)
        i = ArchiveItemFactory(archive=p.archive)
        i.values.add(civ)

        InvoiceFactory(
            challenge=p.challenge,
            compute_costs_euros=10,
            payment_status=PaymentStatusChoices.COMPLIMENTARY,
        )

        # Fetch from the db to get the cost annotations
        # Maybe this is solved with GeneratedField (Django 5)?
        p = Phase.objects.get(pk=p.pk)

        ai = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=alg,
        )
        AlgorithmJobFactory(algorithm_image=ai, status=4)
        SubmissionFactory(
            phase=p,
            algorithm_image=ai,
        )

        form = SubmissionForm(
            user=user,
            phase=p,
            data={"algorithm": alg, "creator": user, "phase": p},
        )

        assert not form.is_valid()
        assert (
            "A submission for this algorithm container image and model for this phase already exists."
            in form.errors["algorithm"]
        )

        Submission.objects.all().delete()

        EvaluationFactory(submission__algorithm_image=ai)

        form = SubmissionForm(
            user=user,
            phase=p,
            data={"algorithm": alg, "creator": user, "phase": p},
        )

        assert not form.is_valid()
        assert (
            "An evaluation for this algorithm is already in progress for another phase. Please wait for the other evaluation to complete."
            in form.errors["algorithm"]
        )


@pytest.mark.django_db
class TestSubmissionFormOptions:
    def test_no_supplementary_url(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(supplementary_url_choice=Phase.OFF),
        )
        assert "supplementary_url" not in form.fields

    def test_supplementary_url_optional(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(supplementary_url_choice=Phase.OPTIONAL),
        )
        assert "supplementary_url" in form.fields
        assert form.fields["supplementary_url"].required is False

    def test_supplementary_url_required(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(supplementary_url_choice=Phase.REQUIRED),
        )
        assert "supplementary_url" in form.fields
        assert form.fields["supplementary_url"].required is True

    def test_supplementary_url_label(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                supplementary_url_choice=Phase.OPTIONAL,
                supplementary_url_label="TEST",
            ),
        )
        assert form.fields["supplementary_url"].label == "TEST"

    def test_supplementary_url_help_text(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                supplementary_url_choice=Phase.OPTIONAL,
                supplementary_url_help_text="<script>TEST</script>",
            ),
        )
        assert (
            form.fields["supplementary_url"].help_text
            == "&lt;script&gt;TEST&lt;/script&gt;"
        )


def test_algorithm_for_phase_form():
    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory.build(),
        hanging_protocol=HangingProtocolFactory.build(),
        optional_hanging_protocols=[HangingProtocolFactory.build()],
        view_content="{}",
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory.build(),
        inputs=[ComponentInterfaceFactory.build()],
        outputs=[ComponentInterfaceFactory.build()],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=PhaseFactory.build(),
        user=UserFactory.build(),
    )

    assert form.fields["inputs"].disabled
    assert form.fields["outputs"].disabled
    assert form.fields["workstation_config"].disabled
    assert form.fields["hanging_protocol"].disabled
    assert form.fields["optional_hanging_protocols"].disabled
    assert form.fields["view_content"].disabled
    assert form.fields["display_editors"].disabled
    assert form.fields["workstation"].disabled
    assert form.fields["structures"].disabled
    assert form.fields["modalities"].disabled
    assert form.fields["contact_email"].disabled
    assert form.fields["logo"].disabled
    assert form.fields["time_limit"].disabled
    assert not form.fields["title"].disabled
    assert not form.fields["description"].disabled
    assert not form.fields["image_requires_gpu"].disabled
    assert not form.fields["image_requires_memory_gb"].disabled

    assert {
        form.fields["inputs"],
        form.fields["outputs"],
        form.fields["workstation_config"],
        form.fields["hanging_protocol"],
        form.fields["optional_hanging_protocols"],
        form.fields["view_content"],
        form.fields["display_editors"],
        form.fields["workstation"],
        form.fields["structures"],
        form.fields["modalities"],
        form.fields["contact_email"],
        form.fields["logo"],
        form.fields["time_limit"],
    } == {field.field for field in form.hidden_fields()}

    assert {
        form.fields["title"],
        form.fields["description"],
        form.fields["image_requires_gpu"],
        form.fields["image_requires_memory_gb"],
    } == {field.field for field in form.visible_fields()}


@pytest.mark.django_db
def test_algorithm_for_phase_form_validation():
    user = UserFactory()
    phase = PhaseFactory()
    alg1, alg2, alg3 = AlgorithmFactory.create_batch(3)
    ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
    phase.algorithm_inputs.set([ci1, ci2])
    phase.algorithm_outputs.set([ci3, ci4])
    for alg in [alg1, alg2]:
        alg.add_editor(user)
        alg.inputs.set([ci1, ci2])
        alg.outputs.set([ci3, ci4])

    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory(),
        hanging_protocol=HangingProtocolFactory(),
        optional_hanging_protocols=[HangingProtocolFactory()],
        view_content=None,
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory(),
        inputs=[ci1, ci2],
        outputs=[ci3, ci4],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=phase,
        user=user,
        data={
            "title": "foo",
            "image_requires_memory_gb": 10,
        },
    )

    assert not (
        "You have already created the maximum number of algorithms for this phase."
        in str(form.errors)
    )

    alg3.add_editor(user)
    alg3.inputs.set([ci1, ci2])
    alg3.outputs.set([ci3, ci4])

    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory(),
        hanging_protocol=HangingProtocolFactory(),
        optional_hanging_protocols=[HangingProtocolFactory()],
        view_content=None,
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory(),
        inputs=[ci1, ci2],
        outputs=[ci3, ci4],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=phase,
        user=user,
        data={
            "title": "foo",
            "image_requires_memory_gb": 10,
        },
    )

    assert (
        "You have already created the maximum number of algorithms for this phase."
        in str(form.errors)
    )


@pytest.mark.django_db
def test_configure_algorithm_phases_form():
    ch = ChallengeFactory()
    p1, p2, p3 = PhaseFactory.create_batch(
        3, challenge=ch, submission_kind=SubmissionKindChoices.CSV
    )
    PhaseFactory(submission_kind=SubmissionKindChoices.CSV)
    SubmissionFactory(phase=p1)
    MethodFactory(phase=p2)
    PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)

    form = ConfigureAlgorithmPhasesForm(challenge=ch)
    assert list(form.fields["phases"].queryset) == [p3]

    form3 = ConfigureAlgorithmPhasesForm(
        challenge=ch,
        data={
            "phases": [p3],
            "algorithm_inputs": [ci1],
            "algorithm_outputs": [ci2],
        },
    )
    assert form3.is_valid()
