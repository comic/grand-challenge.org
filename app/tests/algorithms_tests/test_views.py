import datetime
import json
import tempfile
from pathlib import Path

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.text import slugify
from django_capture_on_commit_callbacks import capture_on_commit_callbacks
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.cases.widgets import WidgetChoices
from grandchallenge.components.models import ComponentInterface, InterfaceKind
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.cases_tests import RESOURCE_PATH
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_upload_from_file,
)
from tests.utils import get_view_for_user, recurse_callbacks
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_create_link_view(client, settings):
    user = UserFactory()

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )
    assert reverse("algorithms:create") not in response.rendered_content

    g = Group.objects.get(name=settings.ALGORITHMS_CREATORS_GROUP_NAME)
    g.user_set.add(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )
    assert reverse("algorithms:create") in response.rendered_content


@pytest.mark.django_db
def test_algorithm_list_view(client):
    alg1, alg2 = AlgorithmFactory(), AlgorithmFactory()
    user = UserFactory()

    alg1.add_user(user)
    alg2.add_user(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert alg1.get_absolute_url() in response.rendered_content
    assert alg2.get_absolute_url() in response.rendered_content

    alg1.remove_user(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert alg1.get_absolute_url() not in response.rendered_content
    assert alg2.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_algorithm_list_view_filter(client):
    user = UserFactory()
    alg1, alg2, pubalg = (
        AlgorithmFactory(),
        AlgorithmFactory(),
        AlgorithmFactory(public=True),
    )
    alg1.add_user(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert response.status_code == 200
    assert alg1.get_absolute_url() in response.rendered_content
    assert alg2.get_absolute_url() not in response.rendered_content
    assert pubalg.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_algorithm_image_create_link_view(client):
    alg = AlgorithmFactory()
    expected_url = reverse(
        "algorithms:image-create", kwargs={"slug": alg.slug}
    )
    user = UserFactory()

    alg.add_user(user)

    response = get_view_for_user(
        viewname="algorithms:detail",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 200
    assert expected_url not in response.rendered_content

    alg.add_editor(user)

    response = get_view_for_user(
        viewname="algorithms:detail",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 200
    assert expected_url in response.rendered_content


@pytest.mark.django_db
def test_algorithm_image_create_detail(client):
    user = UserFactory()
    VerificationFactory(user=user, is_verified=True)
    algorithm = AlgorithmFactory()
    algorithm.add_editor(user)

    algorithm_image = UserUploadFactory(
        filename="test_image.tar.gz", creator=user
    )
    algorithm_image.status = algorithm_image.StatusChoices.COMPLETED
    algorithm_image.save()

    response = get_view_for_user(
        client=client,
        viewname="algorithms:image-create",
        reverse_kwargs={"slug": algorithm.slug},
        user=user,
    )
    assert response.status_code == 200

    assert AlgorithmImage.objects.all().count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="algorithms:image-create",
        reverse_kwargs={"slug": algorithm.slug},
        user=user,
        data={
            "user_upload": algorithm_image.pk,
            "requires_memory_gb": 24,
            "creator": user.pk,
            "algorithm": algorithm.pk,
        },
    )
    assert response.status_code == 302

    images = AlgorithmImage.objects.all()
    assert len(images) == 1
    assert images[0].algorithm == algorithm
    assert response.url == reverse(
        "algorithms:image-detail",
        kwargs={"slug": algorithm.slug, "pk": images[0].pk},
    )


@pytest.mark.django_db
def test_algorithm_permission_request_list(client):
    user = UserFactory()
    editor = UserFactory()

    alg = AlgorithmFactory(public=True)
    alg.add_editor(editor)

    pr = AlgorithmPermissionRequestFactory(algorithm=alg, user=user)

    response = get_view_for_user(
        viewname="algorithms:permission-request-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
    )

    assert response.status_code == 200
    assert pr.user.username in response.rendered_content

    response = get_view_for_user(
        viewname="algorithms:permission-request-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=user,
        method=client.get,
        follow=True,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_algorithm_jobs_list_view(client):
    editor = UserFactory()

    alg = AlgorithmFactory(public=True)
    alg.add_editor(editor)
    im = AlgorithmImageFactory(algorithm=alg)
    for x in range(50):
        created = timezone.now() - datetime.timedelta(days=x + 365)
        job = AlgorithmJobFactory(algorithm_image=im, status=Job.SUCCESS)
        job.created = created
        job.save()
        job.viewer_groups.add(alg.editors_group)

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
    )

    assert response.status_code == 200

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        data={
            "length": 10,
            "draw": 1,
            "order[0][dir]": "desc",
            "order[0][column]": 0,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp = response.json()
    assert resp["recordsTotal"] == 50
    assert len(resp["data"]) == 10

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        data={
            "length": 50,
            "draw": 1,
            "order[0][dir]": "desc",
            "order[0][column]": 0,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp = response.json()
    assert resp["recordsTotal"] == 50
    assert len(resp["data"]) == 50

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        data={
            "length": 50,
            "draw": 1,
            "order[0][dir]": "asc",
            "order[0][column]": 0,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp_new = response.json()
    assert resp_new["recordsTotal"] == 50
    assert resp_new["data"] == resp["data"][::-1]

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        data={
            "length": 50,
            "draw": 1,
            "search[value]": job.creator.username,
            "order[0][column]": 0,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp = response.json()
    assert resp["recordsTotal"] == 50
    assert resp["recordsFiltered"] == 1
    assert len(resp["data"]) == 1


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        ai = AlgorithmImageFactory(is_manifest_valid=True, is_in_registry=True)
        u = UserFactory()
        j = AlgorithmJobFactory(algorithm_image=ai, status=Job.SUCCESS)
        p = AlgorithmPermissionRequestFactory(algorithm=ai.algorithm)

        VerificationFactory(user=u, is_verified=True)

        for view_name, kwargs, permission, obj, redirect in [
            ("create", {}, "algorithms.add_algorithm", None, None),
            (
                "detail",
                {"slug": ai.algorithm.slug},
                "view_algorithm",
                ai.algorithm,
                reverse(
                    "algorithms:permission-request-create",
                    kwargs={"slug": ai.algorithm.slug},
                ),
            ),
            (
                "update",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "image-create",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "image-detail",
                {"slug": ai.algorithm.slug, "pk": ai.pk},
                "view_algorithmimage",
                ai,
                None,
            ),
            (
                "image-update",
                {"slug": ai.algorithm.slug, "pk": ai.pk},
                "change_algorithmimage",
                ai,
                None,
            ),
            (
                "job-create",
                {"slug": ai.algorithm.slug},
                "execute_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "job-progress-detail",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "view_job",
                j,
                None,
            ),
            (
                "job-detail",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "view_job",
                j,
                None,
            ),
            (
                "job-update",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "change_job",
                j,
                None,
            ),
            (
                "display-set-from-job-create",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "view_job",
                j,
                None,
            ),
            (
                "job-viewers-update",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "change_job",
                j,
                None,
            ),
            (
                "editors-update",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "users-update",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "permission-request-update",
                {"slug": ai.algorithm.slug, "pk": p.pk},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "publish",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"algorithms:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            if redirect is not None:
                assert response.status_code == 302
                assert response.url == redirect
            else:
                assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = _get_view()
            assert response.status_code == 200

            remove_perm(permission, u, obj)

    def test_permission_required_list_views(self, client):
        ai = AlgorithmImageFactory()
        u = UserFactory()
        j = AlgorithmJobFactory(algorithm_image=ai)

        for view_name, kwargs, permission, objs in [
            ("list", {}, "view_algorithm", {ai.algorithm}),
            (
                "job-list",
                {"slug": j.algorithm_image.algorithm.slug},
                "view_job",
                {j},
            ),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"algorithms:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            assert response.status_code == 200
            assert set() == {*response.context[-1]["object_list"]}

            assign_perm(permission, u, list(objs))

            response = _get_view()
            assert response.status_code == 200
            assert objs == {*response.context[-1]["object_list"]}

            for obj in objs:
                remove_perm(permission, u, obj)


@pytest.mark.django_db
class TestJobDetailView:
    def test_guarded_content_visibility(self, client):
        j = AlgorithmJobFactory()
        u = UserFactory()
        assign_perm("view_job", u, j)

        for content, permission, permission_object in [
            ("<h2>Viewers</h2>", "change_job", j),
            ("<h2>Logs</h2>", "view_logs", j),
        ]:
            view_kwargs = {
                "client": client,
                "viewname": "algorithms:job-detail",
                "reverse_kwargs": {
                    "slug": j.algorithm_image.algorithm.slug,
                    "pk": j.pk,
                },
                "user": u,
            }
            response = get_view_for_user(**view_kwargs)
            assert response.status_code == 200
            assert content not in response.rendered_content

            assign_perm(permission, u, permission_object)

            response = get_view_for_user(**view_kwargs)
            assert response.status_code == 200
            assert content in response.rendered_content

            remove_perm(permission, u, permission_object)


@pytest.mark.django_db
def test_display_set_from_job(client):
    u = UserFactory()
    rs = ReaderStudyFactory()
    j = AlgorithmJobFactory(status=Job.SUCCESS)
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2)
    j.inputs.set([civ1])
    j.outputs.set([civ2])

    j.add_viewer(user=u)

    def create_display_set_from_job():
        return get_view_for_user(
            client=client,
            viewname="algorithms:display-set-from-job-create",
            reverse_kwargs={
                "slug": j.algorithm_image.algorithm.slug,
                "pk": j.pk,
            },
            user=u,
            method=client.post,
            data={"reader_study": rs.pk},
        )

    # User must have reader study edit permissions
    rs.add_reader(user=u)
    response = create_display_set_from_job()
    assert response.status_code == 200
    assert response.context_data["form"].errors == {
        "reader_study": [
            "Select a valid choice. That choice is not one of the available choices."
        ]
    }

    rs.add_editor(user=u)
    response = create_display_set_from_job()
    assert response.status_code == 302
    created_display_set = rs.display_sets.get()
    assert response.url == created_display_set.workstation_url

    # Check idempotency
    response = create_display_set_from_job()
    assert response.url == created_display_set.workstation_url


@pytest.mark.django_db
def test_import_is_staff_only(client, authenticated_staff_user):
    response = get_view_for_user(
        viewname="algorithms:import",
        user=authenticated_staff_user,
        client=client,
    )

    assert response.status_code == 200

    authenticated_staff_user.is_staff = False
    authenticated_staff_user.save()

    response = get_view_for_user(
        viewname="algorithms:import",
        user=authenticated_staff_user,
        client=client,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_import_view(client, authenticated_staff_user, mocker):
    class RemoteTestClient:
        def list_algorithms(self, **__):
            return {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "api_url": "https://grand-challenge.org/api/v1/algorithms/0d11fc7b-c63f-4fd7-b80b-51d2e21492c0/",
                        "url": "https://grand-challenge.org/algorithms/the-pi-cai-challenge-baseline-nndetection/",
                        "description": "Baseline algorithm submission for PI-CAI based on the nnDetection framework",
                        "pk": "0d11fc7b-c63f-4fd7-b80b-51d2e21492c0",
                        "title": "PI-CAI: Baseline nnDetection (supervised)",
                        "logo": "https://rumc-gcorg-p-public.s3.amazonaws.com/logos/algorithm/0d11fc7b-c63f-4fd7-b80b-51d2e21492c0/square_logo.x20.jpeg",
                        "slug": "the-pi-cai-challenge-baseline-nndetection",
                        "average_duration": 363.50596,
                        "inputs": [
                            {
                                "title": "Coronal T2 Prostate MRI",
                                "description": "Coronal T2 MRI of the Prostate",
                                "slug": "coronal-t2-prostate-mri",
                                "kind": "Image",
                                "pk": 31,
                                "default_value": None,
                                "super_kind": "Image",
                                "relative_path": "images/coronal-t2-prostate-mri",
                                "overlay_segments": [],
                                "look_up_table": None,
                            },
                            {
                                "title": "Transverse T2 Prostate MRI",
                                "description": "Transverse T2 MRI of the Prostate",
                                "slug": "transverse-t2-prostate-mri",
                                "kind": "Image",
                                "pk": 32,
                                "default_value": None,
                                "super_kind": "Image",
                                "relative_path": "images/transverse-t2-prostate-mri",
                                "overlay_segments": [],
                                "look_up_table": None,
                            },
                            {
                                "title": "Sagittal T2 Prostate MRI",
                                "description": "Sagittal T2 MRI of the Prostate",
                                "slug": "sagittal-t2-prostate-mri",
                                "kind": "Image",
                                "pk": 33,
                                "default_value": None,
                                "super_kind": "Image",
                                "relative_path": "images/sagittal-t2-prostate-mri",
                                "overlay_segments": [],
                                "look_up_table": None,
                            },
                            {
                                "title": "Transverse HBV Prostate MRI",
                                "description": "Transverse High B-Value Prostate MRI",
                                "slug": "transverse-hbv-prostate-mri",
                                "kind": "Image",
                                "pk": 47,
                                "default_value": None,
                                "super_kind": "Image",
                                "relative_path": "images/transverse-hbv-prostate-mri",
                                "overlay_segments": [],
                                "look_up_table": None,
                            },
                            {
                                "title": "Transverse ADC Prostate MRI",
                                "description": "Transverse Apparent Diffusion Coefficient Prostate MRI",
                                "slug": "transverse-adc-prostate-mri",
                                "kind": "Image",
                                "pk": 48,
                                "default_value": None,
                                "super_kind": "Image",
                                "relative_path": "images/transverse-adc-prostate-mri",
                                "overlay_segments": [],
                                "look_up_table": None,
                            },
                            {
                                "title": "Clinical Information Prostate MRI",
                                "description": "Clinical information to support clinically significant prostate cancer detection in prostate MRI. Provided information: patient age at time of examination (patient_age), PSA level in ng/mL as reported (PSA_report), PSA density in ng/mL^2 as reported (PSAD_report), prostate volume as reported (prostate_volume_report), prostate volume derived from automatic whole-gland segmentation (prostate_volume_automatic), scanner manufacturer (scanner_manufacturer), scanner model name (scanner_model_name), diffusion b-value of (calculated) high b-value diffusion map (diffusion_high_bvalue). Values acquired from radiology reports will be missing, if not reported.",
                                "slug": "clinical-information-prostate-mri",
                                "kind": "Anything",
                                "pk": 156,
                                "default_value": None,
                                "super_kind": "Value",
                                "relative_path": "clinical-information-prostate-mri.json",
                                "overlay_segments": [],
                                "look_up_table": None,
                            },
                        ],
                        "outputs": [
                            {
                                "title": "Case-level Cancer Likelihood Prostate MRI",
                                "description": "Case-level likelihood of harboring clinically significant prostate cancer, in range [0,1].",
                                "slug": "prostate-cancer-likelihood",
                                "kind": "Float",
                                "pk": 144,
                                "default_value": None,
                                "super_kind": "Value",
                                "relative_path": "cspca-case-level-likelihood.json",
                                "overlay_segments": [],
                                "look_up_table": None,
                            },
                            {
                                "title": "Transverse Cancer Detection Map Prostate MRI",
                                "description": "Single-class, detection map of clinically significant prostate cancer lesions in 3D, where each voxel represents a floating point in range [0,1].",
                                "slug": "cspca-detection-map",
                                "kind": "Heat Map",
                                "pk": 151,
                                "default_value": None,
                                "super_kind": "Image",
                                "relative_path": "images/cspca-detection-map",
                                "overlay_segments": [],
                                "look_up_table": None,
                            },
                        ],
                    }
                ],
            }

        def list_algorithm_images(self, **__):
            return {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "pk": "11ed712b-41ae-44fd-8a89-40ab09a27e07",
                        "url": "https://grand-challenge.org/algorithms/the-pi-cai-challenge-baseline-nndetection/images/11ed712b-41ae-44fd-8a89-40ab09a27e07/",
                        "api_url": "https://grand-challenge.org/api/v1/algorithms/images/11ed712b-41ae-44fd-8a89-40ab09a27e07/",
                        "algorithm": "https://grand-challenge.org/api/v1/algorithms/0d11fc7b-c63f-4fd7-b80b-51d2e21492c0/",
                        "created": "2022-06-17T16:46:44.853654+02:00",
                        "requires_gpu": True,
                        "requires_memory_gb": 15,
                        "import_status": "Completed",
                    },
                    {
                        "pk": "cad9106c-e3cb-45fa-bda0-068ddacafb59",
                        "url": "https://grand-challenge.org/algorithms/the-pi-cai-challenge-baseline-nndetection/images/cad9106c-e3cb-45fa-bda0-068ddacafb59/",
                        "api_url": "https://grand-challenge.org/api/v1/algorithms/images/cad9106c-e3cb-45fa-bda0-068ddacafb59/",
                        "algorithm": "https://grand-challenge.org/api/v1/algorithms/0d11fc7b-c63f-4fd7-b80b-51d2e21492c0/",
                        "created": "2022-06-17T18:36:30.875295+02:00",
                        "requires_gpu": True,
                        "requires_memory_gb": 15,
                        "import_status": "Completed",
                    },
                ],
            }

    mocker.patch(
        "grandchallenge.algorithms.forms.AlgorithmImportForm.remote_instance_client",
        new_callable=mocker.PropertyMock,
        return_value=RemoteTestClient(),
    )

    with capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            viewname="algorithms:import",
            user=authenticated_staff_user,
            client=client,
            method=client.post,
            data={
                "api_token": "testtoken",
                "algorithm_url": "https://grand-challenge.org/algorithms/the-pi-cai-challenge-baseline-nndetection/",
                "remote_bucket_name": "testbucketname",
            },
        )

    assert response.status_code == 302
    assert (
        response.url
        == "https://testserver/algorithms/the-pi-cai-challenge-baseline-nndetection/"
    )

    assert len(callbacks) == 1
    assert (
        str(callbacks[0])
        == "<bound method Signature.apply_async of grandchallenge.algorithms.tasks.import_remote_algorithm_image(algorithm_image_pk='cad9106c-e3cb-45fa-bda0-068ddacafb59', remote_bucket_name='testbucketname')>"
    )

    algorithm = Algorithm.objects.get(
        slug="the-pi-cai-challenge-baseline-nndetection"
    )
    assert algorithm.is_editor(user=authenticated_staff_user)
    assert str(algorithm.pk) == "0d11fc7b-c63f-4fd7-b80b-51d2e21492c0"
    assert algorithm.logo.name.startswith(
        "logos/algorithm/0d11fc7b-c63f-4fd7-b80b-51d2e21492c0/square_logo"
    )
    assert "Imported from [grand-challenge.org]" in algorithm.summary
    assert {i.slug for i in algorithm.inputs.all()} == {
        "clinical-information-prostate-mri",
        "coronal-t2-prostate-mri",
        "sagittal-t2-prostate-mri",
        "transverse-adc-prostate-mri",
        "transverse-hbv-prostate-mri",
        "transverse-t2-prostate-mri",
    }
    assert {i.slug for i in algorithm.outputs.all()} == {
        "cspca-detection-map",
        "prostate-cancer-likelihood",
    }

    algorithm_image = algorithm.algorithm_container_images.get()
    assert str(algorithm_image.pk) == "cad9106c-e3cb-45fa-bda0-068ddacafb59"
    assert algorithm_image.requires_gpu is True
    assert algorithm_image.requires_memory_gb == 15
    assert (
        algorithm_image.import_status
        == algorithm_image.ImportStatusChoices.INITIALIZED
    )
    assert algorithm_image.creator == authenticated_staff_user

    interface = ComponentInterface.objects.get(
        slug="prostate-cancer-likelihood"
    )
    assert interface.slug == "prostate-cancer-likelihood"
    assert interface.title == "Case-level Cancer Likelihood Prostate MRI"
    assert (
        interface.description
        == "Case-level likelihood of harboring clinically significant prostate cancer, in range [0,1]."
    )
    assert interface.store_in_database is True
    assert interface.kind == ComponentInterface.Kind.FLOAT

    image_interface = ComponentInterface.objects.get(
        slug="transverse-adc-prostate-mri"
    )
    assert image_interface.store_in_database is False
    assert image_interface.kind == ComponentInterface.Kind.IMAGE


@pytest.mark.django_db
def test_create_job_with_json_file(client, settings, algorithm_io_image):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)
    recurse_callbacks(callbacks=callbacks)

    editor = UserFactory()
    ai.algorithm.add_editor(editor)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=False
    )
    ai.algorithm.inputs.set([ci])

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as file:
        json.dump('{"Foo": "bar"}', file)
        file.seek(0)
        upload = create_upload_from_file(
            creator=editor, file_path=Path(file.name)
        )
        with capture_on_commit_callbacks(execute=True):
            with capture_on_commit_callbacks(execute=True):
                response = get_view_for_user(
                    viewname="algorithms:job-create",
                    client=client,
                    method=client.post,
                    reverse_kwargs={
                        "slug": ai.algorithm.slug,
                    },
                    user=editor,
                    follow=True,
                    data={ci.slug: upload.pk},
                )
        assert response.status_code == 200
        assert (
            file.name.split("/")[-1]
            in Job.objects.get().inputs.first().file.name
        )


@pytest.mark.django_db
def test_algorithm_job_create_with_image_input(
    settings, client, algorithm_io_image
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)
    recurse_callbacks(callbacks=callbacks)

    editor = UserFactory()
    ai.algorithm.add_editor(editor)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.IMAGE, store_in_database=False
    )
    ai.algorithm.inputs.set([ci])

    image1, image2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", editor, image1)
    assign_perm("cases.view_image", editor, image2)

    civ = ComponentInterfaceValueFactory(interface=ci, image=image1)
    with capture_on_commit_callbacks(execute=True):
        with capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="algorithms:job-create",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "slug": ai.algorithm.slug,
                },
                user=editor,
                follow=True,
                data={
                    ci.slug: image1.pk,
                    f"WidgetChoice-{ci.slug}": WidgetChoices.IMAGE_SEARCH.name,
                },
            )
    assert response.status_code == 200
    assert Job.objects.get().inputs.first().image.pk == image1.pk
    # same civ reused
    assert Job.objects.get().inputs.first() == civ

    with capture_on_commit_callbacks(execute=True):
        with capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="algorithms:job-create",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "slug": ai.algorithm.slug,
                },
                user=editor,
                follow=True,
                data={
                    ci.slug: image2.pk,
                    f"WidgetChoice-{ci.slug}": WidgetChoices.IMAGE_SEARCH.name,
                },
            )
    assert response.status_code == 200
    assert Job.objects.last().inputs.first().image.pk == image2.pk
    assert Job.objects.last().inputs.first() != civ

    upload = create_upload_from_file(
        file_path=RESOURCE_PATH / "image10x10x10.mha",
        creator=editor,
    )
    with capture_on_commit_callbacks(execute=True):
        with capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="algorithms:job-create",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "slug": ai.algorithm.slug,
                },
                user=editor,
                follow=True,
                data={
                    ci.slug: upload.pk,
                    f"WidgetChoice-{ci.slug}": WidgetChoices.IMAGE_UPLOAD.name,
                },
            )
    assert response.status_code == 200
    assert Job.objects.last().inputs.first().image.name == "image10x10x10.mha"
    assert Job.objects.last().inputs.first() != civ
