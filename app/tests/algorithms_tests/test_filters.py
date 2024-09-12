import pytest
from rest_framework.test import force_authenticate

from grandchallenge.algorithms.views import JobViewSet
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.factories import ImageFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_job_list_is_filtered_on_permissions(client):
    j1 = AlgorithmJobFactory(time_limit=60)
    j2 = AlgorithmJobFactory(time_limit=60)
    j1viewer = UserFactory()
    j2viewer = UserFactory()
    non_viewer = UserFactory()
    both_viewer = UserFactory()
    j1.viewers.user_set.add(both_viewer, j1viewer)
    j2.viewers.user_set.add(both_viewer, j2viewer)
    tests = [
        ([], [j1, j2], non_viewer),
        ([j1], [j2], j1viewer),
        ([j2], [j1], j2viewer),
        ([j1, j2], [], both_viewer),
    ]
    for test in tests:
        response = get_view_for_user(
            url=reverse("api:algorithms-job-list"), client=client, user=test[2]
        )
        for job_object in test[0]:
            assert str(job_object.pk) in str(response.rendered_content)
        for job_object in test[1]:
            assert str(job_object.pk) not in str(response.rendered_content)


@pytest.mark.django_db
def test_job_list_is_filtered_on_images(client, rf):
    im1 = ImageFactory()
    civ1 = ComponentInterfaceValueFactory(image=im1)
    im2 = ImageFactory()
    civ2 = ComponentInterfaceValueFactory(image=im2)

    j1 = AlgorithmJobFactory(time_limit=60)
    j1.inputs.add(civ1)
    j1.outputs.add(civ2)
    j2 = AlgorithmJobFactory(time_limit=60)
    j2.inputs.add(civ2)
    j3 = AlgorithmJobFactory(time_limit=60)
    j3.outputs.add(civ2)
    u = UserFactory()
    for j in (j1, j2, j3):
        j.viewers.user_set.add(u)
    tests = [
        ([j1, j2, j3], [], u, ""),
        ([j1], [j2, j3], u, f"?input_image={str(im1.pk)}"),
        ([j2], [j1, j3], u, f"?input_image={str(im2.pk)}"),
        ([j1, j3], [j2], u, f"?output_image={str(im2.pk)}"),
        (
            [j1],
            [j2, j3],
            u,
            f"?output_image={str(im2.pk)}&input_image={im1.pk}",
        ),
    ]
    for test in tests:
        url = reverse("api:algorithms-job-list") + test[3]
        request = rf.get(url)
        force_authenticate(request, user=u)
        view = JobViewSet.as_view(actions={"get": "list"})
        response = view(request)
        for job_object in test[0]:
            assert str(job_object.pk) in str(response.rendered_content)
        for job_object in test[1]:
            assert str(job_object.pk) not in str(response.rendered_content)
