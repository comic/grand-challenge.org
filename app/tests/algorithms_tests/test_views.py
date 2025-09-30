import datetime
import io
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.test import override_settings
from django.utils import timezone
from django.utils.text import slugify
from guardian.shortcuts import assign_perm, remove_perm
from requests import put

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmAlgorithmInterface,
    AlgorithmImage,
    AlgorithmInterface,
    Job,
)
from grandchallenge.algorithms.views import JobsList
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    ImportStatusChoices,
    InterfaceKind,
    InterfaceKindChoices,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import PaymentStatusChoices
from grandchallenge.profiles.templatetags.profiles import user_profile_link
from grandchallenge.subdomains.utils import reverse
from grandchallenge.uploads.models import UserUpload
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.cases_tests import RESOURCE_PATH
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
from tests.factories import GroupFactory, ImageFactory, UserFactory
from tests.invoices_tests.factories import InvoiceFactory
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

    VerificationFactory(user=user, is_verified=True)

    response = get_view_for_user(
        viewname="algorithms:create-redirect", client=client, user=user
    )
    assert reverse("algorithms:custom-create") not in response.rendered_content

    g = Group.objects.get(name=settings.ALGORITHMS_CREATORS_GROUP_NAME)
    g.user_set.add(user)

    response = get_view_for_user(
        viewname="algorithms:create-redirect", client=client, user=user
    )
    assert reverse("algorithms:custom-create") in response.rendered_content


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
        job = AlgorithmJobFactory(
            algorithm_image=im,
            status=Job.SUCCESS,
            time_limit=im.algorithm.time_limit,
        )
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
            "order[0][dir]": JobsList.default_sort_order,
            "order[0][column]": JobsList.default_sort_column,
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
            "order[0][column]": 1,
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
            "order[0][column]": 1,
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
            "order[0][column]": JobsList.default_sort_column,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp = response.json()
    assert resp["recordsTotal"] == 50
    assert resp["recordsFiltered"] == 1
    assert len(resp["data"]) == 1


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_group_permission_required_views(self, client):
        ai = AlgorithmImageFactory(is_manifest_valid=True, is_in_registry=True)
        am = AlgorithmModelFactory()
        interface = AlgorithmInterfaceFactory(
            inputs=[ComponentInterfaceFactory()],
            outputs=[ComponentInterfaceFactory()],
        )
        ai.algorithm.interfaces.set([interface])
        u = UserFactory()
        group = Group.objects.create(name="test-group")
        group.user_set.add(u)
        j = AlgorithmJobFactory(
            algorithm_image=ai,
            algorithm_interface=interface,
            status=Job.SUCCESS,
            time_limit=ai.algorithm.time_limit,
        )
        p = AlgorithmPermissionRequestFactory(algorithm=ai.algorithm)

        VerificationFactory(user=u, is_verified=True)

        for view_name, kwargs, permission, obj, redirect in [
            ("custom-create", {}, "algorithms.add_algorithm", None, None),
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
                "statistics",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
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
                "image-import-status-detail",
                {"slug": ai.algorithm.slug, "pk": ai.pk},
                "view_algorithmimage",
                ai,
                None,
            ),
            (
                "image-build-status-detail",
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
                "image-template",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "job-create",
                {
                    "slug": ai.algorithm.slug,
                    "interface_pk": ai.algorithm.interfaces.first().pk,
                },
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
                "job-status-detail",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "view_job",
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
            (
                "model-create",
                {"slug": am.algorithm.slug},
                "change_algorithm",
                am.algorithm,
                None,
            ),
            (
                "model-detail",
                {"slug": am.algorithm.slug, "pk": am.pk},
                "view_algorithmmodel",
                am,
                None,
            ),
            (
                "model-import-status-detail",
                {"slug": am.algorithm.slug, "pk": am.pk},
                "view_algorithmmodel",
                am,
                None,
            ),
            (
                "model-update",
                {"slug": am.algorithm.slug, "pk": am.pk},
                "change_algorithmmodel",
                am,
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

            assign_perm(permission, group, obj)

            response = _get_view()
            assert response.status_code == 200

            remove_perm(permission, group, obj)

    def test_user_permission_required_views(self, client):
        ai = AlgorithmImageFactory(is_manifest_valid=True, is_in_registry=True)
        u = UserFactory()
        j = AlgorithmJobFactory(
            status=Job.SUCCESS,
            time_limit=ai.algorithm.time_limit,
        )

        VerificationFactory(user=u, is_verified=True)

        for view_name, kwargs, permission, obj, redirect in [
            (
                "job-update",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "change_job",
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
        group = GroupFactory()
        group.user_set.add(u)
        j = AlgorithmJobFactory(
            algorithm_image=ai, time_limit=ai.algorithm.time_limit
        )

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

            assign_perm(permission, group, list(objs))

            response = _get_view()
            assert response.status_code == 200
            assert objs == {*response.context[-1]["object_list"]}

            for obj in objs:
                remove_perm(permission, group, obj)


@pytest.mark.django_db
class TestJobDetailView:
    def test_guarded_group_content_visibility(self, client):
        j = AlgorithmJobFactory(time_limit=60)
        u = UserFactory()
        group = GroupFactory()
        group.user_set.add(u)
        assign_perm("view_job", group, j)

        for content, permission, permission_object in [
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

            assign_perm(permission, group, permission_object)

            response = get_view_for_user(**view_kwargs)
            assert response.status_code == 200
            assert content in response.rendered_content

            remove_perm(permission, group, permission_object)

    def test_guarded_user_content_visibility(self, client):
        j = AlgorithmJobFactory(time_limit=60)
        u = UserFactory()
        group = GroupFactory()
        group.user_set.add(u)
        assign_perm("view_job", group, j)

        for content, permission, permission_object in [
            ("<h2>Viewers</h2>", "change_job", j),
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
    j = AlgorithmJobFactory(status=Job.SUCCESS, time_limit=60)
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
def test_import_is_staff_only(client):
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="algorithms:import",
        user=user,
        client=client,
    )

    assert response.status_code == 200

    user.is_staff = False
    user.save()

    response = get_view_for_user(
        viewname="algorithms:import",
        user=user,
        client=client,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_import_view(
    client,
    mocker,
    django_capture_on_commit_callbacks,
):
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
                        "logo": "https://public.grand-challenge-user-content.org/logos/algorithm/0d11fc7b-c63f-4fd7-b80b-51d2e21492c0/square_logo.x20.jpeg",
                        "slug": "the-pi-cai-challenge-baseline-nndetection",
                        "average_duration": 363.50596,
                        "interfaces": [
                            {
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

    staff_user = UserFactory(is_staff=True)

    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            viewname="algorithms:import",
            user=staff_user,
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
    assert algorithm.is_editor(user=staff_user)
    assert str(algorithm.pk) == "0d11fc7b-c63f-4fd7-b80b-51d2e21492c0"
    assert algorithm.logo.name.startswith(
        "logos/algorithm/0d11fc7b-c63f-4fd7-b80b-51d2e21492c0/square_logo"
    )
    assert "Imported from [grand-challenge.org]" in algorithm.summary

    assert algorithm.interfaces.count() == 1
    interface = algorithm.interfaces.get()
    assert {i.slug for i in interface.inputs.all()} == {
        "clinical-information-prostate-mri",
        "coronal-t2-prostate-mri",
        "sagittal-t2-prostate-mri",
        "transverse-adc-prostate-mri",
        "transverse-hbv-prostate-mri",
        "transverse-t2-prostate-mri",
    }
    assert {i.slug for i in interface.outputs.all()} == {
        "cspca-detection-map",
        "prostate-cancer-likelihood",
    }

    algorithm_image = algorithm.algorithm_container_images.get()
    assert str(algorithm_image.pk) == "cad9106c-e3cb-45fa-bda0-068ddacafb59"
    assert (
        algorithm_image.import_status
        == algorithm_image.ImportStatusChoices.INITIALIZED
    )
    assert algorithm_image.creator == staff_user

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
    assert image_interface.kind == ComponentInterface.Kind.MHA_OR_TIFF_IMAGE


@pytest.mark.django_db
def test_create_job_with_json_file(
    client, settings, algorithm_io_image, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with django_capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    editor = UserFactory()
    VerificationFactory(user=editor, is_verified=True)
    ai.algorithm.add_editor(editor)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=False
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[ci],
    )
    ai.algorithm.interfaces.add(interface)

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json") as file:
        json.dump('{"Foo": "bar"}', file)
        file.seek(0)
        upload = create_upload_from_file(
            creator=editor, file_path=Path(file.name)
        )
        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="algorithms:job-create",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "slug": ai.algorithm.slug,
                    "interface_pk": interface.pk,
                },
                user=editor,
                follow=True,
                data={
                    **get_interface_form_data(
                        interface_slug=ci.slug, data=upload.pk
                    )
                },
            )
        assert response.status_code == 200
        assert (
            file.name.split("/")[-1]
            in Job.objects.get().inputs.first().file.name
        )
        assert not UserUpload.objects.filter(pk=upload.pk).exists()


@pytest.mark.django_db
def test_algorithm_job_create_with_image_input(
    settings, client, algorithm_io_image, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with django_capture_on_commit_callbacks() as callbacks:
        ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)
    recurse_callbacks(
        callbacks=callbacks,
        django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
    )

    editor = UserFactory()
    VerificationFactory(user=editor, is_verified=True)
    ai.algorithm.add_editor(editor)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.MHA_OR_TIFF_IMAGE,
        store_in_database=False,
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[ci],
    )
    ai.algorithm.interfaces.add(interface)

    image1, image2 = ImageFactory.create_batch(2)
    assign_perm("cases.view_image", editor, image1)
    assign_perm("cases.view_image", editor, image2)

    civ = ComponentInterfaceValueFactory(interface=ci, image=image1)
    with django_capture_on_commit_callbacks(execute=True):
        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="algorithms:job-create",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "slug": ai.algorithm.slug,
                    "interface_pk": interface.pk,
                },
                user=editor,
                follow=True,
                data={
                    **get_interface_form_data(
                        interface_slug=ci.slug,
                        data=image1.pk,
                        existing_data=True,
                    )
                },
            )
    assert response.status_code == 200
    assert str(Job.objects.get().inputs.first().image.pk) == str(image1.pk)
    # same civ reused
    assert Job.objects.get().inputs.first() == civ

    with django_capture_on_commit_callbacks(execute=True):
        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="algorithms:job-create",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "slug": ai.algorithm.slug,
                    "interface_pk": interface.pk,
                },
                user=editor,
                follow=True,
                data={
                    **get_interface_form_data(
                        interface_slug=ci.slug,
                        data=image2.pk,
                        existing_data=True,
                    )
                },
            )
    assert response.status_code == 200
    assert str(Job.objects.last().inputs.first().image.pk) == str(image2.pk)
    assert Job.objects.last().inputs.first() != civ

    upload = create_upload_from_file(
        file_path=RESOURCE_PATH / "image10x10x10.mha",
        creator=editor,
    )
    with django_capture_on_commit_callbacks(execute=True):
        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                viewname="algorithms:job-create",
                client=client,
                method=client.post,
                reverse_kwargs={
                    "slug": ai.algorithm.slug,
                    "interface_pk": interface.pk,
                },
                user=editor,
                follow=True,
                data={
                    **get_interface_form_data(
                        interface_slug=ci.slug, data=upload.pk
                    )
                },
            )
    assert response.status_code == 200
    assert Job.objects.last().inputs.first().image.name == "image10x10x10.mha"
    assert Job.objects.last().inputs.first() != civ


@pytest.mark.django_db
class TestJobCreateView:

    def create_job(
        self,
        client,
        django_capture_on_commit_callbacks,
        user,
        inputs,
        algorithm,
    ):
        with patch(
            "grandchallenge.components.tasks.execute_job"
        ) as mocked_execute_job:
            # no need to actually execute the job,
            # all other async tasks should run though
            mocked_execute_job.return_value = None
            with django_capture_on_commit_callbacks(execute=True):
                response = get_view_for_user(
                    viewname="algorithms:job-create",
                    client=client,
                    method=client.post,
                    user=user,
                    reverse_kwargs={
                        "slug": algorithm.slug,
                        "interface_pk": algorithm.interfaces.first().pk,
                    },
                    follow=True,
                    data=inputs,
                )
        return response

    def create_existing_civs(self, interface_data):
        civ1 = ComponentInterfaceValueFactory(
            interface=interface_data.ci_bool, value=True
        )
        civ2 = ComponentInterfaceValueFactory(
            interface=interface_data.ci_str, value="Foo"
        )
        civ3 = ComponentInterfaceValueFactory(
            interface=interface_data.ci_existing_img,
            image=interface_data.image_1,
        )
        civ4 = ComponentInterfaceValueFactory(
            interface=interface_data.ci_json_in_db_with_schema,
            value=["Foo", "bar"],
        )
        civ5 = ComponentInterfaceValueFactory(
            interface=interface_data.ci_json_file,
            file=ContentFile(
                json.dumps(["Foo", "bar"]).encode("utf-8"),
                name=Path(interface_data.ci_json_file.relative_path).name,
            ),
        )
        return [civ1, civ2, civ3, civ4, civ5]

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_multiple_new_inputs(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        # configure multiple inputs
        interface = AlgorithmInterfaceFactory(
            inputs=[
                algorithm_with_multiple_inputs.ci_json_in_db_with_schema,
                algorithm_with_multiple_inputs.ci_existing_img,
                algorithm_with_multiple_inputs.ci_str,
                algorithm_with_multiple_inputs.ci_bool,
                algorithm_with_multiple_inputs.ci_json_file,
                algorithm_with_multiple_inputs.ci_img_upload,
            ],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)

        assert ComponentInterfaceValue.objects.count() == 0

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_str.slug,
                    data="Foo",
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_bool.slug,
                    data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_img_upload.slug,
                    data=algorithm_with_multiple_inputs.im_upload_through_ui.pk,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_existing_img.slug,
                    data=algorithm_with_multiple_inputs.image_1.pk,
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_json_file.slug,
                    data=algorithm_with_multiple_inputs.file_upload.pk,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    data='["Foo", "bar"]',
                ),
            },
        )
        assert response.status_code == 200
        assert Job.objects.count() == 1

        job = Job.objects.get()

        assert (
            job.algorithm_image
            == algorithm_with_multiple_inputs.algorithm.active_image
        )
        assert (
            job.algorithm_model
            == algorithm_with_multiple_inputs.algorithm.active_model
        )
        assert job.time_limit == 600
        assert job.inputs.count() == 6

        assert not UserUpload.objects.filter(
            pk=algorithm_with_multiple_inputs.file_upload.pk
        ).exists()

        assert sorted(
            [
                int.pk
                for int in algorithm_with_multiple_inputs.algorithm.interfaces.first().inputs.all()
            ]
        ) == sorted([civ.interface.pk for civ in job.inputs.all()])

        value_inputs = [civ.value for civ in job.inputs.all() if civ.value]
        assert "Foo" in value_inputs
        assert True in value_inputs
        assert ["Foo", "bar"] in value_inputs

        image_inputs = [
            civ.image.name for civ in job.inputs.all() if civ.image
        ]
        assert algorithm_with_multiple_inputs.image_1.name in image_inputs
        assert "image10x10x10.mha" in image_inputs
        assert (
            algorithm_with_multiple_inputs.file_upload.filename.split(".")[0]
            in [civ.file for civ in job.inputs.all() if civ.file][0].name
        )

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_existing_inputs(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        # configure multiple inputs
        interface = AlgorithmInterfaceFactory(
            inputs=[
                algorithm_with_multiple_inputs.ci_json_in_db_with_schema,
                algorithm_with_multiple_inputs.ci_existing_img,
                algorithm_with_multiple_inputs.ci_str,
                algorithm_with_multiple_inputs.ci_bool,
                algorithm_with_multiple_inputs.ci_json_file,
            ],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)

        civ1, civ2, civ3, civ4, civ5 = self.create_existing_civs(
            interface_data=algorithm_with_multiple_inputs
        )

        old_job_with_only_file_input = AlgorithmJobFactory(
            algorithm_image=algorithm_with_multiple_inputs.algorithm.active_image,
            algorithm_model=algorithm_with_multiple_inputs.algorithm.active_model,
            status=Job.SUCCESS,
            time_limit=10,
            creator=algorithm_with_multiple_inputs.editor,
        )
        old_job_with_only_file_input.inputs.set([civ5])

        old_job_count = 1
        old_civ_count = ComponentInterfaceValue.objects.count()

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_str.slug,
                    data="Foo",
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_bool.slug,
                    data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_existing_img.slug,
                    data=algorithm_with_multiple_inputs.image_1.pk,
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_json_file.slug,
                    data=civ5.pk,
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    data='["Foo", "bar"]',
                ),
            },
        )
        assert response.status_code == 200
        # no new CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == old_civ_count
        # since there is no job with these inputs yet, a job was created:
        assert Job.objects.count() == old_job_count + 1
        job = Job.objects.last()
        assert job.inputs.count() == 5
        for civ in [civ1, civ2, civ3, civ4, civ5]:
            assert civ in job.inputs.all()

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_is_idempotent(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        # configure multiple inputs
        interface = AlgorithmInterfaceFactory(
            inputs=[
                algorithm_with_multiple_inputs.ci_str,
                algorithm_with_multiple_inputs.ci_bool,
                algorithm_with_multiple_inputs.ci_existing_img,
                algorithm_with_multiple_inputs.ci_json_in_db_with_schema,
            ],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)
        civ1, civ2, civ3, civ4, civ5 = self.create_existing_civs(
            interface_data=algorithm_with_multiple_inputs
        )

        job = AlgorithmJobFactory(
            algorithm_image=algorithm_with_multiple_inputs.algorithm.active_image,
            algorithm_model=algorithm_with_multiple_inputs.algorithm.active_model,
            status=Job.SUCCESS,
            time_limit=10,
        )
        job.inputs.set([civ1, civ2, civ3, civ4])
        old_civ_count = ComponentInterfaceValue.objects.count()

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_str.slug,
                    data="Foo",
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_bool.slug,
                    data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_existing_img.slug,
                    data=algorithm_with_multiple_inputs.image_1.pk,
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    data='["Foo", "bar"]',
                ),
            },
        )
        assert response.status_code == 200
        assert (
            "A result for these inputs with the current image and model already exists."
            in str(response.content)
        )
        # no new CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == old_civ_count
        # and no new job because there already is a job with these inputs
        assert Job.objects.count() == 1

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_faulty_file_input(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        # configure file input
        interface = AlgorithmInterfaceFactory(
            inputs=[algorithm_with_multiple_inputs.ci_json_file],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)
        file_upload = UserUploadFactory(
            filename="file.json", creator=algorithm_with_multiple_inputs.editor
        )
        presigned_urls = file_upload.generate_presigned_urls(part_numbers=[1])
        response = put(presigned_urls["1"], data=b'{"Foo": "bar"}')
        file_upload.complete_multipart_upload(
            parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
        )
        file_upload.save()

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_json_file.slug,
                    data=file_upload.pk,
                ),
            },
        )
        assert response.status_code == 200
        # validation of files happens async, so job gets created
        assert Job.objects.count() == 1
        job = Job.objects.get()
        # but in cancelled state and with an error message
        assert job.status == Job.CANCELLED
        assert (
            "One or more of the inputs failed validation." == job.error_message
        )
        assert job.detailed_error_message == {
            algorithm_with_multiple_inputs.ci_json_file.title: "JSON does not fulfill schema: instance is not of type 'array'"
        }
        # and no CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == 0

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_faulty_json_input(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        interface = AlgorithmInterfaceFactory(
            inputs=[algorithm_with_multiple_inputs.ci_json_in_db_with_schema],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)
        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    data='{"foo": "bar"}',
                ),
            },
        )
        # validation of values stored in DB happens synchronously,
        # so no job and no CIVs get created if validation fails
        # error message is reported back to user directly in the form
        assert response.status_code == 200
        assert "JSON does not fulfill schema" in str(response.content)
        assert Job.objects.count() == 0
        assert ComponentInterfaceValue.objects.count() == 0

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_faulty_image_input(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        interface = AlgorithmInterfaceFactory(
            inputs=[algorithm_with_multiple_inputs.ci_img_upload],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)
        user_upload = create_upload_from_file(
            creator=algorithm_with_multiple_inputs.editor,
            file_path=RESOURCE_PATH / "corrupt.png",
        )

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_with_multiple_inputs.ci_img_upload.slug,
                    data=user_upload.pk,
                ),
            },
        )
        assert response.status_code == 200
        # validation of images happens async, so job gets created
        assert Job.objects.count() == 1
        job = Job.objects.get()
        # but in cancelled state and with an error message
        assert job.status == Job.CANCELLED
        assert (
            "One or more of the inputs failed validation." == job.error_message
        )
        assert "1 file could not be imported" in str(
            job.detailed_error_message
        )
        # and no CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == 0

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_multiple_faulty_existing_image_inputs(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        # configure multiple inputs
        ci1, ci2 = ComponentInterfaceFactory.create_batch(
            2, kind=InterfaceKindChoices.MHA_OR_TIFF_SEGMENTATION
        )

        for ci in [ci1, ci2]:
            ci.overlay_segments = [
                {"name": "s1", "visible": True, "voxel_value": 1}
            ]
            ci.save()

        interface = AlgorithmInterfaceFactory(
            inputs=[ci1, ci2], outputs=[ComponentInterfaceFactory()]
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)

        assert ComponentInterfaceValue.objects.count() == 0

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs={
                **get_interface_form_data(
                    interface_slug=ci1.slug,
                    data=algorithm_with_multiple_inputs.image_1.pk,
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=ci2.slug,
                    data=algorithm_with_multiple_inputs.image_2.pk,
                    existing_data=True,
                ),
            },
        )
        assert response.status_code == 200
        assert Job.objects.count() == 1

        job = Job.objects.get()
        assert job.status == job.CANCELLED
        assert job.inputs.count() == 0
        assert (
            "One or more of the inputs failed validation." == job.error_message
        )
        assert (
            "Image segments could not be determined, ensure the voxel values are integers and that it contains no more than 64 segments"
            in str(job.detailed_error_message)
        )
        # and no CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == 0


@pytest.mark.django_db
def test_algorithm_image_activate(
    settings, client, algorithm_io_image, mocker
):
    mocker.patch.object(
        AlgorithmImage, "calculate_size_in_registry", lambda x: 100
    )

    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    alg = AlgorithmFactory()
    i1, i2 = AlgorithmImageFactory.create_batch(
        2,
        algorithm=alg,
        is_manifest_valid=True,
        is_in_registry=True,
        image=None,
    )
    for image in {i1, i2}:
        with open(algorithm_io_image, "rb") as f:
            image.image.save(algorithm_io_image, ContentFile(f.read()))

    i2.is_desired_version = True
    i2.save()

    editor, user = UserFactory.create_batch(2)
    alg.add_editor(editor)

    response = get_view_for_user(
        viewname="algorithms:image-activate",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": alg.slug},
        data={"algorithm_image": i1.pk},
        user=user,
        follow=True,
    )
    assert response.status_code == 403

    response2 = get_view_for_user(
        viewname="algorithms:image-activate",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": alg.slug},
        data={"algorithm_image": i1.pk},
        user=editor,
        follow=True,
    )

    assert response2.status_code == 200
    i1.refresh_from_db()
    i2.refresh_from_db()
    assert i1.is_desired_version
    assert not i2.is_desired_version
    assert alg.active_image == i1

    i2.is_manifest_valid = True
    i2.is_in_registry = False
    i2.save()

    response4 = get_view_for_user(
        viewname="algorithms:image-activate",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": alg.slug},
        data={"algorithm_image": i2.pk},
        user=editor,
        follow=True,
    )
    assert response4.status_code == 200
    assert "Image validation and upload to registry in progress." in str(
        response4.content
    )

    i2.import_status = ImportStatusChoices.INITIALIZED
    i2.is_desired_version = False
    i2.save()
    response6 = get_view_for_user(
        viewname="algorithms:image-activate",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": alg.slug},
        data={"algorithm_image": i2.pk},
        user=editor,
        follow=True,
    )
    assert response6.status_code == 200
    i1.refresh_from_db()
    i2.refresh_from_db()
    del alg.active_image
    assert not i1.is_desired_version
    assert i2.is_desired_version
    assert alg.active_image == i2
    assert i2.is_in_registry


@pytest.mark.django_db
def test_job_time_limit(client):
    algorithm = AlgorithmFactory(time_limit=600)
    algorithm_image = AlgorithmImageFactory(
        algorithm=algorithm,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    user = UserFactory()
    VerificationFactory(user=user, is_verified=True)
    algorithm.add_editor(user=user)

    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=True
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[ci], outputs=[ComponentInterfaceFactory()]
    )
    algorithm.interfaces.add(interface)

    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": algorithm.slug,
            "interface_pk": algorithm.interfaces.first().pk,
        },
        user=user,
        follow=True,
        data={
            **get_interface_form_data(
                interface_slug=ci.slug, data='{"Foo": "bar"}'
            )
        },
    )

    assert response.status_code == 200

    job = Job.objects.get()

    assert job.algorithm_image == algorithm_image
    assert job.time_limit == 600


@pytest.mark.django_db
def test_job_gpu_type_set(client, settings):
    settings.COMPONENTS_DEFAULT_BACKEND = "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor"

    algorithm = AlgorithmFactory(
        job_requires_gpu_type=GPUTypeChoices.T4,
        job_requires_memory_gb=64,
    )
    algorithm_image = AlgorithmImageFactory(
        algorithm=algorithm,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    user = UserFactory()
    VerificationFactory(user=user, is_verified=True)
    algorithm.add_editor(user=user)

    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=True
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[ci], outputs=[ComponentInterfaceFactory()]
    )
    algorithm.interfaces.add(interface)

    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": algorithm.slug,
            "interface_pk": algorithm.interfaces.first().pk,
        },
        user=user,
        follow=True,
        data={
            **get_interface_form_data(
                interface_slug=ci.slug, data='{"Foo": "bar"}'
            )
        },
    )

    assert response.status_code == 200

    job = Job.objects.get()

    assert job.algorithm_image == algorithm_image
    assert job.requires_gpu_type == GPUTypeChoices.T4
    assert job.requires_memory_gb == 64
    assert job.credits_consumed == 190
    assert algorithm.credits_per_job == 190


@pytest.mark.django_db
def test_job_gpu_type_set_with_api(client, settings):
    settings.COMPONENTS_DEFAULT_BACKEND = "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor"

    algorithm = AlgorithmFactory(
        job_requires_gpu_type=GPUTypeChoices.A10G,
        job_requires_memory_gb=64,
    )
    algorithm_image = AlgorithmImageFactory(
        algorithm=algorithm,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    user = UserFactory()
    VerificationFactory(user=user, is_verified=True)
    algorithm.add_editor(user=user)

    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY, store_in_database=True
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[ci],
    )
    algorithm.interfaces.add(interface)

    response = get_view_for_user(
        viewname="api:algorithms-job-list",
        client=client,
        method=client.post,
        user=user,
        follow=True,
        content_type="application/json",
        data={
            "algorithm": algorithm.api_url,
            "inputs": [
                {
                    "interface": ci.slug,
                    "value": '{"Foo": "bar"}',
                },
            ],
        },
    )

    assert response.status_code == 201

    job = Job.objects.get()

    assert job.algorithm_interface == interface
    assert job.algorithm_image == algorithm_image
    assert job.requires_gpu_type == GPUTypeChoices.A10G
    assert job.requires_memory_gb == 64
    assert job.credits_consumed == 250
    assert algorithm.credits_per_job == 250


@pytest.mark.django_db
def test_job_create_view_for_verified_users_only(client):
    user = UserFactory()
    editor = UserFactory()
    VerificationFactory(user=editor, is_verified=True)
    alg = AlgorithmFactory()
    alg.add_user(user)
    alg.add_user(editor)

    interface = AlgorithmInterfaceFactory(
        inputs=[ComponentInterfaceFactory()],
        outputs=[ComponentInterfaceFactory()],
    )
    alg.interfaces.add(interface)

    response = get_view_for_user(
        viewname="algorithms:job-create",
        reverse_kwargs={
            "slug": alg.slug,
            "interface_pk": alg.interfaces.first().pk,
        },
        client=client,
        user=user,
    )
    assert response.status_code == 403

    response2 = get_view_for_user(
        viewname="algorithms:job-create",
        reverse_kwargs={
            "slug": alg.slug,
            "interface_pk": alg.interfaces.first().pk,
        },
        client=client,
        user=editor,
    )
    assert response2.status_code == 200


@pytest.mark.django_db
def test_evaluations_are_filtered(client):
    user = UserFactory()

    algorithm_image = AlgorithmImageFactory()
    algorithm_image.algorithm.add_editor(user=user)

    public_phase_private_challenge = PhaseFactory(
        public=True, challenge__hidden=True
    )
    public_phase_public_challenge = PhaseFactory(
        public=True, challenge__hidden=False
    )
    public_phase_public_challenge_2 = PhaseFactory(
        public=True, challenge__hidden=False
    )
    private_phase_private_challenge = PhaseFactory(
        public=False, challenge__hidden=True
    )
    private_phase_public_challenge = PhaseFactory(
        public=False, challenge__hidden=False
    )

    # 2nd Ignored as there is an older evaluation
    e, _ = EvaluationFactory.create_batch(
        2,
        submission__phase=public_phase_public_challenge,
        submission__algorithm_image=algorithm_image,
        rank=2,
        time_limit=algorithm_image.algorithm.time_limit,
    )
    # Ignored as there is a better submission
    EvaluationFactory(
        submission__phase=public_phase_public_challenge,
        submission__algorithm_image=algorithm_image,
        rank=3,
        time_limit=algorithm_image.algorithm.time_limit,
    )
    # Ignored as challenge is private
    EvaluationFactory.create_batch(
        2,
        submission__phase=public_phase_private_challenge,
        submission__algorithm_image=algorithm_image,
        rank=1,
        time_limit=algorithm_image.algorithm.time_limit,
    )
    # Ignored as phase is private
    EvaluationFactory.create_batch(
        2,
        submission__phase=private_phase_private_challenge,
        submission__algorithm_image=algorithm_image,
        rank=1,
        time_limit=algorithm_image.algorithm.time_limit,
    )
    # Ignored as phase is private
    EvaluationFactory.create_batch(
        2,
        submission__phase=private_phase_public_challenge,
        submission__algorithm_image=algorithm_image,
        rank=1,
        time_limit=algorithm_image.algorithm.time_limit,
    )
    e2, _ = EvaluationFactory.create_batch(
        2,
        submission__phase=public_phase_public_challenge_2,
        submission__algorithm_image=algorithm_image,
        rank=5,
        time_limit=algorithm_image.algorithm.time_limit,
    )

    response = get_view_for_user(
        viewname="algorithms:detail",
        client=client,
        reverse_kwargs={
            "slug": algorithm_image.algorithm.slug,
        },
        user=user,
    )

    assert [*response.context["best_evaluation_per_phase"]] == [e, e2]


@pytest.mark.django_db
def test_job_create_denied_for_same_input_model_and_image(client):
    creator = UserFactory()
    VerificationFactory(user=creator, is_verified=True)
    alg = AlgorithmFactory()
    alg.add_editor(user=creator)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.MHA_OR_TIFF_IMAGE
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[ci], outputs=[ComponentInterfaceFactory()]
    )
    alg.interfaces.add(interface)
    ai = AlgorithmImageFactory(
        algorithm=alg,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    am = AlgorithmModelFactory(algorithm=alg, is_desired_version=True)
    im = ImageFactory()
    assign_perm("view_image", creator, im)
    civ = ComponentInterfaceValueFactory(interface=ci, image=im)
    j = AlgorithmJobFactory(
        algorithm_image=ai,
        algorithm_model=am,
        time_limit=ai.algorithm.time_limit,
    )
    j.inputs.set([civ])
    response = get_view_for_user(
        viewname="algorithms:job-create",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": alg.slug,
            "interface_pk": alg.interfaces.first().pk,
        },
        user=creator,
        data={
            **get_interface_form_data(
                interface_slug=ci.slug, data=im.pk, existing_data=True
            )
        },
    )
    assert not response.context["form"].is_valid()
    assert (
        "A result for these inputs with the current image and model already exists."
        in str(response.context["form"].errors)
    )


@pytest.mark.django_db
def test_algorithm_model_version_management(settings, client):
    alg = AlgorithmFactory()
    m1, m2 = AlgorithmModelFactory.create_batch(
        2, algorithm=alg, import_status=ImportStatusChoices.COMPLETED
    )
    m2.is_desired_version = True
    m2.save()

    editor, user = UserFactory.create_batch(2)
    alg.add_editor(editor)

    response = get_view_for_user(
        viewname="algorithms:model-activate",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": alg.slug},
        data={"algorithm_model": m1.pk},
        user=user,
        follow=True,
    )
    assert response.status_code == 403

    response2 = get_view_for_user(
        viewname="algorithms:model-activate",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": alg.slug},
        data={"algorithm_model": m1.pk},
        user=editor,
        follow=True,
    )

    assert response2.status_code == 200
    m1.refresh_from_db()
    m2.refresh_from_db()
    assert m1.is_desired_version
    assert not m2.is_desired_version
    assert alg.active_model == m1

    response2 = get_view_for_user(
        viewname="algorithms:model-deactivate",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": alg.slug},
        data={"algorithm_model": m1.pk},
        user=editor,
        follow=True,
    )

    assert response2.status_code == 200
    m1.refresh_from_db()
    m2.refresh_from_db()
    assert not m1.is_desired_version
    assert not m2.is_desired_version
    del alg.active_model
    assert not alg.active_model


@pytest.mark.django_db
def test_job_list_row_template_ajax_renders(client):

    editor = UserFactory()

    algorithm = AlgorithmFactory()
    algorithm.add_editor(editor)

    algorithm_image = AlgorithmImageFactory(algorithm=algorithm)

    job = AlgorithmJobFactory(
        creator=editor,
        algorithm_image=algorithm_image,
        status=Job.SUCCESS,
        time_limit=algorithm.time_limit,
    )

    headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    response = get_view_for_user(
        viewname="algorithms:job-list",
        client=client,
        method=client.get,
        reverse_kwargs={
            "slug": algorithm.slug,
        },
        user=editor,
        data={
            "draw": "1",
            "order[0][column]": "1",
            "order[0][dir]": "desc",
            "start": "0",
            "length": "25",
        },
        **headers,
    )

    job_details_url = reverse(
        "algorithms:job-detail",
        kwargs={"slug": job.algorithm_image.algorithm.slug, "pk": job.pk},
    )

    response_content = json.loads(response.content.decode("utf-8"))

    assert response.status_code == 200
    assert response_content["recordsTotal"] == 1
    assert len(response_content["data"]) == 1
    assert job_details_url in response_content["data"][0][0]


@pytest.mark.django_db
def test_update_view_limits_gpu_choice(client):
    algorithm = AlgorithmFactory(title="test-algorithm")

    editor = UserFactory()
    VerificationFactory(user=editor, is_verified=True)
    algorithm.add_editor(user=editor)

    response = get_view_for_user(
        client=client,
        viewname="algorithms:update",
        reverse_kwargs={"slug": algorithm.slug},
        method=client.post,
        user=editor,
        data={
            "title": algorithm.title,
            "contact_email": "foo@bar.com",
            "access_request_handling": algorithm.access_request_handling,
            "minimum_credits_per_job": algorithm.minimum_credits_per_job,
            "workstation": algorithm.workstation.pk,
            "job_requires_gpu_type": GPUTypeChoices.V100,
            "job_requires_memory_gb": 64,
        },
    )

    assert response.status_code == 200
    assert "job_requires_gpu_type" in response.context["form"].errors
    assert response.context["form"].errors["job_requires_gpu_type"] == [
        "Select a valid choice. V100 is not one of the available choices."
    ]
    assert "job_requires_memory_gb" in response.context["form"].errors
    assert response.context["form"].errors["job_requires_memory_gb"] == [
        "Ensure this value is less than or equal to 32."
    ]

    response = get_view_for_user(
        client=client,
        viewname="algorithms:update",
        reverse_kwargs={"slug": algorithm.slug},
        method=client.post,
        user=editor,
        data={
            "title": algorithm.title,
            "contact_email": "foo@bar.com",
            "access_request_handling": algorithm.access_request_handling,
            "minimum_credits_per_job": algorithm.minimum_credits_per_job,
            "workstation": algorithm.workstation.pk,
            "job_requires_gpu_type": GPUTypeChoices.NO_GPU,
            "job_requires_memory_gb": 16,
        },
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_algorithm_template_download(client):
    alg = AlgorithmFactory()
    editor = UserFactory()
    alg.add_editor(editor)

    response = get_view_for_user(
        viewname="algorithms:image-template",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=editor,
    )

    assert (
        response.status_code == 200
    ), "Editor can download template"  # Sanity

    assert (
        response["Content-Type"] == "application/zip"
    ), "Response is a ZIP file"

    assert (
        "attachment" in response["Content-Disposition"]
    ), "Response is a downloadable attachment"
    assert response["Content-Disposition"].endswith(
        '.zip"'
    ), "Filename ends with .zip"

    # Load the response content into a BytesIO object to read as a zip
    buffer = io.BytesIO(
        b"".join(chunk for chunk in response.streaming_content)
    )
    zip_file = zipfile.ZipFile(buffer)

    # Spot check for expected files in the zip
    expected_files = [
        "README.md",
        "Dockerfile",
        "inference.py",
    ]
    for file_name in expected_files:
        assert (
            str(file_name) in zip_file.namelist()
        ), f"{file_name} is in the ZIP file"


@pytest.mark.parametrize(
    "viewname", ["algorithms:interface-list", "algorithms:interface-create"]
)
@pytest.mark.django_db
def test_algorithm_interface_view_permission(client, viewname):
    (
        user_with_alg_add_perm,
        user_without_alg_add_perm,
        algorithm_editor_with_alg_add,
        algorithm_editor_without_alg_add,
    ) = UserFactory.create_batch(4)
    assign_perm("algorithms.add_algorithm", user_with_alg_add_perm)
    assign_perm("algorithms.add_algorithm", algorithm_editor_with_alg_add)

    alg = AlgorithmFactory()
    alg.add_editor(algorithm_editor_with_alg_add)
    alg.add_editor(algorithm_editor_without_alg_add)

    for user, status in [
        [user_with_alg_add_perm, 403],
        [user_without_alg_add_perm, 403],
        [algorithm_editor_with_alg_add, 200],
        [algorithm_editor_without_alg_add, 403],
    ]:
        response = get_view_for_user(
            viewname=viewname,
            client=client,
            reverse_kwargs={"slug": alg.slug},
            user=user,
        )
        assert response.status_code == status


@pytest.mark.django_db
def test_algorithm_interface_delete_permission(client):
    (
        user_with_alg_add_perm,
        user_without_alg_add_perm,
        algorithm_editor_with_alg_add,
        algorithm_editor_without_alg_add,
    ) = UserFactory.create_batch(4)
    assign_perm("algorithms.add_algorithm", user_with_alg_add_perm)
    assign_perm("algorithms.add_algorithm", algorithm_editor_with_alg_add)

    alg = AlgorithmFactory()
    alg.add_editor(algorithm_editor_with_alg_add)
    alg.add_editor(algorithm_editor_without_alg_add)

    int1, int2 = AlgorithmInterfaceFactory.create_batch(2)
    alg.interfaces.add(int1)
    alg.interfaces.add(int2)

    for user, status in [
        [user_with_alg_add_perm, 403],
        [user_without_alg_add_perm, 403],
        [algorithm_editor_with_alg_add, 200],
        [algorithm_editor_without_alg_add, 403],
    ]:
        response = get_view_for_user(
            viewname="algorithms:interface-delete",
            client=client,
            reverse_kwargs={
                "slug": alg.slug,
                "interface_pk": int2.pk,
            },
            user=user,
        )
        assert response.status_code == status


@pytest.mark.django_db
def test_algorithm_interface_create(client):
    user = UserFactory()
    assign_perm("algorithms.add_algorithm", user)
    alg = AlgorithmFactory()
    alg.add_editor(user)

    ci_1 = ComponentInterfaceFactory()
    ci_2 = ComponentInterfaceFactory()

    response = get_view_for_user(
        viewname="algorithms:interface-create",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": alg.slug},
        data={
            "inputs": [ci_1.pk],
            "outputs": [ci_2.pk],
        },
        user=user,
    )
    assert response.status_code == 302

    assert AlgorithmInterface.objects.count() == 1
    io = AlgorithmInterface.objects.get()
    assert io.inputs.get() == ci_1
    assert io.outputs.get() == ci_2

    assert AlgorithmAlgorithmInterface.objects.count() == 1
    io_through = AlgorithmAlgorithmInterface.objects.get()
    assert io_through.algorithm == alg
    assert io_through.interface == io


@pytest.mark.django_db
def test_algorithm_interfaces_list_queryset(client):
    user = UserFactory()
    assign_perm("algorithms.add_algorithm", user)
    alg, alg2 = AlgorithmFactory.create_batch(2)
    alg.add_editor(user)
    VerificationFactory(user=user, is_verified=True)

    io1, io2, io3, io4 = AlgorithmInterfaceFactory.create_batch(4)

    alg.interfaces.set([io1, io2])
    alg2.interfaces.set([io3, io4])

    iots = AlgorithmAlgorithmInterface.objects.order_by("id").all()

    response = get_view_for_user(
        viewname="algorithms:interface-list",
        client=client,
        reverse_kwargs={"slug": alg.slug},
        user=user,
    )
    assert response.status_code == 200
    assert response.context["object_list"].count() == 2
    assert iots[0] in response.context["object_list"]
    assert iots[1] in response.context["object_list"]
    assert iots[2] not in response.context["object_list"]
    assert iots[3] not in response.context["object_list"]


@pytest.mark.django_db
def test_algorithm_interface_delete(client):
    user = UserFactory()
    assign_perm("algorithms.add_algorithm", user)
    alg = AlgorithmFactory()
    alg.add_editor(user)

    int1, int2 = AlgorithmInterfaceFactory.create_batch(2)
    alg.interfaces.add(int1)
    alg.interfaces.add(int2)

    response = get_view_for_user(
        viewname="algorithms:interface-delete",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": alg.slug,
            "interface_pk": int2.pk,
        },
        user=user,
    )
    assert response.status_code == 302
    # no interface was deleted
    assert AlgorithmInterface.objects.count() == 2
    # only the relation between interface and algorithm was deleted
    assert AlgorithmAlgorithmInterface.objects.count() == 1
    assert alg.interfaces.count() == 1
    assert alg.interfaces.get() == int1


@pytest.mark.django_db
def test_interface_select_for_job_view_permission(client):
    verified_user, unverified_user = UserFactory.create_batch(2)
    VerificationFactory(user=verified_user, is_verified=True)
    alg = AlgorithmFactory()
    alg.add_user(verified_user)
    alg.add_user(unverified_user)

    interface1 = AlgorithmInterfaceFactory(
        inputs=[ComponentInterfaceFactory()],
        outputs=[ComponentInterfaceFactory()],
    )
    interface2 = AlgorithmInterfaceFactory(
        inputs=[ComponentInterfaceFactory()],
        outputs=[ComponentInterfaceFactory()],
    )
    alg.interfaces.add(interface1)
    alg.interfaces.add(interface2)

    response = get_view_for_user(
        viewname="algorithms:job-interface-select",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=unverified_user,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="algorithms:job-interface-select",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=verified_user,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_interface_select_automatic_redirect(client):
    verified_user = UserFactory()
    VerificationFactory(user=verified_user, is_verified=True)
    alg = AlgorithmFactory()
    alg.add_user(verified_user)

    interface = AlgorithmInterfaceFactory(
        inputs=[ComponentInterfaceFactory()],
        outputs=[ComponentInterfaceFactory()],
    )
    alg.interfaces.add(interface)

    # with just 1 interface, user gets redirected immediately
    response = get_view_for_user(
        viewname="algorithms:job-interface-select",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=verified_user,
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "algorithms:job-create",
        kwargs={"slug": alg.slug, "interface_pk": interface.pk},
    )

    # with more than 1 interfaces, user has to choose the interface
    interface2 = AlgorithmInterfaceFactory(
        inputs=[ComponentInterfaceFactory()],
        outputs=[ComponentInterfaceFactory()],
    )
    alg.interfaces.add(interface2)
    response = get_view_for_user(
        viewname="algorithms:job-interface-select",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=verified_user,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_algorithm_statistics_view(client):
    alg = AlgorithmFactory()
    ai = AlgorithmImageFactory(algorithm=alg)
    user = UserFactory()
    alg.add_editor(user)

    response1 = get_view_for_user(
        viewname="algorithms:statistics",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=user,
    )

    assert response1.status_code == 200
    assert (
        "No usage statistics are available for this algorithm"
        in response1.rendered_content
    )

    succeeded_jobs = AlgorithmJobFactory.create_batch(
        10,
        algorithm_image=ai,
        creator=user,
        status=Job.SUCCESS,
        time_limit=alg.time_limit,
    )
    cancelled_jobs = AlgorithmJobFactory.create_batch(
        9,
        algorithm_image=ai,
        creator=user,
        status=Job.CANCELLED,
        time_limit=alg.time_limit,
    )
    failed_jobs = AlgorithmJobFactory.create_batch(
        8,
        algorithm_image=ai,
        creator=user,
        status=Job.FAILURE,
        time_limit=alg.time_limit,
    )
    total_jobs = len(succeeded_jobs) + len(cancelled_jobs) + len(failed_jobs)

    top_user_profile = user_profile_link(user)

    response2 = get_view_for_user(
        viewname="algorithms:statistics",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=user,
    )

    assert response2.status_code == 200
    assert "Succeeded" in response2.rendered_content
    assert f"<dd>{len(succeeded_jobs)}</dd>" in response2.rendered_content
    assert "Cancelled" in response2.rendered_content
    assert f"<dd>{len(cancelled_jobs)}</dd>" in response2.rendered_content
    assert "Failed" in response2.rendered_content
    assert f"<dd>{len(failed_jobs)}</dd>" in response2.rendered_content
    assert top_user_profile in response2.rendered_content
    assert f"{total_jobs} jobs" in response2.rendered_content


@pytest.mark.django_db
def test_algorithm_create_redirect(client):
    user = UserFactory()
    VerificationFactory(user=user, is_verified=True)

    open_phase, closed_phase, non_public_phase, non_participant_phase = (
        PhaseFactory.create_batch(
            4,
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=1,
        )
    )

    open_phase.challenge.add_participant(user=user)
    closed_phase.challenge.add_participant(user=user)

    non_public_phase.challenge.add_participant(user=user)
    non_public_phase.public = False
    non_public_phase.save()

    InvoiceFactory(
        challenge=open_phase.challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )

    response = get_view_for_user(
        viewname="algorithms:create-redirect",
        client=client,
        user=user,
    )

    assert response.status_code == 200
    assert {*response.context["form"].fields["phase"].queryset} == {
        open_phase,
        closed_phase,
    }

    response = get_view_for_user(
        viewname="algorithms:create-redirect",
        client=client,
        user=user,
        method=client.post,
        data={"phase": open_phase.pk},
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "evaluation:phase-algorithm-create",
        kwargs={
            "challenge_short_name": open_phase.challenge.short_name,
            "slug": open_phase.slug,
        },
    )

    response = get_view_for_user(
        viewname="algorithms:create-redirect",
        client=client,
        user=user,
        method=client.post,
        data={"phase": closed_phase.pk},
    )

    assert response.status_code == 200
    assert response.context["form"].errors == {
        "phase": [
            "This phase is not currently open for submissions, please try again later."
        ]
    }
