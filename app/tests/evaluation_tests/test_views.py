import json
from datetime import timedelta

import factory
import pytest
from django.conf import settings
from django.core.cache import cache
from django.db.models import signals
from django.utils import timezone
from factory.django import ImageField
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.evaluation.models import CombinedLeaderboard, Evaluation
from grandchallenge.evaluation.tasks import update_combined_leaderboard
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.invoices.models import PaymentStatusChoices
from grandchallenge.workstations.models import Workstation
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import (
    CombinedLeaderboardFactory,
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
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestLoginViews:
    def test_login_redirect(self, client):
        e = EvaluationFactory()

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
            ("submission-create-legacy", {"slug": e.submission.phase.slug}),
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
        e = EvaluationFactory(submission__phase__challenge__hidden=False)

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
        e = EvaluationFactory()
        u = UserFactory()
        VerificationFactory(user=u, is_verified=True)

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
                "submission-create-legacy",
                {"slug": e.submission.phase.slug},
                "change_challenge",
                e.submission.phase.challenge,
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
            ("update", {"pk": e.pk}, "change_evaluation", e),
            ("detail", {"pk": e.pk}, "view_evaluation", e),
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

            assign_perm(permission, u, obj)

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

            remove_perm(permission, u, obj)

    def test_permission_filtered_views(self, client):
        u = UserFactory()
        p = PhaseFactory()
        m = MethodFactory(phase=p)
        s = SubmissionFactory(phase=p, creator=u)
        e = EvaluationFactory(
            method=m, submission=s, rank=1, status=Evaluation.SUCCESS
        )

        for view_name, kwargs, permission, obj in [
            (
                "method-list",
                {"slug": e.submission.phase.slug},
                "view_method",
                m,
            ),
            ("submission-list", {}, "view_submission", s),
            ("list", {"slug": e.submission.phase.slug}, "view_evaluation", e),
            (
                "leaderboard",
                {"slug": e.submission.phase.slug},
                "view_evaluation",
                e,
            ),
        ]:

            assign_perm(permission, u, obj)

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

            remove_perm(permission, u, obj)

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
        )
        e2 = EvaluationFactory(
            method__phase=c2.phase_set.first(),
            submission__phase=c2.phase_set.first(),
            submission__creator=u,
        )

        assign_perm("view_method", u, e1.method)
        assign_perm("view_method", u, e2.method)

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
        )
        _ = EvaluationFactory(
            method__phase=p2,
            submission__phase=p2,
            rank=1,
            status=Evaluation.SUCCESS,
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
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
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
@factory.django.mute_signals(signals.post_save)
def test_evaluation_list(client, two_challenge_sets):
    # participant 0, submission 1, challenge 1, etc
    e_p_s1 = EvaluationFactory(
        submission__phase=two_challenge_sets.challenge_set_1.challenge.phase_set.get(),
        submission__creator=two_challenge_sets.challenge_set_1.participant,
    )
    e_p_s2 = EvaluationFactory(
        submission__phase=two_challenge_sets.challenge_set_1.challenge.phase_set.get(),
        submission__creator=two_challenge_sets.challenge_set_1.participant,
    )
    e_p1_s1 = EvaluationFactory(
        submission__phase=two_challenge_sets.challenge_set_1.challenge.phase_set.get(),
        submission__creator=two_challenge_sets.challenge_set_1.participant1,
    )
    # participant12, submission 1 to each challenge
    e_p12_s1_c1 = EvaluationFactory(
        submission__phase=two_challenge_sets.challenge_set_1.challenge.phase_set.get(),
        submission__creator=two_challenge_sets.participant12,
    )
    e_p12_s1_c2 = EvaluationFactory(
        submission__phase=two_challenge_sets.challenge_set_2.challenge.phase_set.get(),
        submission__creator=two_challenge_sets.participant12,
    )
    e_p_s3_p2 = EvaluationFactory(
        submission__phase=PhaseFactory(
            challenge=two_challenge_sets.challenge_set_2.challenge
        ),
        submission__creator=two_challenge_sets.challenge_set_1.participant,
    )

    # Participants should only be able to see their own evaluations from a phase
    response = get_view_for_user(
        viewname="evaluation:list",
        reverse_kwargs={
            "slug": two_challenge_sets.challenge_set_1.challenge.phase_set.first().slug
        },
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.challenge_set_1.participant,
    )
    assert str(e_p_s1.pk) in str(response.content)
    assert str(e_p_s2.pk) in str(response.content)
    assert str(e_p1_s1.pk) not in str(response.content)
    assert str(e_p12_s1_c1.pk) not in str(response.content)
    assert str(e_p12_s1_c2.pk) not in str(response.content)
    assert str(e_p_s3_p2.pk) not in str(response.content)

    # Admins should be able to see all evaluations from a phase
    response = get_view_for_user(
        viewname="evaluation:list",
        reverse_kwargs={
            "slug": two_challenge_sets.challenge_set_1.challenge.phase_set.first().slug
        },
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.challenge_set_1.admin,
    )
    assert str(e_p_s1.pk) in str(response.content)
    assert str(e_p_s2.pk) in str(response.content)
    assert str(e_p1_s1.pk) in str(response.content)
    assert str(e_p12_s1_c1.pk) in str(response.content)
    assert str(e_p12_s1_c2.pk) not in str(response.content)
    assert str(e_p_s3_p2.pk) not in str(response.content)


@pytest.mark.django_db
def test_hidden_phase_visible_for_admins_but_not_participants(client):
    ch = ChallengeFactory()
    PhaseFactory(challenge=ch)
    u = UserFactory()
    ch.add_participant(u)
    visible_phase = ch.phase_set.first()
    hidden_phase = PhaseFactory(challenge=ch, public=False)
    e1 = EvaluationFactory(
        submission__phase=visible_phase, submission__creator=u
    )
    e2 = EvaluationFactory(
        submission__phase=hidden_phase, submission__creator=u
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
        ("submission-create", {"slug": hidden_phase.slug}, 200),
        (
            "submission-detail",
            {"pk": e2.submission.pk, "slug": e2.submission.phase.slug},
            403,
        ),
        ("leaderboard", {"slug": hidden_phase.slug}, 200),
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
            assert f"{visible_phase.title}</a>" in str(response.content)
            assert f"{hidden_phase.title}</a>" not in str(response.content)

        # for the admin both phases are visible and they have access to submissions
        # and evals from both phases
        response = get_view_for_user(
            client=client,
            viewname=f"evaluation:{view_name}",
            reverse_kwargs={"challenge_short_name": ch.short_name, **kwargs},
            user=ch.admins_group.user_set.first(),
        )
        assert response.status_code == 200
        assert f"{visible_phase.title}</a>" in str(response.content)
        assert f"{hidden_phase.title}</a>" in str(response.content)


@pytest.mark.django_db
def test_create_algorithm_for_phase_permission(client, uploaded_image):
    phase = PhaseFactory()
    admin, participant, user = UserFactory.create_batch(3)
    phase.challenge.add_admin(admin)
    phase.challenge.add_participant(participant)

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
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
    phase.algorithm_inputs.set([ComponentInterfaceFactory()])
    phase.algorithm_outputs.set([ComponentInterfaceFactory()])
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
    ci1 = ComponentInterfaceFactory()
    ci2 = ComponentInterfaceFactory()
    optional_protocol = HangingProtocolFactory()
    phase.algorithm_inputs.set([ci1])
    phase.algorithm_outputs.set([ci2])
    phase.hanging_protocol = HangingProtocolFactory()
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
    assert response.context_data["form"]["inputs"].initial.get() == ci1
    assert response.context_data["form"]["outputs"].initial.get() == ci2
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
    assert list(response.context_data["form"]["modalities"].initial) == []
    assert list(response.context_data["form"]["structures"].initial) == []

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
            "title": "Test algorithm",
            "image_requires_memory_gb": 8,
            "inputs": [
                response.context_data["form"]["inputs"].initial.get().pk
            ],
            "outputs": [
                response.context_data["form"]["outputs"].initial.get().pk
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
    assert algorithm.inputs.get() == ci1
    assert algorithm.outputs.get() == ci2
    assert algorithm.hanging_protocol == phase.hanging_protocol
    assert algorithm.optional_hanging_protocols.get() == optional_protocol
    assert algorithm.workstation_config == phase.workstation_config
    assert algorithm.view_content == phase.view_content
    assert algorithm.workstation.slug == settings.DEFAULT_WORKSTATION_SLUG
    assert algorithm.contact_email == admin.email
    assert algorithm.display_editors is True
    assert list(algorithm.structures.all()) == []
    assert list(algorithm.modalities.all()) == []
    assert algorithm.logo == phase.challenge.logo
    assert algorithm.time_limit == 10 * 60

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
            "title": "Test algorithm",
            "image_requires_memory_gb": 8,
            "inputs": [ci3.pk],
            "outputs": [ci2.pk],
            "workstation": ws.pk,
            "hanging_protocol": hp.pk,
            "optional_hanging_protocols": [oph.pk],
            "workstation_config": wsc.pk,
            "view_content": "{}",
        },
    )

    # created algorithm has the initial values set, not the modified ones
    alg2 = Algorithm.objects.last()
    assert alg2.inputs.get() == ci1
    assert alg2.outputs.get() == ci2
    assert alg2.hanging_protocol == phase.hanging_protocol
    assert alg2.optional_hanging_protocols.get() == optional_protocol
    assert alg2.workstation_config == phase.workstation_config
    assert alg2.view_content == phase.view_content
    assert alg2.workstation.slug == settings.DEFAULT_WORKSTATION_SLUG
    assert alg2.inputs.get() != ci3
    assert alg2.outputs.get() != ci4
    assert alg2.hanging_protocol != hp
    assert alg2.workstation_config != wsc
    assert alg2.view_content != "{}"
    assert alg2.workstation.slug != ws
    assert alg2.logo == phase.challenge.logo


@pytest.mark.django_db
def test_create_algorithm_for_phase_limits(client):
    phase = PhaseFactory(challenge__logo=ImageField(filename="test.jpeg"))
    phase.submission_kind = SubmissionKindChoices.ALGORITHM
    phase.creator_must_be_verified = True
    phase.archive = ArchiveFactory()
    ci1 = ComponentInterfaceFactory()
    ci2 = ComponentInterfaceFactory()
    phase.algorithm_inputs.set([ci1])
    phase.algorithm_outputs.set([ci2])
    phase.submissions_limit_per_user_per_period = 10
    phase.save()

    InvoiceFactory(
        challenge=phase.challenge,
        compute_costs_euros=10,
        payment_status=PaymentStatusChoices.COMPLIMENTARY,
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
    alg6.add_editor(u1)
    for alg in [alg1, alg2, alg3, alg4, alg5]:
        alg.inputs.set([ci1])
        alg.outputs.set([ci2])
    ci3 = ComponentInterfaceFactory()
    alg5.inputs.add(ci3)
    alg6.inputs.set([ci3])
    alg6.outputs.set([ci2])

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
    assert '<form  method="post" >' in str(response.content)

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
    assert '<form  method="post" >' in str(response.content)

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
            "image_requires_memory_gb": 1,
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
        method=m, submission=s, rank=1, status=Evaluation.SUCCESS
    )

    response = get_view_for_user(
        client=client,
        viewname="evaluation:evaluation-admin-list",
        reverse_kwargs={
            "challenge_short_name": ch.short_name,
            "slug": ch.phase_set.get().slug,
        },
        user=u,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname="evaluation:evaluation-admin-list",
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
        phase=PhaseFactory(challenge=challenge), requires_memory_gb=4
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
        data={"requires_memory_gb": 16},
    )

    assert response.status_code == 302

    method.refresh_from_db()
    assert method.requires_memory_gb == 16


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
