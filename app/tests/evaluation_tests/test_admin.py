import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.evaluation.admin import (
    ConfigureAlgorithmPhasesForm,
    PhaseAdmin,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.archives_tests.factories import ArchiveFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import PhaseFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_disjoint_interfaces():
    i = ComponentInterfaceFactory()
    form = PhaseAdmin.form(
        data={"algorithm_inputs": [i.pk], "algorithm_outputs": [i.pk]}
    )
    assert form.is_valid() is False
    assert (
        "The sets of Algorithm Inputs and Algorithm Outputs must be unique"
        in str(form.errors)
    )


@pytest.mark.django_db
def test_configure_algorithm_phases_form():
    p1, p2 = PhaseFactory.create_batch(
        2, submission_kind=SubmissionKindChoices.CSV
    )
    p_alg = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
    _ = ArchiveFactory(title=f"{p1.challenge.short_name}-{p1.title}-dataset")
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)

    form = ConfigureAlgorithmPhasesForm(
        data={
            "phases": [p1, p2, p_alg],
            "algorithm_inputs": [ci1],
            "algorithm_outputs": [ci2],
        }
    )
    assert form.is_valid() is False
    assert f"{p_alg.pk} is not one of the available choices" in str(
        form.errors["phases"]
    )

    form2 = ConfigureAlgorithmPhasesForm(
        data={
            "phases": [p1, p2],
            "algorithm_inputs": [ci1],
            "algorithm_outputs": [ci2],
        }
    )
    assert form2.is_valid() is False
    assert f"Archive for {p1} already exists"

    form3 = ConfigureAlgorithmPhasesForm(
        data={
            "phases": [p2],
            "algorithm_inputs": [ci1],
            "algorithm_outputs": [ci2],
        }
    )
    assert form3.is_valid()


@pytest.mark.django_db
def test_configure_algorithm_phases_admin_view_permissions(
    client, authenticated_staff_user
):
    response = get_view_for_user(
        viewname="admin:algorithm_phase_create",
        client=client,
        user=authenticated_staff_user,
    )
    assert response.status_code == 403

    assign_perm(
        "evaluation.configure_algorithm_phase", authenticated_staff_user
    )
    response = get_view_for_user(
        viewname="admin:algorithm_phase_create",
        client=client,
        user=authenticated_staff_user,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_configure_algorithm_phases_admin_view(
    client, authenticated_staff_user
):
    p1, p2 = PhaseFactory.create_batch(
        2, submission_kind=SubmissionKindChoices.CSV
    )
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)

    assign_perm(
        "evaluation.configure_algorithm_phase", authenticated_staff_user
    )
    response = get_view_for_user(
        viewname="admin:algorithm_phase_create",
        client=client,
        method=client.post,
        user=authenticated_staff_user,
        data={
            "phases": [p1.pk, p2.pk],
            "algorithm_inputs": [ci1.pk],
            "algorithm_outputs": [ci2.pk],
        },
    )
    assert response.status_code == 302
    for phase in [p1, p2]:
        phase.refresh_from_db()
        assert phase.submission_kind == SubmissionKindChoices.ALGORITHM
        assert phase.creator_must_be_verified
        assert (
            phase.archive.title
            == f"{phase.challenge.short_name} {phase.title} dataset"
        )
        assert list(phase.algorithm_inputs.all()) == [ci1]
        assert list(phase.algorithm_outputs.all()) == [ci2]
