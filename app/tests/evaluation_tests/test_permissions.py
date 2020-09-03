from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from guardian.shortcuts import get_groups_with_perms, get_users_with_perms

from grandchallenge.evaluation.models import (
    AlgorithmEvaluation,
    Evaluation,
    Method,
    Phase,
    Submission,
)
from tests.evaluation_tests.factories import (
    AlgorithmEvaluationFactory,
    EvaluationFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)


class TestPhasePermissions(TestCase):
    def test_phase_permissions(self):
        """Only challenge admins should be able to view and change phases."""
        p: Phase = PhaseFactory()

        assert get_groups_with_perms(p, attach_perms=True) == {
            p.challenge.admins_group: ["change_phase", "view_phase"]
        }
        assert get_users_with_perms(p, with_group_users=False).count() == 0


class TestMethodPermissions(TestCase):
    def test_method_permissions(self):
        """Only challenge admins should be able to view and change methods."""
        m: Method = MethodFactory()

        assert get_groups_with_perms(m, attach_perms=True) == {
            m.phase.challenge.admins_group: ["change_method", "view_method"]
        }
        assert get_users_with_perms(m, with_group_users=False).count() == 0


class TestSubmissionPermissions(TestCase):
    def test_submission_permissions(self):
        """
        Challenge admins and submission creators should be able to view
        submissions.
        """
        s: Submission = SubmissionFactory()

        assert get_groups_with_perms(s, attach_perms=True) == {
            s.phase.challenge.admins_group: ["view_submission"]
        }
        assert get_users_with_perms(
            s, attach_perms=True, with_group_users=False
        ) == {s.creator: ["view_submission"]}


class TestAlgorithmEvaluationPermissions(TestCase):
    def test_algorithm_evaluation_permissions(self):
        """
        Only the challenge admins should be able to view algorithm evaluations
        The submission creator, algorithm groups and participants should not
        have view permissions
        """
        ae: AlgorithmEvaluation = AlgorithmEvaluationFactory()

        assert get_groups_with_perms(ae, attach_perms=True) == {
            ae.submission.phase.challenge.admins_group: [
                "view_algorithmevaluation"
            ]
        }
        assert get_users_with_perms(ae, with_group_users=False).count() == 0


class TestEvaluationPermissions(TestCase):
    def test_published_evaluation_permissions(self):
        """
        Challenge admins can change and view published evaluations,
        and anyone can view published evaluations
        """
        e: Evaluation = EvaluationFactory(
            submission__phase__auto_publish_new_results=True
        )

        g_reg_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        assert e.published is True
        assert get_groups_with_perms(e, attach_perms=True) == {
            e.submission.phase.challenge.admins_group: [
                "change_evaluation",
                "view_evaluation",
            ],
            g_reg_anon: ["view_evaluation"],
        }
        assert get_users_with_perms(e, with_group_users=False).count() == 0

    def test_unpublished_evaluation_permissions(self):
        """Only challenge admins can change and view unpublished evaluations."""
        e: Evaluation = EvaluationFactory(
            submission__phase__auto_publish_new_results=False
        )

        assert e.published is False
        assert get_groups_with_perms(e, attach_perms=True) == {
            e.submission.phase.challenge.admins_group: [
                "change_evaluation",
                "view_evaluation",
            ],
        }
        assert get_users_with_perms(e, with_group_users=False).count() == 0

    def test_unpublishing_results_removes_permissions(self):
        """
        If an evaluation is unpublished then the view permission should be
        removed.
        """
        e: Evaluation = EvaluationFactory(
            submission__phase__auto_publish_new_results=True
        )
        g_reg_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        assert e.published is True
        assert get_groups_with_perms(e, attach_perms=True) == {
            e.submission.phase.challenge.admins_group: [
                "change_evaluation",
                "view_evaluation",
            ],
            g_reg_anon: ["view_evaluation"],
        }

        e.published = False
        e.save()

        assert get_groups_with_perms(e, attach_perms=True) == {
            e.submission.phase.challenge.admins_group: [
                "change_evaluation",
                "view_evaluation",
            ],
        }
