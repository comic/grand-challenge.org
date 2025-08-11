import io
import json
import zipfile
from datetime import timedelta
from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import override_settings
from django.utils import timezone
from factory.django import ImageField
from guardian.shortcuts import assign_perm, remove_perm
from requests import put

from grandchallenge.algorithms.models import Algorithm, AlgorithmInterface, Job
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    ImportStatusChoices,
    InterfaceKind,
    InterfaceKindChoices,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.evaluation.models import (
    CombinedLeaderboard,
    Evaluation,
    PhaseAlgorithmInterface,
    Submission,
)
from grandchallenge.evaluation.tasks import update_combined_leaderboard
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import (
    PaymentStatusChoices,
    PaymentTypeChoices,
)
from grandchallenge.uploads.models import UserUpload
from grandchallenge.workstations.models import Workstation
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.cases_tests import RESOURCE_PATH
from tests.cases_tests.factories import (
    ImageFileFactoryWithMHDFile,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
from tests.evaluation_tests.factories import (
    CombinedLeaderboardFactory,
    EvaluationFactory,
    EvaluationGroundTruthFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import (
    ChallengeFactory,
    ChallengeRequestFactory,
    GroupFactory,
    ImageFactory,
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
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


class PhaseWithInputs(NamedTuple):
    phase: PhaseFactory
    admin: UserFactory
    algorithm: AlgorithmFactory
    ci_str: ComponentInterfaceFactory
    ci_bool: ComponentInterfaceFactory
    ci_img_upload: ComponentInterfaceFactory
    ci_existing_img: ComponentInterfaceFactory
    ci_json_in_db_with_schema: ComponentInterfaceFactory
    ci_json_file: ComponentInterfaceFactory
    im_upload_through_api: RawImageUploadSessionFactory
    im_upload_through_ui: UserUploadFactory
    file_upload: UserUploadFactory
    image_1: ImageFactory
    image_2: ImageFactory


@pytest.fixture
def algorithm_phase_with_multiple_inputs():
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
    algorithm = AlgorithmFactory()
    ai = AlgorithmImageFactory(
        algorithm=algorithm,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    AlgorithmModelFactory(
        algorithm=algorithm,
        is_desired_version=True,
    )

    alg_in = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.STRING
    )
    interface = AlgorithmInterfaceFactory(
        inputs=[alg_in],
        outputs=[ComponentInterfaceFactory()],
    )
    ai.algorithm.interfaces.add(interface)

    admin = UserFactory()
    VerificationFactory(user=admin, is_verified=True)
    algorithm.add_editor(admin)
    phase.challenge.add_admin(user=admin)
    phase.algorithm_interfaces.add(interface)

    MethodFactory(
        phase=phase,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    archive = ArchiveFactory()
    phase.archive = archive
    phase.save()

    item = ArchiveItemFactory(archive=archive)
    item.values.add(
        ComponentInterfaceValueFactory(interface=alg_in, value="foo")
    )

    InvoiceFactory(
        challenge=phase.challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )

    # create interfaces of different kinds
    ci_str = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.STRING
    )
    ci_bool = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
    ci_img_upload = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.IMAGE
    )
    ci_existing_img = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.IMAGE
    )
    ci_json_in_db_with_schema = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY,
        store_in_database=True,
        schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "array",
        },
    )
    ci_json_file = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.ANY,
        store_in_database=False,
        schema={
            "$schema": "http://json-schema.org/draft-07/schema",
            "type": "array",
        },
    )

    # Create inputs
    im_upload_through_api = RawImageUploadSessionFactory(creator=admin)
    image_1, image_2 = ImageFactory.create_batch(2)
    mhd1, mhd2 = ImageFileFactoryWithMHDFile.create_batch(2)
    image_1.files.set([mhd1])
    image_2.files.set([mhd2])
    for im in [image_1, image_2]:
        assign_perm("cases.view_image", admin, im)
    im_upload_through_api.image_set.set([image_1])

    im_upload_through_ui = create_upload_from_file(
        file_path=RESOURCE_PATH / "image10x10x10.mha",
        creator=admin,
    )

    file_upload = UserUploadFactory(filename="file.json", creator=admin)
    presigned_urls = file_upload.generate_presigned_urls(part_numbers=[1])
    response = put(presigned_urls["1"], data=b'["Foo", "bar"]')
    file_upload.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    file_upload.save()

    return PhaseWithInputs(
        phase=phase,
        algorithm=ai.algorithm,
        admin=admin,
        ci_str=ci_str,
        ci_bool=ci_bool,
        ci_img_upload=ci_img_upload,
        ci_existing_img=ci_existing_img,
        ci_json_in_db_with_schema=ci_json_in_db_with_schema,
        ci_json_file=ci_json_file,
        im_upload_through_api=im_upload_through_api,
        im_upload_through_ui=im_upload_through_ui,
        file_upload=file_upload,
        image_1=image_1,
        image_2=image_2,
    )


@pytest.mark.django_db
class TestLoginViews:
    def test_login_redirect(self, client):
        e = EvaluationFactory(time_limit=60)

        for view_name, kwargs in [
            ("phase-create", {}),
            ("phase-update", {"slug": e.submission.phase.slug}),
            ("method-create", {"slug": e.submission.phase.slug}),
            ("method-list", {"slug": e.submission.phase.slug}),
            (
                "method-detail",
                {"pk": e.method.pk, "slug": e.submission.phase.slug},
            ),
            ("submission-create", {"slug": e.submission.phase.slug}),
            ("submission-list", {}),
            (
                "submission-detail",
                {"pk": e.submission.pk, "slug": e.submission.phase.slug},
            ),
            ("list", {"slug": e.submission.phase.slug}),
            ("update", {"pk": e.pk}),
        ]:
            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=None,
            )

            assert response.status_code == 302
            assert response.url.startswith(
                f"https://testserver/accounts/login/?next=http%3A//"
                f"{e.submission.phase.challenge.short_name}.testserver/"
            )

    def test_open_views(self, client):
        e = EvaluationFactory(
            submission__phase__challenge__hidden=False, time_limit=60
        )

        for view_name, kwargs in [
            ("leaderboard", {"slug": e.submission.phase.slug}),
            ("detail", {"pk": e.pk}),
        ]:
            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=None,
            )

            assert response.status_code == 200


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        e = EvaluationFactory(time_limit=60)
        u = UserFactory()
        VerificationFactory(user=u, is_verified=True)
        group = Group.objects.create(name="test-group")
        group.user_set.add(u)

        for view_name, kwargs, permission, obj in [
            (
                "phase-create",
                {},
                "change_challenge",
                e.submission.phase.challenge,
            ),
            (
                "phase-update",
                {"slug": e.submission.phase.slug},
                "change_phase",
                e.submission.phase,
            ),
            (
                "method-create",
                {"slug": e.submission.phase.slug},
                "change_challenge",
                e.submission.phase.challenge,
            ),
            (
                "method-detail",
                {"pk": e.method.pk, "slug": e.submission.phase.slug},
                "view_method",
                e.method,
            ),
            (
                "method-import-status-detail",
                {"pk": e.method.pk, "slug": e.submission.phase.slug},
                "view_method",
                e.method,
            ),
            (
                "method-update",
                {"pk": e.method.pk, "slug": e.submission.phase.slug},
                "change_method",
                e.method,
            ),
            (
                "submission-create",
                {"slug": e.submission.phase.slug},
                "create_phase_submission",
                e.submission.phase,
            ),
            (
                "evaluation-create",
                {"slug": e.submission.phase.slug, "pk": e.submission.pk},
                "change_challenge",
                e.submission.phase.challenge,
            ),
            (
                "submission-detail",
                {"pk": e.submission.pk, "slug": e.submission.phase.slug},
                "view_submission",
                e.submission,
            ),
        ]:
            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=u,
            )

            assert response.status_code == 403

            assign_perm(permission, group, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=u,
            )

            assert response.status_code == 200

            remove_perm(permission, group, obj)

    def test_group_permission_required_views(self, client):
        e = EvaluationFactory(time_limit=60)
        u = UserFactory()
        g = GroupFactory()
        g.user_set.add(u)
        VerificationFactory(user=u, is_verified=True)

        for view_name, kwargs, permission, obj in [
            ("update", {"pk": e.pk}, "change_evaluation", e),
            ("detail", {"pk": e.pk}, "view_evaluation", e),
            (
                "status-detail",
                {"pk": e.pk},
                "view_evaluation",
                e,
            ),
            (
                "evaluation-incomplete-jobs-detail",
                {"pk": e.pk},
                "change_evaluation",
                e,
            ),
        ]:
            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=u,
            )

            assert response.status_code == 403

            with pytest.raises(RuntimeError) as err:
                assign_perm(permission, u, obj)

            assert (
                f"{permission} should not be assigned to users for this model"
                in str(err.value)
            )

            assign_perm(permission, g, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=u,
            )

            assert response.status_code == 200

            remove_perm(permission, g, obj)

    def test_permission_filtered_views(self, client):
        u = UserFactory()
        p = PhaseFactory()
        m = MethodFactory(phase=p)
        s = SubmissionFactory(phase=p)
        e = EvaluationFactory(
            method=m,
            submission=s,
            rank=1,
            status=Evaluation.SUCCESS,
            time_limit=s.phase.evaluation_time_limit,
        )
        group = Group.objects.create(name="test-group")
        group.user_set.add(u)

        for view_name, kwargs, permission, obj in [
            (
                "method-list",
                {"slug": e.submission.phase.slug},
                "view_method",
                m,
            ),
            ("submission-list", {}, "view_submission", s),
        ]:
            assign_perm(permission, group, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=u,
            )

            assert response.status_code == 200
            assert obj in response.context[-1]["object_list"]

            remove_perm(permission, group, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=u,
            )

            assert response.status_code == 200
            assert obj not in response.context[-1]["object_list"]

    def test_group_only_permission_filtered_views(self, client):
        u = UserFactory()
        p = PhaseFactory()
        m = MethodFactory(phase=p)
        s = SubmissionFactory(phase=p, creator=u)
        e = EvaluationFactory(
            method=m,
            submission=s,
            rank=1,
            status=Evaluation.SUCCESS,
            time_limit=s.phase.evaluation_time_limit,
        )
        g = GroupFactory()
        g.user_set.add(u)

        for view_name, kwargs, permission, obj in [
            ("list", {"slug": e.submission.phase.slug}, "view_evaluation", e),
            (
                "leaderboard",
                {"slug": e.submission.phase.slug},
                "view_evaluation",
                e,
            ),
        ]:
            with pytest.raises(RuntimeError) as err:
                assign_perm(permission, u, obj)

            assert (
                f"{permission} should not be assigned to users for this model"
                in str(err.value)
            )

            assign_perm(permission, g, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=u,
            )

            assert response.status_code == 200
            assert obj in response.context[-1]["object_list"]

            remove_perm(permission, g, obj)

            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e.submission.phase.challenge.short_name,
                    **kwargs,
                },
                user=u,
            )

            assert response.status_code == 200
            assert obj not in response.context[-1]["object_list"]


@pytest.mark.django_db
class TestViewFilters:
    def test_challenge_filtered_views(self, client):
        c1, c2 = ChallengeFactory.create_batch(2, hidden=False)

        PhaseFactory(challenge=c1)
        PhaseFactory(challenge=c2)

        u = UserFactory()
        e1 = EvaluationFactory(
            method__phase=c1.phase_set.first(),
            submission__phase=c1.phase_set.first(),
            submission__creator=u,
            time_limit=c1.phase_set.first().evaluation_time_limit,
        )
        e2 = EvaluationFactory(
            method__phase=c2.phase_set.first(),
            submission__phase=c2.phase_set.first(),
            submission__creator=u,
            time_limit=c2.phase_set.first().evaluation_time_limit,
        )

        group = Group.objects.create(name="test-group")
        group.user_set.add(u)

        assign_perm("view_method", group, e1.method)
        assign_perm("view_method", group, e2.method)

        for view_name, obj, extra_kwargs in [
            ("method-list", e1.method, {"slug": e1.submission.phase.slug}),
            ("submission-list", e1.submission, {}),
            ("list", e1, {"slug": e1.submission.phase.slug}),
        ]:
            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e1.submission.phase.challenge.short_name,
                    **extra_kwargs,
                },
                user=u,
            )

            assert response.status_code == 200
            assert {obj.pk} == {
                o.pk for o in response.context[-1]["object_list"]
            }

    def test_phase_filtered_views(self, client):
        c = ChallengeFactory(hidden=False)

        p1, p2 = PhaseFactory.create_batch(2, challenge=c)

        e1 = EvaluationFactory(
            method__phase=p1,
            submission__phase=p1,
            rank=1,
            status=Evaluation.SUCCESS,
            time_limit=p1.evaluation_time_limit,
        )
        _ = EvaluationFactory(
            method__phase=p2,
            submission__phase=p2,
            rank=1,
            status=Evaluation.SUCCESS,
            time_limit=p2.evaluation_time_limit,
        )

        response = get_view_for_user(
            client=client,
            viewname="evaluation:leaderboard",
            reverse_kwargs={
                "challenge_short_name": e1.submission.phase.challenge.short_name,
                "slug": e1.submission.phase.slug,
            },
        )

        assert response.status_code == 200
        assert {e1.pk} == {o.pk for o in response.context[-1]["object_list"]}


@pytest.mark.django_db
def test_submission_time_limit(client, two_challenge_sets):
    phase = two_challenge_sets.challenge_set_1.challenge.phase_set.get()
    phase.submissions_limit_per_user_per_period = 10
    phase.save()

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    SubmissionFactory(
        phase=phase, creator=two_challenge_sets.challenge_set_1.participant
    )

    def get_submission_view():
        return get_view_for_user(
            viewname="evaluation:submission-create",
            client=client,
            user=two_challenge_sets.challenge_set_1.participant,
            reverse_kwargs={
                "challenge_short_name": two_challenge_sets.challenge_set_1.challenge.short_name,
                "slug": two_challenge_sets.challenge_set_1.challenge.phase_set.get().slug,
            },
        )

    assert "create 9 more" in get_submission_view().rendered_content

    s = SubmissionFactory(
        phase=phase, creator=two_challenge_sets.challenge_set_1.participant
    )
    s.created = timezone.now() - timedelta(hours=23)
    s.save()
    assert "create 8 more" in get_submission_view().rendered_content

    s = SubmissionFactory(
        phase=phase, creator=two_challenge_sets.challenge_set_1.participant
    )
    s.created = timezone.now() - timedelta(hours=25)
    s.save()
    assert "create 8 more" in get_submission_view().rendered_content


@pytest.mark.django_db
def test_hidden_phase_visible_for_admins_but_not_participants(client):
    ch = ChallengeFactory()
    PhaseFactory(challenge=ch)
    u = UserFactory()
    ch.add_participant(u)
    visible_phase = ch.phase_set.first()
    hidden_phase = PhaseFactory(challenge=ch, public=False)
    e1 = EvaluationFactory(
        submission__phase=visible_phase,
        submission__creator=u,
        time_limit=visible_phase.evaluation_time_limit,
    )
    e2 = EvaluationFactory(
        submission__phase=hidden_phase,
        submission__creator=u,
        time_limit=hidden_phase.evaluation_time_limit,
    )

    for view_name, kwargs, status in [
        # phase non-specific pages
        ("submission-list", {}, 200),
        # visible phase
        ("detail", {"pk": e1.pk}, 200),
        ("submission-create", {"slug": visible_phase.slug}, 200),
        (
            "submission-detail",
            {"pk": e1.submission.pk, "slug": e1.submission.phase.slug},
            200,
        ),
        ("leaderboard", {"slug": visible_phase.slug}, 200),
        # hidden phase
        ("detail", {"pk": e2.pk}, 403),
        ("submission-create", {"slug": hidden_phase.slug}, 403),
        (
            "submission-detail",
            {"pk": e2.submission.pk, "slug": e2.submission.phase.slug},
            403,
        ),
        ("leaderboard", {"slug": hidden_phase.slug}, 403),
    ]:
        # for participants only the visible phase tab is visible
        # and they do not have access to the detail pages of their evals and
        # submissions from the hidden phase, and do not see subs/evals from the hidden
        # phase on the respective list pages
        response = get_view_for_user(
            client=client,
            viewname=f"evaluation:{view_name}",
            reverse_kwargs={"challenge_short_name": ch.short_name, **kwargs},
            user=u,
        )

        assert response.status_code == status
        if status == 200:
            assert visible_phase.title in str(response.content)
            assert hidden_phase.title not in str(response.content)

        # for the admin both phases are visible and they have access to submissions
        # and evals from both phases
        response = get_view_for_user(
            client=client,
            viewname=f"evaluation:{view_name}",
            reverse_kwargs={"challenge_short_name": ch.short_name, **kwargs},
            user=ch.admins_group.user_set.first(),
        )
        assert response.status_code == 200
        assert visible_phase.title in str(response.content)
        assert hidden_phase.title in str(response.content)


@pytest.mark.django_db
def test_create_algorithm_for_phase_permission(client, uploaded_image):
    phase = PhaseFactory()
    admin, participant, user = UserFactory.create_batch(3)
    phase.challenge.add_admin(admin)
    phase.challenge.add_participant(participant)

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    # admin can make a submission only if they are verified
    # and if the phase has been configured properly
    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=admin,
    )
    assert response.status_code == 403
    assert (
        "You need to first upload a logo for your challenge before you can create algorithms for its phases."
        in str(response.content)
    )

    phase.challenge.logo = uploaded_image()
    phase.challenge.save()
    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=admin,
    )
    assert response.status_code == 403
    assert "This phase is not configured for algorithm submission" in str(
        response.content
    )

    phase.submission_kind = SubmissionKindChoices.ALGORITHM
    phase.creator_must_be_verified = True
    phase.archive = ArchiveFactory()
    interface = AlgorithmInterfaceFactory()
    phase.algorithm_interfaces.set([interface])
    phase.save()

    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=admin,
    )
    assert "You need to verify your account before you can do this" in str(
        response.content
    )

    VerificationFactory(user=admin, is_verified=True)
    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=admin,
    )
    assert response.status_code == 200

    # participant can only create algorithm when verified,
    # when phase is open for submission and
    # when the phase has been configured properly (already the case here)
    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=participant,
    )
    assert response.status_code == 403
    assert "The phase is currently not open for submissions." in str(
        response.content
    )

    phase.submissions_limit_per_user_per_period = 1
    phase.save()

    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=participant,
    )
    assert response.status_code == 403
    assert "You need to verify your account before you can do this" in str(
        response.content
    )

    VerificationFactory(user=participant, is_verified=True)
    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=participant,
    )
    assert response.status_code == 200

    # normal user cannot create algorithm for phase
    VerificationFactory(user=user, is_verified=True)
    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=user,
    )
    assert response.status_code == 403
    assert (
        "You need to be either an admin or a participant of the challenge in order to create an algorithm for this phase."
        in str(response.content)
    )


@pytest.mark.django_db
def test_create_algorithm_for_phase_presets(client):
    phase = PhaseFactory(challenge__logo=ImageField(filename="test.jpeg"))
    admin = UserFactory()
    phase.challenge.add_admin(admin)
    VerificationFactory(user=admin, is_verified=True)

    phase.submission_kind = SubmissionKindChoices.ALGORITHM
    phase.creator_must_be_verified = True
    phase.archive = ArchiveFactory()
    ci1 = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    optional_protocol = HangingProtocolFactory()

    interface1, interface2 = AlgorithmInterfaceFactory.create_batch(2)
    phase.algorithm_interfaces.set([interface1, interface2])
    phase.hanging_protocol = HangingProtocolFactory(
        json=[{"viewport_name": "main"}]
    )
    phase.optional_hanging_protocols.set([optional_protocol])
    phase.workstation_config = WorkstationConfigFactory()
    phase.view_content = {"main": [ci1.slug]}
    phase.algorithm_time_limit = 10 * 60
    phase.save()

    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=admin,
    )
    assert {*response.context_data["form"]["interfaces"].initial.all()} == {
        interface1,
        interface2,
    }
    assert response.context_data["form"][
        "workstation"
    ].initial == Workstation.objects.get(
        slug=settings.DEFAULT_WORKSTATION_SLUG
    )
    assert (
        response.context_data["form"]["hanging_protocol"].initial
        == phase.hanging_protocol
    )
    assert (
        response.context_data["form"][
            "optional_hanging_protocols"
        ].initial.get()
        == optional_protocol
    )
    assert (
        response.context_data["form"]["workstation_config"].initial
        == phase.workstation_config
    )
    assert (
        response.context_data["form"]["view_content"].initial
        == phase.view_content
    )
    assert (
        response.context_data["form"]["contact_email"].initial == admin.email
    )
    assert response.context_data["form"]["display_editors"].initial
    assert (
        response.context_data["form"]["logo"].initial == phase.challenge.logo
    )
    assert {*response.context_data["form"]["modalities"].initial} == set()
    assert {*response.context_data["form"]["structures"].initial} == set()

    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        method=client.post,
        user=admin,
        data={
            "title": "GPT-5",
            "job_requires_memory_gb": 8,  # Fixed at 16 in disabled field
            "interfaces": [
                interface.pk
                for interface in response.context_data["form"][
                    "interfaces"
                ].initial.all()
            ],
            "workstation": response.context_data["form"][
                "workstation"
            ].initial.pk,
            "hanging_protocol": response.context_data["form"][
                "hanging_protocol"
            ].initial.pk,
            "optional_hanging_protocols": response.context_data["form"][
                "optional_hanging_protocols"
            ]
            .initial.get()
            .pk,
            "workstation_config": response.context_data["form"][
                "workstation_config"
            ].initial.pk,
            "view_content": json.dumps(
                response.context_data["form"]["view_content"].initial
            ),
            "logo": response.context_data["form"]["logo"].initial,
        },
    )

    assert response.status_code == 302
    assert Algorithm.objects.count() == 1
    algorithm = Algorithm.objects.get()
    assert {*algorithm.interfaces.all()} == {interface1, interface2}
    assert algorithm.hanging_protocol == phase.hanging_protocol
    assert algorithm.optional_hanging_protocols.get() == optional_protocol
    assert algorithm.workstation_config == phase.workstation_config
    assert algorithm.view_content == phase.view_content
    assert algorithm.workstation.slug == settings.DEFAULT_WORKSTATION_SLUG
    assert algorithm.contact_email == admin.email
    assert algorithm.display_editors is True
    assert {*algorithm.structures.all()} == set()
    assert {*algorithm.modalities.all()} == set()
    assert algorithm.logo == phase.challenge.logo
    assert algorithm.time_limit == 10 * 60
    assert algorithm.job_requires_memory_gb == 16

    # try to set different values
    ci3, ci4 = ComponentInterfaceFactory.create_batch(2)
    hp = HangingProtocolFactory()
    oph = HangingProtocolFactory()
    ws = WorkstationFactory()
    wsc = WorkstationConfigFactory()

    _ = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        method=client.post,
        user=admin,
        data={
            "title": "GPT-5",
            "job_requires_memory_gb": 8,  # Fixed at 16 in disabled field
            "interfaces": [interface1.pk],
            "workstation": ws.pk,
            "hanging_protocol": hp.pk,
            "optional_hanging_protocols": [oph.pk],
            "workstation_config": wsc.pk,
            "view_content": "{}",
        },
    )

    # created algorithm has the initial values set, not the modified ones
    alg2 = Algorithm.objects.last()
    assert {*alg2.interfaces.all()} == {interface1, interface2}
    assert alg2.hanging_protocol == phase.hanging_protocol
    assert alg2.optional_hanging_protocols.get() == optional_protocol
    assert alg2.workstation_config == phase.workstation_config
    assert alg2.view_content == phase.view_content
    assert alg2.workstation.slug == settings.DEFAULT_WORKSTATION_SLUG
    assert alg2.hanging_protocol != hp
    assert alg2.workstation_config != wsc
    assert alg2.view_content != "{}"
    assert alg2.workstation.slug != ws
    assert alg2.logo == phase.challenge.logo
    assert alg2.job_requires_memory_gb == 16


@pytest.mark.django_db
def test_create_algorithm_for_phase_limits(client):
    phase = PhaseFactory(challenge__logo=ImageField(filename="test.jpeg"))
    phase.submission_kind = SubmissionKindChoices.ALGORITHM
    phase.creator_must_be_verified = True
    phase.archive = ArchiveFactory()
    ci1 = ComponentInterfaceFactory()
    ci2 = ComponentInterfaceFactory()

    interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])
    phase.algorithm_interfaces.set([interface])

    phase.submissions_limit_per_user_per_period = 10
    phase.save()

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    u1, u2, u3 = UserFactory.create_batch(3)
    for user in [u1, u2, u3]:
        VerificationFactory(user=user, is_verified=True)
        phase.challenge.add_participant(user)

    alg1, alg2, alg3, alg4, alg5, alg6 = AlgorithmFactory.create_batch(6)
    alg1.add_editor(u1)
    alg1.add_editor(u2)
    alg2.add_editor(u1)
    alg3.add_editor(u1)
    alg4.add_editor(u2)
    alg5.add_editor(u1)
    alg6.add_editor(u2)
    for alg in [alg1, alg2, alg3, alg4]:
        alg.interfaces.set([interface])
    ci3 = ComponentInterfaceFactory()

    interface2 = AlgorithmInterfaceFactory(inputs=[ci1, ci3], outputs=[ci2])
    alg5.interfaces.set([interface2])

    interface3 = AlgorithmInterfaceFactory(inputs=[ci3], outputs=[ci2])
    alg6.interfaces.set([interface3])

    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=u3,
    )
    # u3 has not created any algorithms for the phase yet,
    # so will immediately see the form
    assert "Use the below form to create a new algorithm." in str(
        response.content
    )

    # u2 has created 2 algos, so will see a confirmation button and links to
    # existing algorithms with the same inputs and outputs
    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=u2,
    )
    assert "You have created 2 out of 3 possible algorithms" in str(
        response.content
    )
    assert {*response.context["user_algorithms"]} == {alg1, alg4}

    # clicking on confirm will show the form
    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=u2,
        data={"show_form": "True"},
    )
    assert "Use the below form to create a new algorithm." in str(
        response.content
    )

    # u1 has reached the limit of algorithms,
    # will see links to existing algorithms
    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=u1,
    )
    assert (
        "You have created the maximum number of allowed algorithms for this phase!"
        in str(response.content)
    )
    assert {*response.context["user_algorithms"]} == {alg1, alg2, alg3}

    # force submitting a form with data for a user that has reached the limit,
    # will not work, they will just get redirected to the page telling them that they
    # have reached the limit

    response = get_view_for_user(
        viewname="evaluation:phase-algorithm-create",
        method=client.post,
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=u1,
        data={
            "title": "Foo",
        },
    )
    assert (
        "You have created the maximum number of allowed algorithms for this phase!"
        in str(response.content)
    )
    assert {*response.context["user_algorithms"]} == {alg1, alg2, alg3}
    assert not Algorithm.objects.filter(title="foo").exists()


@pytest.mark.django_db
def test_evaluation_admin_list(client):
    u, admin = UserFactory.create_batch(2)
    ch = ChallengeFactory()
    ch.add_admin(admin)
    PhaseFactory(challenge=ch)
    m = MethodFactory(phase=ch.phase_set.get())
    s = SubmissionFactory(phase=ch.phase_set.get(), creator=u)
    e = EvaluationFactory(
        method=m,
        submission=s,
        rank=1,
        status=Evaluation.SUCCESS,
        time_limit=s.phase.evaluation_time_limit,
    )

    response = get_view_for_user(
        client=client,
        viewname="evaluation:list",
        reverse_kwargs={
            "challenge_short_name": ch.short_name,
            "slug": ch.phase_set.get().slug,
        },
        user=u,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname="evaluation:list",
        reverse_kwargs={
            "challenge_short_name": ch.short_name,
            "slug": ch.phase_set.get().slug,
        },
        user=admin,
    )
    assert response.status_code == 200
    assert e in response.context[-1]["object_list"]


@pytest.mark.django_db
def test_method_update_view(client):
    challenge = ChallengeFactory()
    method = MethodFactory(
        phase=PhaseFactory(challenge=challenge),
        phase__evaluation_requires_memory_gb=4,
    )
    user = UserFactory()

    challenge.add_admin(user=user)

    response = get_view_for_user(
        client=client,
        viewname="evaluation:method-update",
        reverse_kwargs={
            "challenge_short_name": challenge.short_name,
            "slug": method.phase.slug,
            "pk": method.pk,
        },
        user=user,
        method=client.post,
        data={"comment": "blah"},
    )

    assert response.status_code == 302

    method.refresh_from_db()
    assert method.comment == "blah"


@pytest.mark.django_db
def test_combined_leaderboard_create(client):
    ch1, ch2 = ChallengeFactory.create_batch(2)
    ph1 = PhaseFactory(challenge=ch1)
    _ = PhaseFactory(challenge=ch2)
    user = UserFactory()

    response = get_view_for_user(
        viewname="evaluation:combined-leaderboard-create",
        client=client,
        user=user,
        reverse_kwargs={"challenge_short_name": ch1.short_name},
    )
    assert response.status_code == 403

    ch1.add_admin(user)

    response = get_view_for_user(
        viewname="evaluation:combined-leaderboard-create",
        client=client,
        user=user,
        reverse_kwargs={"challenge_short_name": ch1.short_name},
    )
    assert response.status_code == 200
    # Only phases for this challenge
    assert {*response.context["form"].fields["phases"].queryset} == {ph1}

    response = get_view_for_user(
        viewname="evaluation:combined-leaderboard-create",
        client=client,
        method=client.post,
        user=user,
        reverse_kwargs={"challenge_short_name": ch1.short_name},
        data={
            "title": "combined",
            "phases": [ph1.pk],
            "combination_method": "MEAN",
        },
    )
    assert response.status_code == 302

    # Should be created for the first challenge
    assert CombinedLeaderboard.objects.get().challenge == ch1


@pytest.mark.django_db
def test_combined_leaderboard_delete(client):
    challenge = ChallengeFactory()
    _ = PhaseFactory(challenge=challenge)
    leaderboard = CombinedLeaderboardFactory(challenge=challenge)
    user = UserFactory()
    update_combined_leaderboard(pk=leaderboard.pk)

    # Sanity check
    assert CombinedLeaderboard.objects.filter(pk=leaderboard.pk).exists()
    assert cache.get(leaderboard.combined_ranks_cache_key) is not None

    view_args = {
        "viewname": "evaluation:combined-leaderboard-delete",
        "client": client,
        "user": user,
        "reverse_kwargs": {
            "challenge_short_name": challenge.short_name,
            "slug": leaderboard.slug,
        },
    }

    response = get_view_for_user(**view_args)
    assert response.status_code == 403

    challenge.add_admin(user)

    response = get_view_for_user(**view_args)
    assert response.status_code == 200

    response = get_view_for_user(
        method=client.post,
        **view_args,
    )
    assert response.status_code == 302

    assert not CombinedLeaderboard.objects.filter(pk=leaderboard.pk).exists()
    assert cache.get(leaderboard.combined_ranks_cache_key) is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "viewtype",
    ("detail", "update", "delete"),
)
def test_combined_leaderboard_only_visible_for_challenge(client, viewtype):
    ch1, ch2 = ChallengeFactory.create_batch(2)
    _ = PhaseFactory(challenge=ch1)
    _ = PhaseFactory(challenge=ch2)
    leaderboard = CombinedLeaderboardFactory(challenge=ch1)

    user = UserFactory()
    ch1.add_admin(user)
    ch2.add_admin(user)

    response = get_view_for_user(
        viewname=f"evaluation:combined-leaderboard-{viewtype}",
        client=client,
        reverse_kwargs={
            "challenge_short_name": ch1.short_name,
            "slug": leaderboard.slug,
        },
        user=user,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname=f"evaluation:combined-leaderboard-{viewtype}",
        client=client,
        reverse_kwargs={
            "challenge_short_name": ch2.short_name,
            "slug": leaderboard.slug,
        },
        user=user,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_update_view_permissions(client):
    ch1 = ChallengeFactory()
    ph1 = PhaseFactory(challenge=ch1)
    _ = PhaseFactory()
    leaderboard = CombinedLeaderboardFactory(challenge=ch1)

    user = UserFactory()

    response = get_view_for_user(
        viewname="evaluation:combined-leaderboard-update",
        client=client,
        reverse_kwargs={
            "challenge_short_name": ch1.short_name,
            "slug": leaderboard.slug,
        },
        user=user,
    )
    assert response.status_code == 403

    ch1.add_admin(user)

    response = get_view_for_user(
        viewname="evaluation:combined-leaderboard-update",
        client=client,
        reverse_kwargs={
            "challenge_short_name": ch1.short_name,
            "slug": leaderboard.slug,
        },
        user=user,
    )
    assert response.status_code == 200

    # Only phases for this challenge
    assert {*response.context["form"].fields["phases"].queryset} == {ph1}


@pytest.mark.django_db
def test_configure_algorithm_phases_permissions(client):
    user = UserFactory()
    ch = ChallengeFactory()
    response = get_view_for_user(
        viewname="evaluation:configure-algorithm-phases",
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": ch.short_name,
        },
    )
    assert response.status_code == 403

    assign_perm("evaluation.configure_algorithm_phase", user)
    response = get_view_for_user(
        viewname="evaluation:configure-algorithm-phases",
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": ch.short_name,
        },
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_configure_algorithm_phases_view(client):
    user = UserFactory()
    ch = ChallengeFactory()
    phase = PhaseFactory(
        challenge=ch, submission_kind=SubmissionKindChoices.CSV
    )
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)
    challenge_request = ChallengeRequestFactory(short_name=ch.short_name)
    assign_perm("evaluation.configure_algorithm_phase", user)
    response = get_view_for_user(
        viewname="evaluation:configure-algorithm-phases",
        client=client,
        method=client.post,
        user=user,
        reverse_kwargs={
            "challenge_short_name": ch.short_name,
        },
        data={
            "phases": [phase.pk],
        },
    )
    assert response.status_code == 302
    phase.refresh_from_db()
    assert phase.submission_kind == SubmissionKindChoices.ALGORITHM
    assert phase.creator_must_be_verified
    assert (
        phase.archive.title
        == f"{phase.challenge.short_name} {phase.title} dataset"
    )
    assert (
        phase.algorithm_time_limit
        == challenge_request.inference_time_limit_in_minutes * 60
    )
    assert (
        phase.algorithm_selectable_gpu_type_choices
        == challenge_request.algorithm_selectable_gpu_type_choices
    )
    assert (
        phase.algorithm_maximum_settable_memory_gb
        == challenge_request.algorithm_maximum_settable_memory_gb
    )


@pytest.mark.django_db
def test_ground_truth_permissions(client):
    phase = PhaseFactory()
    u = UserFactory()
    gt = EvaluationGroundTruthFactory(phase=phase)
    VerificationFactory(user=u, is_verified=True)
    group = Group.objects.create(name="test-group")
    group.user_set.add(u)

    for view_name, kwargs, permission, obj in [
        (
            "ground-truth-create",
            {},
            "evaluation.change_phase",
            phase,
        ),
        (
            "ground-truth-detail",
            {"pk": gt.pk},
            "evaluation.view_evaluationgroundtruth",
            gt,
        ),
        (
            "ground-truth-update",
            {"pk": gt.pk},
            "evaluation.change_evaluationgroundtruth",
            gt,
        ),
        (
            "ground-truth-import-status-detail",
            {"pk": gt.pk},
            "evaluation.view_evaluationgroundtruth",
            gt,
        ),
    ]:

        def _get_view():
            return get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": phase.challenge.short_name,
                    "slug": phase.slug,
                    **kwargs,
                },
                user=u,
            )

        response = _get_view()
        assert response.status_code == 403

        assign_perm(permission, group, obj)

        response = _get_view()
        assert response.status_code == 200

        remove_perm(permission, group, obj)


@pytest.mark.django_db
def test_ground_truth_version_management(settings, client):
    phase = PhaseFactory()
    gt1, gt2 = EvaluationGroundTruthFactory.create_batch(
        2, phase=phase, import_status=ImportStatusChoices.COMPLETED
    )
    gt2.is_desired_version = True
    gt2.save()

    admin, user = UserFactory.create_batch(2)
    phase.challenge.add_admin(admin)

    response = get_view_for_user(
        viewname="evaluation:ground-truth-activate",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        data={"ground_truth": gt1.pk},
        user=user,
    )
    assert response.status_code == 403

    response2 = get_view_for_user(
        viewname="evaluation:ground-truth-activate",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        data={"ground_truth": gt1.pk},
        user=admin,
    )

    assert response2.status_code == 302
    gt1.refresh_from_db()
    gt2.refresh_from_db()
    assert gt1.is_desired_version
    assert not gt2.is_desired_version
    assert phase.active_ground_truth == gt1

    response3 = get_view_for_user(
        viewname="evaluation:ground-truth-deactivate",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        data={"ground_truth": gt1.pk},
        user=user,
    )
    assert response3.status_code == 403

    response4 = get_view_for_user(
        viewname="evaluation:ground-truth-deactivate",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        data={"ground_truth": gt1.pk},
        user=admin,
    )

    assert response4.status_code == 302
    gt1.refresh_from_db()
    gt2.refresh_from_db()
    assert not gt1.is_desired_version
    assert not gt2.is_desired_version
    del phase.active_ground_truth
    assert not phase.active_ground_truth


@pytest.mark.django_db
def test_evaluation_details_zero_rank_message(client):
    phase = PhaseFactory(
        challenge__hidden=False,
        score_jsonpath="acc.mean",
        score_title="Accuracy Mean",
        extra_results_columns=[
            {"path": "dice.mean", "order": "asc", "title": "Dice mean"}
        ],
    )

    ci = ComponentInterface.objects.get(slug="metrics-json-file")
    civ = ComponentInterfaceValueFactory(
        interface=ci, value={"acc": {"std": 0.1, "mean": 0.0}}
    )

    evaluation = EvaluationFactory(
        submission__phase=phase,
        rank=0,
        status=Evaluation.SUCCESS,
        time_limit=phase.evaluation_time_limit,
    )

    evaluation.outputs.set([civ])

    response = get_view_for_user(
        viewname="evaluation:detail",
        client=client,
        method=client.get,
        reverse_kwargs={
            "pk": evaluation.pk,
        },
        user=phase.challenge.creator,
        challenge=phase.challenge,
    )

    assert response.status_code == 200
    assert str(evaluation.pk) in response.rendered_content
    assert str(phase.challenge.short_name) in response.rendered_content
    assert (
        oxford_comma(evaluation.invalid_metrics) in response.rendered_content
    )


@pytest.mark.django_db
def test_submission_create_sets_limits_correctly_with_algorithm(client):
    inputs = ComponentInterfaceFactory.create_batch(2)
    interface = AlgorithmInterfaceFactory(inputs=inputs)

    algorithm_image = AlgorithmImageFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
        algorithm__job_requires_gpu_type=GPUTypeChoices.V100,
        algorithm__job_requires_memory_gb=1337,
    )
    algorithm_image.algorithm.interfaces.set([interface])

    archive = ArchiveFactory()
    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.set(
        [
            ComponentInterfaceValueFactory(interface=interface)
            for interface in inputs
        ]
    )

    phase = PhaseFactory(
        archive=archive,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        submissions_limit_per_user_per_period=1,
        algorithm_selectable_gpu_type_choices=[GPUTypeChoices.V100],
        algorithm_maximum_settable_memory_gb=1337,
    )
    phase.algorithm_interfaces.set([interface])

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    MethodFactory(
        phase=phase,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    participant = UserFactory()
    phase.challenge.add_participant(user=participant)
    algorithm_image.algorithm.add_editor(user=participant)

    response = get_view_for_user(
        client=client,
        method=client.post,
        user=participant,
        viewname="evaluation:submission-create",
        reverse_kwargs={
            "challenge_short_name": phase.challenge.short_name,
            "slug": phase.slug,
        },
        data={
            "algorithm": algorithm_image.algorithm.pk,
            "creator": participant.pk,
            "phase": phase.pk,
        },
    )

    assert response.status_code == 302

    submission = Submission.objects.get()

    assert submission.algorithm_requires_gpu_type == GPUTypeChoices.V100
    assert submission.algorithm_requires_memory_gb == 1337


@pytest.mark.django_db
def test_submission_create_sets_limits_correctly_with_predictions(client):
    phase = PhaseFactory(
        submission_kind=SubmissionKindChoices.CSV,
        submissions_limit_per_user_per_period=1,
    )

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_type=PaymentTypeChoices.COMPLIMENTARY,
    )

    MethodFactory(
        phase=phase,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    participant = UserFactory()
    phase.challenge.add_participant(user=participant)

    user_upload = UserUploadFactory(creator=participant)
    user_upload.status = user_upload.StatusChoices.COMPLETED
    user_upload.save()

    response = get_view_for_user(
        client=client,
        method=client.post,
        user=participant,
        viewname="evaluation:submission-create",
        reverse_kwargs={
            "challenge_short_name": phase.challenge.short_name,
            "slug": phase.slug,
        },
        data={
            "creator": participant.pk,
            "phase": phase.pk,
            "user_upload": user_upload.pk,
        },
    )

    assert response.status_code == 302

    submission = Submission.objects.get()

    assert submission.algorithm_requires_gpu_type == GPUTypeChoices.NO_GPU
    assert submission.algorithm_requires_memory_gb == 0


@pytest.mark.django_db
def test_phase_archive_info_permissions(client):
    phase1, phase2 = PhaseFactory.create_batch(2, title="Test")
    editor, user = UserFactory.create_batch(2)
    phase1.challenge.add_admin(editor)

    response = get_view_for_user(
        client=client,
        viewname="evaluation:phase-archive-info",
        reverse_kwargs={
            "slug": phase2.slug,
            "challenge_short_name": phase2.challenge.short_name,
        },
        user=user,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname="evaluation:phase-archive-info",
        reverse_kwargs={
            "slug": phase2.slug,
            "challenge_short_name": phase2.challenge.short_name,
        },
        user=editor,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname="evaluation:phase-archive-info",
        reverse_kwargs={
            "slug": phase1.slug,
            "challenge_short_name": phase1.challenge.short_name,
        },
        user=user,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname="evaluation:phase-archive-info",
        reverse_kwargs={
            "slug": phase1.slug,
            "challenge_short_name": phase1.challenge.short_name,
        },
        user=editor,
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "viewname",
    [
        "evaluation:interface-list",
        "evaluation:interface-create",
        "evaluation:interfaces-copy",
    ],
)
@pytest.mark.django_db
def test_algorithm_interface_for_phase_view_permission(client, viewname):
    (participant, admin, user, user_with_perm) = UserFactory.create_batch(4)
    assign_perm("evaluation.configure_algorithm_phase", user_with_perm)

    prediction_phase = PhaseFactory(submission_kind=SubmissionKindChoices.CSV)
    algorithm_phase = PhaseFactory(
        submission_kind=SubmissionKindChoices.ALGORITHM
    )

    for phase in [prediction_phase, algorithm_phase]:
        phase.challenge.add_admin(admin)
        phase.challenge.add_participant(participant)

    for us, status1, status2 in [
        [user, 403, 403],
        [participant, 403, 403],
        [admin, 403, 403],
        [user_with_perm, 404, 200],
    ]:
        response = get_view_for_user(
            viewname=viewname,
            client=client,
            reverse_kwargs={
                "slug": prediction_phase.slug,
                "challenge_short_name": prediction_phase.challenge.short_name,
            },
            user=us,
        )
        assert response.status_code == status1

        response = get_view_for_user(
            viewname=viewname,
            client=client,
            reverse_kwargs={
                "slug": algorithm_phase.slug,
                "challenge_short_name": algorithm_phase.challenge.short_name,
            },
            user=us,
        )
        assert response.status_code == status2


@pytest.mark.django_db
def test_algorithm_interface_for_phase_delete_permission(client):
    (participant, admin, user, user_with_perm) = UserFactory.create_batch(4)
    assign_perm("evaluation.configure_algorithm_phase", user_with_perm)
    prediction_phase = PhaseFactory(submission_kind=SubmissionKindChoices.CSV)
    algorithm_phase = PhaseFactory(
        submission_kind=SubmissionKindChoices.ALGORITHM
    )
    int1 = AlgorithmInterfaceFactory()

    for phase in [prediction_phase, algorithm_phase]:
        phase.challenge.add_admin(admin)
        phase.challenge.add_participant(participant)
        phase.algorithm_interfaces.add(int1)

    for us, status1, status2 in [
        [user, 403, 403],
        [participant, 403, 403],
        [admin, 403, 403],
        [user_with_perm, 404, 200],
    ]:
        response = get_view_for_user(
            viewname="evaluation:interface-delete",
            client=client,
            reverse_kwargs={
                "slug": prediction_phase.slug,
                "interface_pk": int1.pk,
                "challenge_short_name": prediction_phase.challenge.short_name,
            },
            user=us,
        )
        assert response.status_code == status1

        response = get_view_for_user(
            viewname="evaluation:interface-delete",
            client=client,
            reverse_kwargs={
                "slug": algorithm_phase.slug,
                "interface_pk": int1.pk,
                "challenge_short_name": algorithm_phase.challenge.short_name,
            },
            user=us,
        )
        assert response.status_code == status2


@pytest.mark.django_db
def test_algorithm_interface_for_phase_create(client):
    user = UserFactory()
    assign_perm("evaluation.configure_algorithm_phase", user)
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)

    ci_1 = ComponentInterfaceFactory()
    ci_2 = ComponentInterfaceFactory()

    response = get_view_for_user(
        viewname="evaluation:interface-create",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
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

    assert PhaseAlgorithmInterface.objects.count() == 1
    io_through = PhaseAlgorithmInterface.objects.get()
    assert io_through.phase == phase
    assert io_through.interface == io


@pytest.mark.django_db
def test_algorithm_interfaces_for_phase_list_queryset(client):
    user = UserFactory()
    assign_perm("evaluation.configure_algorithm_phase", user)
    phase1, phase2 = PhaseFactory.create_batch(
        2, submission_kind=SubmissionKindChoices.ALGORITHM
    )

    io1, io2, io3, io4 = AlgorithmInterfaceFactory.create_batch(4)

    phase1.algorithm_interfaces.set([io1, io2])
    phase2.algorithm_interfaces.set([io3, io4])

    iots = PhaseAlgorithmInterface.objects.order_by("id").all()

    response = get_view_for_user(
        viewname="evaluation:interface-list",
        client=client,
        reverse_kwargs={
            "slug": phase1.slug,
            "challenge_short_name": phase1.challenge.short_name,
        },
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
    assign_perm("evaluation.configure_algorithm_phase", user)
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)

    int1, int2 = AlgorithmInterfaceFactory.create_batch(2)
    phase.algorithm_interfaces.add(int1)
    phase.algorithm_interfaces.add(int2)

    response = get_view_for_user(
        viewname="evaluation:interface-delete",
        client=client,
        method=client.post,
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
            "interface_pk": int2.pk,
        },
        user=user,
    )
    assert response.status_code == 302
    # no interface was deleted
    assert AlgorithmInterface.objects.count() == 2
    # only the relation between interface and algorithm was deleted
    assert PhaseAlgorithmInterface.objects.count() == 1
    assert phase.algorithm_interfaces.count() == 1
    assert phase.algorithm_interfaces.get() == int1


@pytest.mark.django_db
def test_evaluation_details_error_message(client):
    evaluation_error_message = "Test evaluation error message"

    evaluation = EvaluationFactory(time_limit=60)

    response = get_view_for_user(
        viewname="evaluation:detail",
        client=client,
        method=client.get,
        reverse_kwargs={
            "pk": evaluation.pk,
        },
        user=evaluation.submission.phase.challenge.creator,
        challenge=evaluation.submission.phase.challenge,
    )

    assert response.status_code == 200
    assert evaluation_error_message not in response.rendered_content

    evaluation.error_message = "Test evaluation error message"
    evaluation.save()

    response = get_view_for_user(
        viewname="evaluation:detail",
        client=client,
        method=client.get,
        reverse_kwargs={
            "pk": evaluation.pk,
        },
        user=evaluation.submission.phase.challenge.creator,
        challenge=evaluation.submission.phase.challenge,
    )

    assert response.status_code == 200
    assert evaluation_error_message in response.rendered_content


@pytest.mark.django_db
def test_submission_list_row_template_ajax_renders(client):
    editor = UserFactory()

    phase = PhaseFactory()
    phase.challenge.add_admin(editor)
    SubmissionFactory(phase=phase)

    headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    response = get_view_for_user(
        viewname="evaluation:submission-list",
        client=client,
        method=client.get,
        reverse_kwargs={
            "challenge_short_name": phase.challenge.short_name,
        },
        user=editor,
        data={
            "draw": "1",
            "length": "25",
        },
        **headers,
    )
    response_content = json.loads(response.content.decode("utf-8"))

    assert response.status_code == 200
    assert response_content["recordsTotal"] == 1
    assert len(response_content["data"][0]) == 5
    assert phase.title in response_content["data"][0][1]


@pytest.mark.django_db
class TestSubmissionCreationWithExtraInputs:
    def create_submission(
        self,
        client,
        django_capture_on_commit_callbacks,
        user,
        extra_inputs,
        phase,
        algorithm,
    ):
        with patch(
            "grandchallenge.evaluation.tasks.create_algorithm_jobs_for_evaluation"
        ) as mocked_execute_eval:
            # no need to actually execute the evaluation
            # we just want to check that the additional inputs are validated and
            # attached
            mocked_execute_eval.return_value = None
            with django_capture_on_commit_callbacks(execute=True):
                response = get_view_for_user(
                    viewname="evaluation:submission-create",
                    client=client,
                    method=client.post,
                    user=user,
                    reverse_kwargs={
                        "challenge_short_name": phase.challenge.short_name,
                        "slug": phase.slug,
                    },
                    data={
                        "algorithm": algorithm.pk,
                        "creator": user.pk,
                        "phase": phase.pk,
                        **extra_inputs,
                    },
                    follow=True,
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
    def test_create_submission_with_multiple_inputs(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_phase_with_multiple_inputs,
    ):
        # configure multiple additional evaluation inputs
        algorithm_phase_with_multiple_inputs.phase.additional_evaluation_inputs.set(
            [
                algorithm_phase_with_multiple_inputs.ci_json_in_db_with_schema,
                algorithm_phase_with_multiple_inputs.ci_existing_img,
                algorithm_phase_with_multiple_inputs.ci_str,
                algorithm_phase_with_multiple_inputs.ci_bool,
                algorithm_phase_with_multiple_inputs.ci_json_file,
                algorithm_phase_with_multiple_inputs.ci_img_upload,
            ]
        )

        assert (
            ComponentInterfaceValue.objects.count() == 1
        )  # the archive item in the linked archive

        response = self.create_submission(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_phase_with_multiple_inputs.algorithm,
            user=algorithm_phase_with_multiple_inputs.admin,
            phase=algorithm_phase_with_multiple_inputs.phase,
            extra_inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_str.slug,
                    data="Foo",
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_bool.slug,
                    data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_img_upload.slug,
                    data=algorithm_phase_with_multiple_inputs.im_upload_through_ui.pk,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_existing_img.slug,
                    data=algorithm_phase_with_multiple_inputs.image_1.pk,
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_json_file.slug,
                    data=algorithm_phase_with_multiple_inputs.file_upload.pk,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    data='["Foo", "bar"]',
                ),
            },
        )
        assert response.status_code == 200

        assert Submission.objects.count() == 1
        assert Evaluation.objects.count() == 1

        eval = Evaluation.objects.get()

        assert (
            eval.submission.algorithm_image
            == algorithm_phase_with_multiple_inputs.algorithm.active_image
        )
        assert (
            eval.submission.algorithm_model
            == algorithm_phase_with_multiple_inputs.algorithm.active_model
        )
        assert eval.time_limit == 3600
        assert eval.inputs.count() == 6

        assert not UserUpload.objects.filter(
            pk=algorithm_phase_with_multiple_inputs.file_upload.pk
        ).exists()

        assert sorted(
            [
                int.pk
                for int in algorithm_phase_with_multiple_inputs.phase.additional_evaluation_inputs.all()
            ]
        ) == sorted([civ.interface.pk for civ in eval.inputs.all()])

        value_inputs = [civ.value for civ in eval.inputs.all() if civ.value]
        assert "Foo" in value_inputs
        assert True in value_inputs
        assert ["Foo", "bar"] in value_inputs

        image_inputs = [
            civ.image.name for civ in eval.inputs.all() if civ.image
        ]
        assert (
            algorithm_phase_with_multiple_inputs.image_1.name in image_inputs
        )
        assert "image10x10x10.mha" in image_inputs
        assert (
            algorithm_phase_with_multiple_inputs.file_upload.filename.split(
                "."
            )[0]
            in [civ.file for civ in eval.inputs.all() if civ.file][0].name
        )

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_existing_inputs(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_phase_with_multiple_inputs,
    ):
        # configure multiple inputs
        algorithm_phase_with_multiple_inputs.phase.additional_evaluation_inputs.set(
            [
                algorithm_phase_with_multiple_inputs.ci_json_in_db_with_schema,
                algorithm_phase_with_multiple_inputs.ci_existing_img,
                algorithm_phase_with_multiple_inputs.ci_str,
                algorithm_phase_with_multiple_inputs.ci_bool,
                algorithm_phase_with_multiple_inputs.ci_json_file,
            ]
        )

        civ1, civ2, civ3, civ4, civ5 = self.create_existing_civs(
            interface_data=algorithm_phase_with_multiple_inputs
        )

        # create a job with the existing file so that the user has permission to reuse it
        old_job_with_only_file_input = AlgorithmJobFactory(
            algorithm_image=algorithm_phase_with_multiple_inputs.algorithm.active_image,
            algorithm_model=algorithm_phase_with_multiple_inputs.algorithm.active_model,
            status=Job.SUCCESS,
            time_limit=10,
            creator=algorithm_phase_with_multiple_inputs.admin,
        )
        old_job_with_only_file_input.inputs.set([civ5])

        old_civ_count = ComponentInterfaceValue.objects.count()

        response = self.create_submission(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_phase_with_multiple_inputs.algorithm,
            user=algorithm_phase_with_multiple_inputs.admin,
            phase=algorithm_phase_with_multiple_inputs.phase,
            extra_inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_str.slug,
                    data="Foo",
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_bool.slug,
                    data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_existing_img.slug,
                    data=algorithm_phase_with_multiple_inputs.image_1.pk,
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_json_file.slug,
                    data=civ5.pk,
                    existing_data=True,
                ),
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    data='["Foo", "bar"]',
                ),
            },
        )
        assert response.status_code == 200
        # no new CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == old_civ_count
        assert Submission.objects.count() == 1
        assert Evaluation.objects.count() == 1
        eval = Evaluation.objects.last()
        assert eval.inputs.count() == 5
        for civ in [civ1, civ2, civ3, civ4, civ5]:
            assert civ in eval.inputs.all()

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_faulty_file_input(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_phase_with_multiple_inputs,
    ):
        # configure file input
        algorithm_phase_with_multiple_inputs.phase.additional_evaluation_inputs.set(
            [
                algorithm_phase_with_multiple_inputs.ci_json_file,
            ]
        )

        file_upload = UserUploadFactory(
            filename="file.json",
            creator=algorithm_phase_with_multiple_inputs.admin,
        )
        presigned_urls = file_upload.generate_presigned_urls(part_numbers=[1])
        response = put(presigned_urls["1"], data=b'{"Foo": "bar"}')
        file_upload.complete_multipart_upload(
            parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
        )
        file_upload.save()

        old_civ_count = ComponentInterfaceValue.objects.count()

        response = self.create_submission(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_phase_with_multiple_inputs.algorithm,
            user=algorithm_phase_with_multiple_inputs.admin,
            phase=algorithm_phase_with_multiple_inputs.phase,
            extra_inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_json_file.slug,
                    data=file_upload.pk,
                ),
            },
        )
        assert response.status_code == 200
        # validation of files happens async, so submission and evaluation get created
        assert Submission.objects.count() == 1
        assert Evaluation.objects.count() == 1
        eval = Evaluation.objects.get()
        # but in cancelled state and with an error message
        assert eval.status == Evaluation.CANCELLED
        assert (
            "One or more of the inputs failed validation."
            == eval.error_message
        )
        assert eval.detailed_error_message == {
            algorithm_phase_with_multiple_inputs.ci_json_file.title: "Input validation failed"
        }
        # and no CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == old_civ_count

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_faulty_json_input(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_phase_with_multiple_inputs,
    ):
        algorithm_phase_with_multiple_inputs.phase.additional_evaluation_inputs.set(
            [
                algorithm_phase_with_multiple_inputs.ci_json_in_db_with_schema,
            ]
        )
        old_civ_count = ComponentInterfaceValue.objects.count()

        response = self.create_submission(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_phase_with_multiple_inputs.algorithm,
            user=algorithm_phase_with_multiple_inputs.admin,
            phase=algorithm_phase_with_multiple_inputs.phase,
            extra_inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    data='{"foo": "bar"}',
                ),
            },
        )
        # validation of values stored in DB happens synchronously,
        # so no job and no CIVs get created if validation fails
        # error message is reported back to user directly in the form
        assert response.status_code == 200
        assert "JSON does not fulfill schema" in str(response.content)
        assert Submission.objects.count() == 0
        assert Evaluation.objects.count() == 0
        assert ComponentInterfaceValue.objects.count() == old_civ_count

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_faulty_image_input(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_phase_with_multiple_inputs,
    ):
        algorithm_phase_with_multiple_inputs.phase.additional_evaluation_inputs.set(
            [
                algorithm_phase_with_multiple_inputs.ci_img_upload,
            ]
        )

        user_upload = create_upload_from_file(
            creator=algorithm_phase_with_multiple_inputs.admin,
            file_path=RESOURCE_PATH / "corrupt.png",
        )

        old_civ_count = ComponentInterfaceValue.objects.count()

        response = self.create_submission(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_phase_with_multiple_inputs.algorithm,
            user=algorithm_phase_with_multiple_inputs.admin,
            phase=algorithm_phase_with_multiple_inputs.phase,
            extra_inputs={
                **get_interface_form_data(
                    interface_slug=algorithm_phase_with_multiple_inputs.ci_img_upload.slug,
                    data=user_upload.pk,
                ),
            },
        )
        assert response.status_code == 200
        # validation of images happens async, so job gets created
        assert Submission.objects.count() == 1
        assert Evaluation.objects.count() == 1
        eval = Evaluation.objects.get()
        # but in cancelled state and with an error message
        assert eval.status == Evaluation.CANCELLED
        assert (
            "One or more of the inputs failed validation."
            == eval.error_message
        )
        assert "Input validation failed" in str(eval.detailed_error_message)
        # and no CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == old_civ_count


@pytest.mark.django_db
def test_parent_phase_algorithm_interfaces_locked(client):
    challenge = ChallengeFactory()
    phase, parent_phase = PhaseFactory.create_batch(
        2, challenge=challenge, submission_kind=SubmissionKindChoices.ALGORITHM
    )
    phase.parent = parent_phase
    phase.save()

    user = UserFactory()
    phase.challenge.add_admin(user)

    assert phase.algorithm_interfaces_locked
    assert parent_phase.algorithm_interfaces_locked

    interface = AlgorithmInterfaceFactory()

    for p in [phase, parent_phase]:
        p.algorithm_interfaces.set([interface])
        response = get_view_for_user(
            viewname="evaluation:interface-create",
            client=client,
            user=user,
            reverse_kwargs={
                "challenge_short_name": p.challenge.short_name,
                "slug": p.slug,
            },
        )
        assert response.status_code == 403

        response = get_view_for_user(
            viewname="evaluation:interface-delete",
            client=client,
            user=user,
            reverse_kwargs={
                "challenge_short_name": p.challenge.short_name,
                "slug": p.slug,
                "interface_pk": interface.pk,
            },
        )
        assert response.status_code == 403


@pytest.mark.django_db
def test_reschedule_evaluation_with_additional_inputs(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # create phase with inputs
    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)
    ci_str = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    ci_bool = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)
    phase.additional_evaluation_inputs.set([ci_str, ci_bool])

    archive = ArchiveFactory()
    phase.archive = archive
    phase.save()

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
    algorithm.add_editor(user)
    ai = AlgorithmImageFactory(algorithm=algorithm)

    civ_str = ComponentInterfaceValueFactory(interface=ci_str, value="Foo")
    civ_bool = ComponentInterfaceValueFactory(interface=ci_bool, value=True)

    submission = SubmissionFactory(
        phase=phase, creator=user, algorithm_image=ai
    )
    eval1 = EvaluationFactory(
        submission=submission,
        method=method,
        status=Evaluation.SUCCESS,
        time_limit=10,
    )
    eval1.inputs.set([civ_str, civ_bool])

    with django_capture_on_commit_callbacks(execute=False):
        response = get_view_for_user(
            viewname="evaluation:evaluation-create",
            client=client,
            method=client.post,
            user=user,
            reverse_kwargs={
                "challenge_short_name": phase.challenge.short_name,
                "slug": phase.slug,
                "pk": submission.pk,
            },
            data={
                **get_interface_form_data(
                    interface_slug=ci_str.slug, data="Bar"
                ),
                **get_interface_form_data(
                    interface_slug=ci_bool.slug, data=False
                ),
            },
        )

    assert response.status_code == 302

    eval2 = Evaluation.objects.exclude(pk=eval1.pk).get()
    evaluation_count = Evaluation.objects.count()

    assert evaluation_count == 2
    assert eval2.inputs.count() == 2
    assert civ_str not in eval2.inputs.all()
    assert civ_bool not in eval2.inputs.all()
    assert eval2.inputs.get(interface=ci_str).value == "Bar"
    assert not eval2.inputs.get(interface=ci_bool).value

    # mark eval2 as successful
    eval2.status = Evaluation.SUCCESS
    eval2.save()

    # try rerunning with identical inputs, that should fail
    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="evaluation:evaluation-create",
            client=client,
            method=client.post,
            user=user,
            reverse_kwargs={
                "challenge_short_name": phase.challenge.short_name,
                "slug": phase.slug,
                "pk": submission.pk,
            },
            data={
                **get_interface_form_data(
                    interface_slug=ci_str.slug, data="Bar"
                ),
                **get_interface_form_data(
                    interface_slug=ci_bool.slug, data=False
                ),
            },
        )

    assert response.status_code == 200
    assert (
        "A result for these inputs with the current method and ground truth already exists."
        in str(response.content)
    )
    assert Evaluation.objects.count() == evaluation_count


@pytest.mark.parametrize(
    "select_interfaces, status",
    (
        [[0, 1, 2], Evaluation.VALIDATING_INPUTS],  # full match
        [
            [0, 1],
            Evaluation.CANCELLED,
        ],  # different number, partially overlapping
        [
            [0, 1, 3],
            Evaluation.CANCELLED,
        ],  # same number, partially overlapping
        [
            [0, 1, 2, 3],
            Evaluation.VALIDATING_INPUTS,
        ],  # different number, but covering all the phase interfaces
    ),
)
@pytest.mark.django_db
def test_create_evaluation_requires_matching_algorithm_interfaces(
    select_interfaces, status
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

    submission.create_evaluation(additional_inputs=None)

    eval = Evaluation.objects.order_by("created").last()

    assert eval.status == status
    if status == Evaluation.CANCELLED:
        assert (
            "The algorithm interfaces do not match those defined for the phase."
            in str(eval.error_message)
        )


@pytest.mark.parametrize(
    "num_jobs, jobs_statuses, status",
    (
        [1, [Job.SUCCESS], Evaluation.VALIDATING_INPUTS],
        [1, [Job.FAILURE], Evaluation.CANCELLED],
        [2, [Job.FAILURE, Job.SUCCESS], Evaluation.CANCELLED],
        [2, [Job.SUCCESS, Job.CANCELLED], Evaluation.CANCELLED],
        [2, [Job.SUCCESS, Job.SUCCESS], Evaluation.VALIDATING_INPUTS],
        [2, [Job.FAILURE, Job.CANCELLED], Evaluation.CANCELLED],
        [2, [Job.PENDING, Job.SUCCESS], Evaluation.CANCELLED],
    ),
)
@pytest.mark.django_db
def test_create_evaluation_blocked_if_failed_jobs_exist(
    num_jobs,
    jobs_statuses,
    status,
    settings,
    django_capture_on_commit_callbacks,
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)

    ci_str = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    ci_bool = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)

    interface = AlgorithmInterfaceFactory(inputs=[ci_str], outputs=[ci_bool])
    phase.algorithm_interfaces.add(interface)

    user = UserFactory()
    phase.challenge.add_admin(user)
    InvoiceFactory(
        challenge=phase.challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    MethodFactory(
        phase=phase,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    archive = ArchiveFactory()
    phase.archive = archive
    phase.save()

    civs = []
    for i in range(num_jobs):
        ai = ArchiveItemFactory(archive=archive)
        civ = ComponentInterfaceValueFactory(
            interface=ci_str, value=f"foo-{i}"
        )
        ai.values.set([civ])
        civs.append(civ)

    algorithm = AlgorithmFactory()
    algorithm.interfaces.add(interface)
    algorithm.add_editor(user)
    ai = AlgorithmImageFactory(algorithm=algorithm)

    for i in range(num_jobs):
        j = AlgorithmJobFactory(
            algorithm_image=ai,
            time_limit=10,
            status=jobs_statuses[i],
            creator=None,
            algorithm_interface=interface,
        )
        j.inputs.set([civs[i]])

    submission = SubmissionFactory(
        phase=phase, creator=user, algorithm_image=ai
    )

    with patch(
        "grandchallenge.evaluation.tasks.prepare_and_execute_evaluation"
    ) as mocked_execute_eval:
        mocked_execute_eval.return_value = None
        with django_capture_on_commit_callbacks(execute=True):
            submission.create_evaluation(additional_inputs=None)

    eval = Evaluation.objects.order_by("created").last()
    assert eval.status == status
    if status == Evaluation.CANCELLED:
        assert (
            "There are non-successful jobs for this submission. These need to be handled first before you can re-evaluate. Please contact support."
            in str(eval.error_message)
        )


@pytest.mark.django_db
def test_reschedule_evaluation_blocked_if_failed_jobs_with_complete_inputs_exist(
    settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    phase = PhaseFactory(submission_kind=SubmissionKindChoices.ALGORITHM)

    ci_str1 = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    ci_str2 = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)
    ci_bool = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)

    interface = AlgorithmInterfaceFactory(
        inputs=[ci_str1, ci_str2], outputs=[ci_bool]
    )
    phase.algorithm_interfaces.add(interface)

    user = UserFactory()
    phase.challenge.add_admin(user)
    InvoiceFactory(
        challenge=phase.challenge,
        support_costs_euros=0,
        compute_costs_euros=10,
        storage_costs_euros=0,
        payment_status=PaymentStatusChoices.PAID,
    )
    MethodFactory(
        phase=phase,
        is_desired_version=True,
        is_manifest_valid=True,
        is_in_registry=True,
    )
    archive = ArchiveFactory()
    phase.archive = archive
    phase.save()

    civs = []
    for i in range(5):
        ai = ArchiveItemFactory(archive=archive)
        civ1 = ComponentInterfaceValueFactory(
            interface=ci_str1, value=f"foo-{i}"
        )
        civ2 = ComponentInterfaceValueFactory(
            interface=ci_str2, value=f"bar-{i}"
        )
        ai.values.set([civ1, civ2])
        civs.append([civ1, civ2])

    algorithm = AlgorithmFactory()
    algorithm.interfaces.add(interface)
    algorithm.add_editor(user)
    ai = AlgorithmImageFactory(algorithm=algorithm)

    # 3 successful jobs with complete inputs
    for i in range(3):
        j = AlgorithmJobFactory(
            algorithm_image=ai,
            time_limit=10,
            status=Job.SUCCESS,
            creator=None,
            algorithm_interface=interface,
        )
        j.inputs.set(civs[i])

    # 1 failed job with partial input -- should be ignored
    j = AlgorithmJobFactory(
        algorithm_image=ai,
        time_limit=10,
        status=Job.FAILURE,
        creator=None,
        algorithm_interface=interface,
    )
    j.inputs.set([civs[3][0]])

    # 1 failed job with additional input -- should be ignored
    j_add = AlgorithmJobFactory(
        algorithm_image=ai,
        time_limit=10,
        status=Job.FAILURE,
        creator=None,
        algorithm_interface=interface,
    )
    j_add.inputs.set([*civs[4], ComponentInterfaceValueFactory()])

    submission = SubmissionFactory(
        phase=phase, creator=user, algorithm_image=ai
    )
    with patch(
        "grandchallenge.evaluation.tasks.prepare_and_execute_evaluation"
    ) as mocked_execute_eval:
        mocked_execute_eval.return_value = None
        with django_capture_on_commit_callbacks(execute=True):
            submission.create_evaluation(additional_inputs=None)

    eval = Evaluation.objects.order_by("created").last()
    assert eval.status == Evaluation.VALIDATING_INPUTS


@pytest.mark.django_db
def test_phase_starter_kit_detail(client):
    challenge = ChallengeFactory()
    admin, participant, user = UserFactory.create_batch(3)

    challenge.add_admin(admin)
    challenge.add_participant(participant)

    # Note: missing archive / algorithm submission kind
    phase_not_setup = PhaseFactory(
        challenge=challenge,
        submission_kind=SubmissionKindChoices.CSV,
    )

    phase_setup = PhaseFactory(
        challenge=challenge,
        archive=ArchiveFactory(),
        submission_kind=SubmissionKindChoices.ALGORITHM,
    )

    phase_setup.algorithm_interfaces.set(
        [
            AlgorithmInterfaceFactory(
                inputs=[
                    ComponentInterfaceFactory(
                        kind=ComponentInterface.Kind.IMAGE
                    ),
                ],
                outputs=[
                    ComponentInterfaceFactory(
                        kind=ComponentInterface.Kind.FLOAT
                    ),
                ],
            )
        ]
    )

    for phase in [phase_not_setup, phase_setup]:
        # Permissions
        for usr in [participant, user]:
            response = get_view_for_user(
                viewname="evaluation:phase-starter-kit-detail",
                reverse_kwargs={
                    "slug": phase.slug,
                    "challenge_short_name": phase.challenge.short_name,
                },
                client=client,
                user=usr,
            )

            assert (
                response.status_code == 403
            ), "Participant or anonym user should not be able to view starter kit info"

        # Admin
        response = get_view_for_user(
            viewname="evaluation:phase-starter-kit-detail",
            reverse_kwargs={
                "slug": phase.slug,
                "challenge_short_name": phase.challenge.short_name,
            },
            client=client,
            user=admin,
        )

        assert response.status_code == 200, "Admin can view starter kit info"


@pytest.mark.django_db
def test_phase_starter_kit_download(client):
    phase = PhaseFactory(
        archive=ArchiveFactory(),
        submission_kind=SubmissionKindChoices.ALGORITHM,
    )

    phase.algorithm_interfaces.set(
        [
            AlgorithmInterfaceFactory(
                inputs=[
                    ComponentInterfaceFactory(
                        kind=ComponentInterface.Kind.IMAGE
                    ),
                ],
                outputs=[
                    ComponentInterfaceFactory(
                        kind=ComponentInterface.Kind.FLOAT
                    ),
                ],
            )
        ]
    )

    admin, participant, user = UserFactory.create_batch(3)
    phase.challenge.add_admin(admin)
    phase.challenge.add_participant(participant)

    for usr in [participant, user]:
        response = get_view_for_user(
            viewname="evaluation:phase-starter-kit-download",
            reverse_kwargs={
                "slug": phase.slug,
                "challenge_short_name": phase.challenge.short_name,
            },
            client=client,
            user=usr,
        )
        assert (
            response.status_code == 403
        ), "Participant or anonym user should not be able to download starter kit"

    response = get_view_for_user(
        viewname="evaluation:phase-starter-kit-download",
        reverse_kwargs={
            "slug": phase.slug,
            "challenge_short_name": phase.challenge.short_name,
        },
        client=client,
        user=admin,
    )

    assert (
        response.status_code == 200
    ), "Admin can download starer kit"  # Sanity

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
        Path(phase.slug) / "example-algorithm" / "Dockerfile",
        Path(phase.slug) / "example-algorithm" / "inference.py",
        Path(phase.slug) / "example-evaluation-method" / "Dockerfile",
        Path(phase.slug) / "example-evaluation-method" / "evaluate.py",
        Path(phase.slug) / "upload-to-archive" / "upload_files.py",
    ]
    for file_name in expected_files:
        assert (
            str(file_name) in zip_file.namelist()
        ), f"{file_name} is in the ZIP file"
