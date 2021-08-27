from datetime import timedelta

import factory
import pytest
from django.db.models import signals
from django.utils import timezone
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.evaluation.models import Evaluation
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


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
                    "challenge_short_name": e1.submission.phase.challenge.short_name,
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

    SubmissionFactory(
        phase=phase, creator=two_challenge_sets.challenge_set_1.participant,
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
        phase=phase, creator=two_challenge_sets.challenge_set_1.participant,
    )
    s.created = timezone.now() - timedelta(hours=23)
    s.save()
    assert "create 8 more" in get_submission_view().rendered_content

    s = SubmissionFactory(
        phase=phase, creator=two_challenge_sets.challenge_set_1.participant,
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
