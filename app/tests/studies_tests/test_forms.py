import datetime
import pytest
import pytz
import factory.fuzzy

from tests.factories import UserFactory
from tests.patients_tests.factories import PatientFactory
from tests.studies_tests.factories import StudyFactory
from tests.utils import get_view_for_user

from grandchallenge.subdomains.utils import reverse
from grandchallenge.studies.forms import StudyCreateForm, StudyUpdateForm

"""" Tests the forms available for Study CRUD """


@pytest.mark.django_db
def test_study_display(client):
    study = StudyFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="studies:study-display", user=staff_user
    )
    assert str(study.id) in response.rendered_content


@pytest.mark.django_db
def test_study_create(client):
    staff_user = UserFactory(is_staff=True)
    patient = PatientFactory()
    data = {
        "name": "test",
        "datetime": datetime.datetime(
            1950, 1, 1, 0, 0, 0, 0, pytz.UTC
        ).strftime("%d/%m/%Y %H:%M:%S"),
        "patient": patient.pk,
    }

    form = StudyCreateForm(data=data)
    assert form.is_valid()

    form = StudyCreateForm()
    assert not form.is_valid()

    response = get_view_for_user(
        viewname="studies:study-create",
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_study_update(client):
    staff_user = UserFactory(is_staff=True)
    study = StudyFactory()
    data = {
        "name": "test",
        "datetime": datetime.datetime(
            1950, 1, 1, 0, 0, 0, 0, pytz.UTC
        ).strftime("%d/%m/%Y %H:%M:%S"),
        "patient": study.patient,
    }

    form = StudyUpdateForm(data=data)
    assert form.is_valid()

    form = StudyUpdateForm()
    assert not form.is_valid()

    response = get_view_for_user(
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
        url=reverse("studies:study-update", kwargs={"pk": study.pk}),
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_study_delete(client):
    study = StudyFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client,
        method=client.post,
        user=staff_user,
        url=reverse("studies:study-remove", kwargs={"pk": study.pk}),
    )

    assert response.status_code == 302
