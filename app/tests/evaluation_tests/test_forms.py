import pytest
from factory.django import ImageField

from grandchallenge.algorithms.forms import AlgorithmForPhaseForm
from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.evaluation.forms import SubmissionForm
from grandchallenge.evaluation.models import Phase
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import PaymentStatusChoices
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import (
    UserFactory,
    WorkstationConfigFactory,
    WorkstationFactory,
)
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.invoices_tests.factories import InvoiceFactory
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

    def test_setting_algorithm_image(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
        )

        assert "algorithm_image" in form.fields
        assert "user_upload" not in form.fields

    def test_algorithm_image_queryset(self):
        editor = UserFactory()
        alg1, alg2, alg3 = AlgorithmFactory.create_batch(3)
        alg1.add_editor(editor)
        alg2.add_editor(editor)
        ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
        alg1.inputs.set([ci1, ci2])
        alg1.outputs.set([ci3, ci4])
        alg3.inputs.set([ci1, ci2])
        alg3.outputs.set([ci3, ci4])
        for alg in [alg1, alg2, alg3]:
            AlgorithmImageFactory(algorithm=alg)
            AlgorithmImageFactory(
                algorithm=alg,
                is_in_registry=True,
                is_desired_version=True,
                is_manifest_valid=True,
            )
        p = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
        p.algorithm_inputs.set([ci1, ci2])
        p.algorithm_outputs.set([ci3, ci4])
        form = SubmissionForm(
            user=editor,
            phase=p,
        )

        assert alg1.active_image in form.fields["algorithm_image"].queryset
        assert alg2.active_image not in form.fields["algorithm_image"].queryset
        assert alg3.active_image not in form.fields["algorithm_image"].queryset
        for im in AlgorithmImage.objects.exclude(
            pk__in=[
                alg1.active_image.pk,
                alg2.active_image.pk,
                alg3.active_image.pk,
            ]
        ).all():
            assert im not in form.fields["algorithm_image"].queryset

    def test_no_algorithm_image_selection(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
            data={"algorithm_image": ""},
        )

        assert form.errors["algorithm_image"] == ["This field is required."]

    def test_algorithm_no_permission(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
            data={"algorithm_image": AlgorithmImageFactory()},
        )

        assert form.errors["algorithm_image"] == [
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
        p = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
        )
        p.algorithm_inputs.set([ci1])
        p.algorithm_outputs.set([ci2])

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
            data={"algorithm_image": ai.pk, "creator": user, "phase": p},
        )

        assert form.errors == {}
        assert "algorithm_image" not in form.errors
        assert form.is_valid()

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
