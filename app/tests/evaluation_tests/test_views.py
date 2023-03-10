import json
from datetime import timedelta

import factory
import pytest
from django.conf import settings
from django.db.models import signals
from django.utils import timezone
from factory.django import ImageField
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.workstations.models import Workstation
from tests.archives_tests.factories import ArchiveFactory
from tests.components_tests.factories import ComponentInterfaceFactory
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
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestLoginViews:
    def test_login_redirect(self, client):
        e = EvaluationFactory()

        for view_name, kwargs in [
            ("phase-create", {}),
            ("phase-update", {"slug": e.submission.phase.slug}),
            ("method-create", {}),
            ("method-list", {}),
            ("method-detail", {"pk": e.method.pk}),
            ("submission-create", {"slug": e.submission.phase.slug}),
            ("submission-create-legacy", {"slug": e.submission.phase.slug}),
            ("submission-list", {}),
            ("submission-detail", {"pk": e.submission.pk}),
            ("list", {}),
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
                {},
                "change_challenge",
                e.submission.phase.challenge,
            ),
            ("method-detail", {"pk": e.method.pk}, "view_method", e.method),
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
                "submission-detail",
                {"pk": e.submission.pk},
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
            ("method-list", {}, "view_method", m),
            ("submission-list", {}, "view_submission", s),
            ("list", {}, "view_evaluation", e),
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

        u = UserFactory()
        e1 = EvaluationFactory(
            method__phase__challenge=c1,
            submission__phase__challenge=c1,
            submission__creator=u,
        )
        e2 = EvaluationFactory(
            method__phase__challenge=c2,
            submission__phase__challenge=c2,
            submission__creator=u,
        )

        assign_perm("view_method", u, e1.method)
        assign_perm("view_method", u, e2.method)

        for view_name, obj in [
            ("method-list", e1.method),
            ("submission-list", e1.submission),
            ("list", e1),
        ]:
            response = get_view_for_user(
                client=client,
                viewname=f"evaluation:{view_name}",
                reverse_kwargs={
                    "challenge_short_name": e1.submission.phase.challenge.short_name
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

    # Participants should only be able to see their own evaluations
    response = get_view_for_user(
        viewname="evaluation:list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.challenge_set_1.participant,
    )
    assert str(e_p_s1.pk) in response.rendered_content
    assert str(e_p_s2.pk) in response.rendered_content
    assert str(e_p1_s1.pk) not in response.rendered_content
    assert str(e_p12_s1_c1.pk) not in response.rendered_content
    assert str(e_p12_s1_c2.pk) not in response.rendered_content

    # Admins should be able to see all evaluations
    response = get_view_for_user(
        viewname="evaluation:list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.challenge_set_1.admin,
    )
    assert str(e_p_s1.pk) in response.rendered_content
    assert str(e_p_s2.pk) in response.rendered_content
    assert str(e_p1_s1.pk) in response.rendered_content
    assert str(e_p12_s1_c1.pk) in response.rendered_content
    assert str(e_p12_s1_c2.pk) not in response.rendered_content

    # Only evaluations relevant to this challenge should be listed
    response = get_view_for_user(
        viewname="evaluation:list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.participant12,
    )
    assert str(e_p12_s1_c1.pk) in response.rendered_content
    assert str(e_p12_s1_c2.pk) not in response.rendered_content
    assert str(e_p_s1.pk) not in response.rendered_content
    assert str(e_p_s2.pk) not in response.rendered_content
    assert str(e_p1_s1.pk) not in response.rendered_content


@pytest.mark.django_db
def test_hidden_phase_visible_for_admins_but_not_participants(client):
    ch = ChallengeFactory()
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
        ("list", {}, 200),
        ("submission-list", {}, 200),
        # visible phase
        ("detail", {"pk": e1.pk}, 200),
        ("submission-create", {"slug": visible_phase.slug}, 200),
        ("submission-detail", {"pk": e1.submission.pk}, 200),
        ("leaderboard", {"slug": visible_phase.slug}, 200),
        # hidden phase
        ("detail", {"pk": e2.pk}, 403),
        ("submission-create", {"slug": hidden_phase.slug}, 200),
        ("submission-detail", {"pk": e2.submission.pk}, 403),
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
            assert f"{visible_phase.title}</a>" in response.rendered_content
            assert f"{hidden_phase.title}</a>" not in response.rendered_content
        if "list" in view_name:
            assert (
                f"<td>{visible_phase.title}</td>" in response.rendered_content
            )
            assert (
                f"<td>{hidden_phase.title}</td>"
                not in response.rendered_content
            )

        # for the admin both phases are visible and they have access to submissions
        # and evals from both phases
        response = get_view_for_user(
            client=client,
            viewname=f"evaluation:{view_name}",
            reverse_kwargs={"challenge_short_name": ch.short_name, **kwargs},
            user=ch.admins_group.user_set.first(),
        )
        assert response.status_code == 200
        assert f"{visible_phase.title}</a>" in response.rendered_content
        assert f"{hidden_phase.title}</a>" in response.rendered_content
        if "list" in view_name:
            assert (
                f"<td>{visible_phase.title}</td>" in response.rendered_content
            )
            assert (
                f"<td>{hidden_phase.title}</td>" in response.rendered_content
            )


@pytest.mark.django_db
def test_create_algorithm_for_phase_permission(client):
    phase = PhaseFactory()
    admin, participant, user = UserFactory.create_batch(3)
    phase.challenge.add_admin(admin)
    phase.challenge.add_participant(participant)

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
        "You need to verify your account before you can do this, you can request this from your profile page."
        in str(response.content)
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
    assert (
        "You need to verify your account before you can do this, you can request this from your profile page."
        in str(response.content)
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
    phase.algorithm_inputs.set([ci1])
    phase.algorithm_outputs.set([ci2])
    phase.hanging_protocol = HangingProtocolFactory()
    phase.workstation_config = WorkstationConfigFactory()
    phase.view_content = {"main": [ci1.slug]}
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
            "image_requires_memory_gb": 1,
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
    assert algorithm.workstation_config == phase.workstation_config
    assert algorithm.view_content == phase.view_content
    assert algorithm.workstation.slug == settings.DEFAULT_WORKSTATION_SLUG
    assert algorithm.contact_email == admin.email
    assert algorithm.display_editors
    assert list(algorithm.structures.all()) == []
    assert list(algorithm.modalities.all()) == []
    assert algorithm.logo == phase.challenge.logo

    # try to set different values
    ci3, ci4 = ComponentInterfaceFactory.create_batch(2)
    hp = HangingProtocolFactory()
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
            "image_requires_memory_gb": 1,
            "inputs": [ci3.pk],
            "outputs": [ci2.pk],
            "workstation": ws.pk,
            "hanging_protocol": hp.pk,
            "workstation_config": wsc.pk,
            "view_content": "{}",
        },
    )

    # created algorithm has the initial values set, not the modified ones
    alg2 = Algorithm.objects.last()
    assert alg2.inputs.get() == ci1
    assert alg2.outputs.get() == ci2
    assert alg2.hanging_protocol == phase.hanging_protocol
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
