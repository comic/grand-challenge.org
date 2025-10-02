from pathlib import Path

import pytest
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import CharField
from factory.django import ImageField

from grandchallenge.algorithms.forms import (
    AlgorithmForPhaseForm,
    AlgorithmInterfaceForm,
)
from grandchallenge.algorithms.models import Job
from grandchallenge.cases.widgets import FlexibleImageField
from grandchallenge.components.form_fields import (
    INTERFACE_FORM_FIELD_PREFIX,
    FlexibleFileField,
)
from grandchallenge.components.models import (
    ImportStatusChoices,
    InterfaceKindChoices,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.evaluation.forms import (
    AlgorithmInterfaceForPhaseCopyForm,
    ConfigureAlgorithmPhasesForm,
    EvaluationForm,
    EvaluationGroundTruthForm,
    EvaluationGroundTruthVersionManagementForm,
    PhaseUpdateForm,
    SubmissionForm,
)
from grandchallenge.evaluation.models import Evaluation, Phase, Submission
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import (
    PaymentStatusChoices,
    PaymentTypeChoices,
)
from grandchallenge.uploads.models import UserUpload
from grandchallenge.verifications.models import (
    Verification,
    VerificationUserSet,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
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
    EvaluationGroundTruthFactory,
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
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_upload_from_file,
)
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

    def test_confirmation_checkbox_for_external_phases(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(external_evaluation=True),
        )
        assert "confirm_submission" in form.fields
        assert form.fields["confirm_submission"].required

        form2 = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(),
        )
        assert "confirm_submission" not in form2.fields

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
        interface = AlgorithmInterfaceFactory(
            inputs=[ci1, ci2], outputs=[ci3, ci4]
        )
        alg1.interfaces.set([interface])
        alg3.interfaces.set([interface])
        alg4.interfaces.set([interface])
        for alg in [alg1, alg2, alg3]:
            AlgorithmImageFactory(
                algorithm=alg,
                is_in_registry=True,
                is_desired_version=True,
                is_manifest_valid=True,
            )
        AlgorithmImageFactory(algorithm=alg4)
        p = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
        p.algorithm_interfaces.set([interface])
        form = SubmissionForm(
            user=editor,
            phase=p,
        )

        assert alg1 in form.fields["algorithm"].queryset
        assert alg2 not in form.fields["algorithm"].queryset
        assert alg3 not in form.fields["algorithm"].queryset
        assert alg4 not in form.fields["algorithm"].queryset

    def test_algorithm_queryset_if_parent_phase_exists(self):
        editor = UserFactory()
        (
            alg1,
            alg2,
            alg3,
            alg4,
            alg5,
            alg6,
            alg7,
            alg8,
            alg9,
            alg10,
        ) = AlgorithmFactory.create_batch(10)
        ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
        interface = AlgorithmInterfaceFactory(
            inputs=[ci1, ci2], outputs=[ci3, ci4]
        )
        for alg in [
            alg1,
            alg2,
            alg3,
            alg4,
            alg5,
            alg6,
            alg7,
            alg8,
            alg9,
            alg10,
        ]:
            alg.add_editor(editor)
            alg.interfaces.set([interface])
            AlgorithmImageFactory(
                algorithm=alg,
                is_in_registry=True,
                is_desired_version=True,
                is_manifest_valid=True,
            )
        for alg in [alg1, alg2, alg8, alg9]:
            AlgorithmModelFactory(algorithm=alg, is_desired_version=True)
        ai_inactive = AlgorithmImageFactory(
            algorithm=alg6,
        )
        for alg in [alg1, alg2, alg3, alg4, alg6, alg10]:
            AlgorithmJobFactory(
                algorithm_image=alg.active_image,
                algorithm_model=alg.active_model,
                algorithm_interface=interface,
                status=Job.SUCCESS,
                time_limit=alg.time_limit,
            )

        p_parent, p_child = PhaseFactory.create_batch(
            2,
            submission_kind=SubmissionKindChoices.ALGORITHM,
            challenge=ChallengeFactory(),
        )
        for p in [p_parent, p_child]:
            p.algorithm_interfaces.set([interface])
        p_child.parent = p_parent
        p_child.save()

        # successful eval to parent phase with active image and model
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg1.active_image,
            submission__algorithm_model=alg1.active_model,
            status=Evaluation.SUCCESS,
            time_limit=p_parent.evaluation_time_limit,
        )
        # successful eval to parent phase with active image, but not active model
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg2.active_image,
            status=Evaluation.SUCCESS,
            time_limit=p_parent.evaluation_time_limit,
        )
        # successful eval to other phase with active image
        other_phase = PhaseFactory()
        EvaluationFactory(
            submission__phase=other_phase,
            submission__algorithm_image=alg3.active_image,
            status=Evaluation.SUCCESS,
            time_limit=other_phase.evaluation_time_limit,
        )
        # failed eval to parent phase with active image
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg4.active_image,
            status=Evaluation.FAILURE,
            time_limit=p_parent.evaluation_time_limit,
        )
        # successful eval to parent phase with active image, but no successful job
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg5.active_image,
            status=Evaluation.SUCCESS,
            time_limit=p_parent.evaluation_time_limit,
        )
        # successful eval to parent phase with active image, but not active model
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=ai_inactive,
            status=Evaluation.SUCCESS,
            time_limit=p_parent.evaluation_time_limit,
        )
        # successful eval to parent phase with active image but failed job
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg7.active_image,
            submission__algorithm_model=alg7.active_model,
            status=Evaluation.SUCCESS,
            time_limit=p_parent.evaluation_time_limit,
        )
        AlgorithmJobFactory(
            algorithm_image=alg.active_image,
            algorithm_model=alg.active_model,
            algorithm_interface=interface,
            status=Job.FAILURE,
            time_limit=alg.time_limit,
        )
        # successful eval to parent phase with active image but successful job with different image
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg8.active_image,
            submission__algorithm_model=alg8.active_model,
            status=Evaluation.SUCCESS,
            time_limit=p_parent.evaluation_time_limit,
        )
        AlgorithmJobFactory(
            algorithm_image=AlgorithmImageFactory(algorithm=alg8),
            algorithm_model=alg.active_model,
            algorithm_interface=interface,
            status=Job.SUCCESS,
            time_limit=alg.time_limit,
        )
        # successful eval to parent phase with active image but successful job with different model
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg9.active_image,
            submission__algorithm_model=alg9.active_model,
            status=Evaluation.SUCCESS,
            time_limit=p_parent.evaluation_time_limit,
        )
        AlgorithmJobFactory(
            algorithm_image=alg9.active_image,
            algorithm_model=AlgorithmModelFactory(algorithm=alg9),
            algorithm_interface=interface,
            status=Job.SUCCESS,
            time_limit=alg9.time_limit,
        )
        # successful evaluation and job, no algorithm model, but that should not matter
        EvaluationFactory(
            submission__phase=p_parent,
            submission__algorithm_image=alg10.active_image,
            submission__algorithm_model=alg10.active_model,
            status=Evaluation.SUCCESS,
            time_limit=p_parent.evaluation_time_limit,
        )

        form = SubmissionForm(
            user=editor,
            phase=p,
        )

        assert alg1 in form.fields["algorithm"].queryset
        assert alg10 in form.fields["algorithm"].queryset
        assert alg2 not in form.fields["algorithm"].queryset
        assert alg3 not in form.fields["algorithm"].queryset
        assert alg4 not in form.fields["algorithm"].queryset
        assert alg5 not in form.fields["algorithm"].queryset
        assert alg6 not in form.fields["algorithm"].queryset
        assert alg7 not in form.fields["algorithm"].queryset
        assert alg8 not in form.fields["algorithm"].queryset
        assert alg9 not in form.fields["algorithm"].queryset

    def test_no_algorithm_selection(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
            data={"algorithm": ""},
        )

        assert form.errors["algorithm"] == ["This field is required."]

    @pytest.mark.parametrize(
        "submission_kind,disabled_field_name",
        (
            [SubmissionKindChoices.CSV, "user_upload"],
            [SubmissionKindChoices.ALGORITHM, "algorithm"],
        ),
    )
    def test_no_submission_possible_without_method(
        self, submission_kind, disabled_field_name
    ):
        phase = PhaseFactory(submission_kind=submission_kind)
        form = SubmissionForm(
            user=UserFactory(),
            phase=phase,
            data={"creator": UserFactory(), "phase": phase},
        )
        assert form.fields[disabled_field_name].disabled
        assert not form.is_valid()
        assert (
            "You cannot submit to this phase because this phase does "
            "not have an active evaluation method yet." in str(form.errors)
        )

        # for external eval phase, this check is skipped
        phase.external_evaluation = True
        phase.save()

        form = SubmissionForm(
            user=UserFactory(),
            phase=phase,
            data={"creator": UserFactory(), "phase": phase},
        )
        assert not form.is_valid()
        if submission_kind == SubmissionKindChoices.ALGORITHM:
            assert not form.fields[disabled_field_name].disabled
        assert (
            "You cannot submit to this phase because this phase does "
            "not have an active evaluation method yet." not in str(form.errors)
        )

        # reset and add method
        MethodFactory(
            phase=phase,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        del phase.active_image
        phase.external_evaluation = False
        phase.save()

        form = SubmissionForm(
            user=UserFactory(),
            phase=phase,
            data={"creator": UserFactory(), "phase": phase},
        )
        assert not form.is_valid()
        assert not form.fields[disabled_field_name].disabled
        assert (
            "You cannot submit to this phase because this phase does "
            "not have an active evaluation method yet." not in str(form.errors)
        )

    def test_algorithm_no_permission(self):
        phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
        MethodFactory(
            phase=phase,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        form = SubmissionForm(
            user=UserFactory(),
            phase=phase,
            data={"algorithm": AlgorithmFactory()},
        )

        assert form.errors["algorithm"] == [
            "Select a valid choice. That choice is not one of the available choices."
        ]

    def test_algorithm_with_permission(self):
        user = UserFactory()
        VerificationFactory(user=user, is_verified=True)
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ci1 = ComponentInterfaceFactory()
        ci2 = ComponentInterfaceFactory()
        interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])
        alg.interfaces.set([interface])
        archive = ArchiveFactory()
        p = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
            archive=archive,
        )
        p.algorithm_interfaces.set([interface])
        civ = ComponentInterfaceValueFactory(interface=ci1)
        i = ArchiveItemFactory(archive=p.archive)
        i.values.add(civ)

        InvoiceFactory(
            challenge=p.challenge,
            compute_costs_euros=10,
            payment_type=PaymentTypeChoices.COMPLIMENTARY,
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
        AlgorithmJobFactory(
            algorithm_image=ai,
            algorithm_interface=interface,
            status=4,
            time_limit=ai.algorithm.time_limit,
        )
        MethodFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            phase=p,
        )

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
        VerificationFactory(user=user, is_verified=True)
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ci1 = ComponentInterfaceFactory()
        ci2 = ComponentInterfaceFactory()
        interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])
        alg.interfaces.set([interface])
        archive = ArchiveFactory()
        p = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
            archive=archive,
        )
        p.algorithm_interfaces.set([interface])
        civ = ComponentInterfaceValueFactory(interface=ci1)
        i = ArchiveItemFactory(archive=p.archive)
        i.values.add(civ)

        InvoiceFactory(
            challenge=p.challenge,
            compute_costs_euros=10,
            payment_type=PaymentTypeChoices.COMPLIMENTARY,
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
        AlgorithmJobFactory(
            algorithm_image=ai,
            algorithm_interface=interface,
            status=Job.SUCCESS,
            time_limit=ai.algorithm.time_limit,
        )
        MethodFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            phase=p,
        )

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
            phase=PhaseFactory(),
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
            submissions_limit_per_user_per_period=10,
        )
        InvoiceFactory(
            challenge=phase.challenge,
            compute_costs_euros=10,
            payment_type=PaymentTypeChoices.COMPLIMENTARY,
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
        VerificationFactory(user=user, is_verified=True)
        p_pred = PhaseFactory(
            submission_kind=SubmissionKindChoices.CSV,
            submissions_limit_per_user_per_period=10,
        )
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ci1 = ComponentInterfaceFactory()
        ci2 = ComponentInterfaceFactory()
        interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])
        alg.interfaces.set([interface])
        archive = ArchiveFactory()
        p_alg = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
            archive=archive,
        )
        p_alg.algorithm_interfaces.set([interface])
        MethodFactory(
            phase=p_alg,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        MethodFactory(
            phase=p_pred,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        for p in [p_alg, p_pred]:
            InvoiceFactory(
                challenge=p.challenge,
                compute_costs_euros=10,
                payment_type=PaymentTypeChoices.COMPLIMENTARY,
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
        AlgorithmJobFactory(
            algorithm_image=ai,
            algorithm_interface=interface,
            status=4,
            time_limit=ai.algorithm.time_limit,
        )

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

        # for external evaluation phases, this check is not done
        p_alg.external_evaluation = True
        p_alg.save()

        form3 = SubmissionForm(
            user=user,
            phase=p_alg,
            data={
                "algorithm": alg,
                "creator": user,
                "phase": p_alg,
                "confirm_submission": True,
            },
        )
        assert form3.is_valid()

        # reset
        p_alg.external_evaluation = False
        p_alg.save()

        civ = ComponentInterfaceValueFactory(interface=ci1)
        i = ArchiveItemFactory(archive=p_alg.archive)
        i.values.add(civ)

        form4 = SubmissionForm(
            user=user,
            phase=p_alg,
            data={"algorithm": alg, "creator": user, "phase": p_alg},
        )
        assert form4.is_valid()

    def test_submission_or_eval_exists_for_image(self):
        user = UserFactory()
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ci1 = ComponentInterfaceFactory()
        ci2 = ComponentInterfaceFactory()
        interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])
        alg.interfaces.set([interface])
        archive = ArchiveFactory()
        p = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
            archive=archive,
        )
        p.algorithm_interfaces.set([interface])
        civ = ComponentInterfaceValueFactory(interface=ci1)
        i = ArchiveItemFactory(archive=p.archive)
        i.values.add(civ)

        InvoiceFactory(
            challenge=p.challenge,
            compute_costs_euros=10,
            payment_type=PaymentTypeChoices.COMPLIMENTARY,
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
        AlgorithmJobFactory(
            algorithm_image=ai,
            algorithm_interface=interface,
            status=4,
            time_limit=ai.algorithm.time_limit,
        )
        SubmissionFactory(
            phase=p,
            algorithm_image=ai,
        )
        MethodFactory(
            phase=p,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
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

        EvaluationFactory(
            submission__algorithm_image=ai,
            time_limit=p.evaluation_time_limit,
        )

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

    @pytest.mark.parametrize(
        "model_active, submission_with_model_present, form_is_valid",
        (
            [True, True, False],
            [True, False, True],
            [False, True, True],
            [False, False, False],
        ),
    )
    def test_eval_exists_for_image_and_model(
        self, model_active, submission_with_model_present, form_is_valid
    ):
        user = UserFactory()
        VerificationFactory(user=user, is_verified=True)
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ci1 = ComponentInterfaceFactory()
        ci2 = ComponentInterfaceFactory()
        interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])
        alg.interfaces.set([interface])
        archive = ArchiveFactory()
        p = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
            archive=archive,
        )
        p.algorithm_interfaces.set([interface])
        civ = ComponentInterfaceValueFactory(interface=ci1)
        i = ArchiveItemFactory(archive=p.archive)
        i.values.add(civ)

        InvoiceFactory(
            challenge=p.challenge,
            compute_costs_euros=10,
            payment_type=PaymentTypeChoices.COMPLIMENTARY,
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
        am = AlgorithmModelFactory(
            is_desired_version=model_active, algorithm=alg
        )
        # create submission
        SubmissionFactory(
            phase=p,
            algorithm_image=ai,
            algorithm_model=am if submission_with_model_present else None,
        )
        MethodFactory(
            phase=p,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        form = SubmissionForm(
            user=user,
            phase=p,
            data={"algorithm": alg, "creator": user, "phase": p},
        )

        assert form.is_valid() == form_is_valid
        if not form_is_valid:
            assert (
                "A submission for this algorithm container image and model for this phase already exists."
                in str(form.errors)
            )

    def test_submission_to_external_phase_requires_confirmation(self):
        user = UserFactory()
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        ai = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=alg,
        )
        phase = PhaseFactory(external_evaluation=True)
        SubmissionFactory(
            phase=phase,
            algorithm_image=ai,
        )
        InvoiceFactory(
            challenge=phase.challenge,
            compute_costs_euros=10,
            payment_type=PaymentTypeChoices.COMPLIMENTARY,
        )
        phase = Phase.objects.get(pk=phase.pk)
        form = SubmissionForm(
            user=user,
            phase=phase,
            data={"algorithm": alg, "creator": user, "phase": phase},
        )
        assert not form.is_valid()
        assert (
            "You must confirm that you want to submit to this phase."
            in str(form.errors)
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
        interfaces=[AlgorithmInterfaceFactory.build()],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=PhaseFactory.build(),
        user=UserFactory.build(),
    )

    assert form.fields["interfaces"].disabled
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
    assert not form.fields["job_requires_gpu_type"].disabled
    assert form.fields["job_requires_memory_gb"].disabled

    assert {
        form.fields["interfaces"],
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
        form.fields["job_requires_memory_gb"],
    } == {field.field for field in form.hidden_fields()}

    assert {
        form.fields["title"],
        form.fields["description"],
        form.fields["job_requires_gpu_type"],
    } == {field.field for field in form.visible_fields()}


@pytest.mark.django_db
def test_algorithm_for_phase_form_validation():
    user = UserFactory()
    phase = PhaseFactory()
    alg1, alg2, alg3 = AlgorithmFactory.create_batch(3)
    ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)

    interface = AlgorithmInterfaceFactory(
        inputs=[ci1, ci2], outputs=[ci3, ci4]
    )

    phase.algorithm_interfaces.set([interface])
    for alg in [alg1, alg2]:
        alg.add_editor(user)
        alg.interfaces.set([interface])

    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory(),
        hanging_protocol=HangingProtocolFactory(),
        optional_hanging_protocols=[HangingProtocolFactory()],
        view_content=None,
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory(),
        interfaces=[interface],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=phase,
        user=user,
        data={
            "title": "foo",
        },
    )

    assert not (
        "You have already created the maximum number of algorithms for this phase."
        in str(form.errors)
    )

    alg3.add_editor(user)
    alg3.interfaces.set([interface])

    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory(),
        hanging_protocol=HangingProtocolFactory(),
        optional_hanging_protocols=[HangingProtocolFactory()],
        view_content=None,
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory(),
        interfaces=[interface],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
        phase=phase,
        user=user,
        data={
            "title": "foo",
        },
    )

    assert (
        "You have already created the maximum number of algorithms for this phase."
        in str(form.errors)
    )


@pytest.mark.django_db
def test_user_algorithms_for_phase():
    def populate_form(interfaces):
        return AlgorithmForPhaseForm(
            workstation_config=WorkstationConfigFactory(),
            hanging_protocol=HangingProtocolFactory(),
            optional_hanging_protocols=[HangingProtocolFactory()],
            view_content=None,
            display_editors=True,
            contact_email="test@test.com",
            workstation=WorkstationFactory(),
            interfaces=interfaces,
            structures=[],
            modalities=[],
            logo=ImageField(filename="test.jpeg"),
            phase=phase,
            user=user,
            data={
                "title": "foo",
            },
        )

    user = UserFactory()
    phase = PhaseFactory()
    alg1, alg2, alg3, alg4, alg5 = AlgorithmFactory.create_batch(5)
    ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)

    interface1 = AlgorithmInterfaceFactory(
        inputs=[ci1, ci2], outputs=[ci3, ci4]
    )
    interface2 = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci3])
    interface3 = AlgorithmInterfaceFactory(inputs=[ci3], outputs=[ci1, ci4])
    interface4 = AlgorithmInterfaceFactory(inputs=[ci2], outputs=[ci1, ci2])

    for alg in [alg1, alg2, alg3, alg4, alg5]:
        alg.add_editor(user)

    # phase has 2 interfaces
    phase.algorithm_interfaces.set([interface1, interface2])
    # only algorithms that have at least these two interfaces set should match
    alg1.interfaces.set([interface1, interface2])  # exact match
    alg2.interfaces.set(
        [interface3, interface4]
    )  # same number of interfaces, but different interfaces
    alg3.interfaces.set(
        [interface1, interface2, interface3]
    )  # required interfaces, plus additional interface
    alg4.interfaces.set(
        [interface1]
    )  # only 1, partially overlapping interface

    form = populate_form(interfaces=phase.algorithm_interfaces.all())
    assert set(form.user_algorithms_for_phase) == {alg1, alg3}

    # user needs to be owner of algorithm
    alg3.remove_editor(user)
    form = populate_form(interfaces=phase.algorithm_interfaces.all())
    assert set(form.user_algorithms_for_phase) == {alg1}


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

    form = ConfigureAlgorithmPhasesForm(challenge=ch)
    assert list(form.fields["phases"].queryset) == [p3]

    form3 = ConfigureAlgorithmPhasesForm(
        challenge=ch,
        data={
            "phases": [p3],
        },
    )
    assert form3.is_valid()


@pytest.mark.django_db
def test_ground_truth_form():
    user = UserFactory()
    phase = PhaseFactory()
    user_upload = UserUploadFactory(creator=user)
    user_upload.status = user_upload.StatusChoices.COMPLETED
    user_upload.save()

    form = EvaluationGroundTruthForm(
        user=user,
        phase=phase,
        data={"user_upload": user_upload, "creator": user, "phase": phase},
    )
    assert not form.is_valid()
    assert "This upload is not a valid .tar.gz file" in str(form.errors)
    assert "Select a valid choice" in str(form.errors["creator"])

    Verification.objects.create(user=user, is_verified=True)
    upload = create_upload_from_file(
        creator=user,
        file_path=Path(__file__).parent / "resources" / "ground-truth.tar.gz",
    )
    EvaluationGroundTruthFactory(creator=user)

    form2 = EvaluationGroundTruthForm(
        user=user,
        phase=phase,
        data={"user_upload": upload, "creator": user, "phase": phase},
    )
    assert not form2.is_valid()
    assert (
        "You have an existing ground truth importing, please wait for it to complete"
        in str(form2.errors)
    )


@pytest.mark.django_db
def test_ground_truth_version_management_form():
    phase = PhaseFactory()
    admin = UserFactory()
    phase.challenge.add_admin(admin)

    gt1 = EvaluationGroundTruthFactory(
        phase=phase,
        is_desired_version=True,
        import_status=ImportStatusChoices.COMPLETED,
    )
    gt2 = EvaluationGroundTruthFactory(
        phase=phase,
        is_desired_version=False,
        import_status=ImportStatusChoices.COMPLETED,
    )
    gt3 = EvaluationGroundTruthFactory(
        phase=phase,
        is_desired_version=True,
        import_status=ImportStatusChoices.FAILED,
    )
    _ = EvaluationGroundTruthFactory(
        phase=phase,
        is_desired_version=False,
        import_status=ImportStatusChoices.FAILED,
    )

    form = EvaluationGroundTruthVersionManagementForm(
        user=admin, phase=phase, activate=True
    )
    assert {*form.fields["ground_truth"].queryset} == {gt2}

    form2 = EvaluationGroundTruthVersionManagementForm(
        user=admin, phase=phase, activate=False
    )
    assert {*form2.fields["ground_truth"].queryset} == {gt1, gt3}

    EvaluationGroundTruthFactory(phase=phase, is_desired_version=False)

    form3 = EvaluationGroundTruthVersionManagementForm(
        user=admin, phase=phase, activate=True, data={"ground_truth": gt2.pk}
    )
    assert not form3.is_valid()
    assert "Ground truth updating already in progress" in str(
        form3.errors["ground_truth"]
    )


@pytest.mark.django_db
def test_submission_limit_avoidance_users():
    phase = PhaseFactory(submissions_limit_per_user_per_period=1)
    user = UserFactory()

    o1, o2, o3, o4, ch_admin = UserFactory.create_batch(5)

    phase.challenge.add_admin(user=ch_admin)

    # Should be included but allow for challenge admins
    VerificationUserSet.objects.create(is_false_positive=False).users.set(
        [user, o1, ch_admin]
    )

    # These should be ignored
    VerificationUserSet.objects.create(is_false_positive=True).users.set(
        [user, o2]
    )
    VerificationUserSet.objects.create(is_false_positive=True).users.set([o3])
    VerificationUserSet.objects.create(is_false_positive=False).users.set([o4])

    form = SubmissionForm(user=user, phase=phase)

    relevant_users = form._get_submission_relevant_users(creator=user)

    assert {o1} == set(relevant_users)


@pytest.mark.django_db
def test_phase_update_form_gpu_limited_choices():
    phase = PhaseFactory()
    form = PhaseUpdateForm(
        instance=phase, challenge=phase.challenge, user=UserFactory()
    )

    validators = form.fields["evaluation_requires_memory_gb"].validators

    min_validator = next(
        (v for v in validators if isinstance(v, MinValueValidator)), None
    )
    assert min_validator is not None
    assert min_validator.limit_value == 4

    max_validator = next(
        (v for v in validators if isinstance(v, MaxValueValidator)), None
    )
    assert max_validator is not None
    assert max_validator.limit_value == 32


@pytest.mark.django_db
def test_phase_update_form_gpu_type_limited_choices():
    phase = PhaseFactory()
    form = PhaseUpdateForm(
        instance=phase, challenge=phase.challenge, user=UserFactory()
    )

    choices = form.fields["evaluation_requires_gpu_type"].widget.choices

    assert choices is not None
    choice = GPUTypeChoices.NO_GPU
    assert (choice.value, choice.label) in choices
    choice = GPUTypeChoices.V100
    assert (choice.value, choice.label) not in choices


@pytest.mark.django_db
def test_phase_update_form_gpu_type_with_additional_selectable_gpu_types():
    phase = PhaseFactory()
    phase.evaluation_selectable_gpu_type_choices = ["V100"]
    form = PhaseUpdateForm(
        instance=phase, challenge=phase.challenge, user=UserFactory()
    )

    choices = form.fields["evaluation_requires_gpu_type"].widget.choices

    assert choices is not None
    choice = GPUTypeChoices.V100
    assert (choice.value, choice.label) in choices


@pytest.mark.django_db
def test_additional_inputs_on_submission_form():
    phase = PhaseFactory()
    ci_img = ComponentInterfaceFactory(kind=InterfaceKindChoices.PANIMG_IMAGE)
    ci_str = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    ci_file = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.ANY, store_in_database=False
    )
    phase.additional_evaluation_inputs.set([ci_img, ci_str, ci_file])

    form = SubmissionForm(
        user=UserFactory(),
        phase=phase,
    )

    assert isinstance(
        form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}{ci_img.slug}"],
        FlexibleImageField,
    )
    assert isinstance(
        form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}{ci_file.slug}"],
        FlexibleFileField,
    )
    assert isinstance(
        form.fields[f"{INTERFACE_FORM_FIELD_PREFIX}{ci_str.slug}"], CharField
    )


@pytest.mark.django_db
def test_disjoint_algorithm_interface_sockets_and_evaluation_inputs():
    ci1, ci2, ci3, ci4 = ComponentInterfaceFactory.create_batch(4)
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
    phase.additional_evaluation_inputs.set([ci1, ci2])

    form = AlgorithmInterfaceForm(
        base_obj=phase, data={"inputs": [ci1, ci3], "outputs": [ci2, ci4]}
    )
    assert not form.is_valid()
    assert (
        f"The following sockets are already configured as additional inputs or outputs on "
        f"{phase}: {ci1}" in str(form.errors["inputs"])
    )
    assert (
        f"The following sockets are already configured as additional inputs or outputs on "
        f"{phase}: {ci2}" in str(form.errors["outputs"])
    )


@pytest.mark.parametrize(
    "select_interfaces, form_valid",
    (
        [[0, 1, 2], True],  # full match
        [[0, 1], False],  # different number, partially overlapping
        [[0, 1, 3], False],  # same number, partially overlapping
    ),
)
@pytest.mark.django_db
def test_reschedule_evaluation_requires_matching_algorithm_interfaces(
    select_interfaces, form_valid
):
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
    archive = ArchiveFactory()
    phase.archive = archive
    phase.save()

    int1, int2, int3, int4 = AlgorithmInterfaceFactory.create_batch(4)
    interfaces = [int1, int2, int3, int4]
    phase.algorithm_interfaces.set(interfaces[0:3])

    user = UserFactory()
    phase.challenge.add_admin(user)
    InvoiceFactory(
        challenge=phase.challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    method = MethodFactory(
        phase=phase,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )

    algorithm = AlgorithmFactory()
    algorithm.interfaces.set([interfaces[i] for i in select_interfaces])
    algorithm.add_editor(user)
    ai = AlgorithmImageFactory(algorithm=algorithm)

    submission = SubmissionFactory(
        phase=phase, creator=user, algorithm_image=ai
    )
    EvaluationFactory(
        submission=submission,
        method=method,
        status=Evaluation.SUCCESS,
        time_limit=10,
    )

    form = EvaluationForm(submission=submission, user=user, data={})

    assert form.is_valid() == form_valid
    if not form_valid:
        assert (
            "The algorithm interfaces do not match those defined for the phase."
            in str(form.errors)
        )


@pytest.mark.django_db
def test_phase_copy_algorithm_interfaces():
    challenge = ChallengeFactory()

    source_phase = PhaseFactory(challenge=challenge)
    ai1 = AlgorithmInterfaceFactory()
    source_phase.algorithm_interfaces.set([ai1])

    target_phase = PhaseFactory(challenge=challenge)

    assert (
        not target_phase.algorithm_interfaces.exists()
    ), "Sanity: no algorithm interfaces to start with"

    form = AlgorithmInterfaceForPhaseCopyForm(
        phase=source_phase,
        data={
            "phases": [
                target_phase.pk,
            ],
        },
    )

    assert form.is_valid()
    form.copy_algorithm_interfaces()

    assert (
        target_phase.algorithm_interfaces.get() == ai1
    ), "Algorithm interface copied correctly"

    # Can run it multiple times without trouble
    form.copy_algorithm_interfaces()
    assert (
        target_phase.algorithm_interfaces.get() == ai1
    ), "Running multiple times does not duplicate interfaces"

    # Existing interfaces pose no problem
    ai2 = AlgorithmInterfaceFactory()
    target_phase.algorithm_interfaces.set([ai2])

    form = AlgorithmInterfaceForPhaseCopyForm(
        phase=source_phase,
        data={
            "phases": [
                target_phase.pk,
            ],
        },
    )
    assert form.is_valid()
    form.copy_algorithm_interfaces()

    assert set(target_phase.algorithm_interfaces.all()) == {ai1, ai2}

    parent_phase = PhaseFactory(challenge=challenge)
    target_phase.parent = parent_phase
    target_phase.save()

    assert (
        target_phase.algorithm_interfaces_locked
    ), "Sanity: interfaces locked"

    form = AlgorithmInterfaceForPhaseCopyForm(
        phase=source_phase,
        data={
            "phases": [
                target_phase.pk,
            ],
        },
    )
    assert (
        not form.is_valid()
    ), "Locked interfaces on a selected phase invalides the form"


@pytest.mark.django_db
def test_reevaluation_blocked_when_pending_evaluation_exists():
    algorithm_image = AlgorithmImageFactory()
    user = UserFactory()
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)

    EvaluationFactory(
        time_limit=10,
        submission__algorithm_image=algorithm_image,
        status=Evaluation.PENDING,
    )
    sub = SubmissionFactory(
        phase=phase, algorithm_image=algorithm_image, creator=user
    )
    form = EvaluationForm(
        submission=sub,
        user=user,
        data={},
    )

    assert not form.is_valid()
    assert "An evaluation for this algorithm is already in progress." in str(
        form.errors
    )


@pytest.mark.django_db
def test_reschedule_evaluation_not_possible_for_external_evaluations():
    phase = PhaseFactory(external_evaluation=True)

    user = UserFactory()
    phase.challenge.add_admin(user)
    InvoiceFactory(
        challenge=phase.challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    method = MethodFactory(
        phase=phase,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )

    submission = SubmissionFactory(
        phase=phase,
        creator=user,
    )
    EvaluationFactory(
        submission=submission,
        method=method,
        status=Evaluation.SUCCESS,
        time_limit=10,
    )

    form = EvaluationForm(submission=submission, user=user, data={})

    assert not form.is_valid()
    assert "You cannot re-evaluate an external evaluation." in str(form.errors)
