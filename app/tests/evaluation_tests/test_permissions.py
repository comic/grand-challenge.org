import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from guardian.shortcuts import get_groups_with_perms, get_users_with_perms

from grandchallenge.evaluation.models import (
    Evaluation,
    Method,
    Phase,
    Submission,
)
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmModelFactory,
)
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    MethodFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import UserFactory


def get_groups_with_set_perms(*args, **kwargs):
    """
    Executes get_groups_with_perms with attach_perms=True, and converts the
    resulting list for each group to a set for easier comparison in tests as
    the ordering of permissions is not always consistent.
    """
    kwargs.update({"attach_perms": True})
    return {k: {*v} for k, v in get_groups_with_perms(*args, **kwargs).items()}


def get_users_with_set_perms(*args, **kwargs):
    """
    Executes get_users_with_perms with attach_perms=True, and converts the
    resulting list for each group to a set for easier comparison in tests as
    the ordering of permissions is not always consistent.
    """
    kwargs.update({"attach_perms": True})
    return {k: {*v} for k, v in get_users_with_perms(*args, **kwargs).items()}


@pytest.mark.django_db
def test_phase_permissions():
    """Only challenge admins should be able to view and change phases."""
    p: Phase = PhaseFactory()

    assert get_groups_with_set_perms(p) == {
        p.challenge.admins_group: {
            "change_phase",
            "view_phase",
            "create_phase_submission",
        },
        p.challenge.participants_group: {"create_phase_submission"},
    }
    assert get_users_with_perms(p, with_group_users=False).count() == 0


@pytest.mark.django_db
def test_hiding_phase_updates_perms(django_capture_on_commit_callbacks):
    e: Evaluation = EvaluationFactory(
        submission__phase__auto_publish_new_results=True,
        submission__phase__public=True,
        submission__phase__challenge__hidden=False,
        submission__creator=UserFactory(),
        time_limit=60,
    )

    all_users = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )

    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
        all_users: {"view_evaluation"},
    }

    assert get_groups_with_set_perms(e.submission) == {
        e.submission.phase.challenge.admins_group: {"view_submission"},
    }
    assert e.submission.creator.has_perm("view_submission", e.submission)

    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with django_capture_on_commit_callbacks(execute=True):
        e.submission.phase.public = False
        e.submission.phase.save()

    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
    }
    assert get_groups_with_set_perms(e.submission) == {
        e.submission.phase.challenge.admins_group: {"view_submission"},
    }


@pytest.mark.django_db
def test_unhiding_phase_updates_perms(django_capture_on_commit_callbacks):
    e: Evaluation = EvaluationFactory(
        submission__phase__auto_publish_new_results=True,
        submission__phase__public=False,
        submission__phase__challenge__hidden=False,
        submission__creator=UserFactory(),
        time_limit=60,
    )

    all_users = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )

    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
    }
    assert get_groups_with_set_perms(e.submission) == {
        e.submission.phase.challenge.admins_group: {"view_submission"},
    }

    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with django_capture_on_commit_callbacks(execute=True):
        e.submission.phase.public = True
        e.submission.phase.save()

    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
        all_users: {"view_evaluation"},
    }

    assert get_groups_with_set_perms(e.submission) == {
        e.submission.phase.challenge.admins_group: {"view_submission"},
    }
    assert e.submission.creator.has_perm("view_submission", e.submission)


@pytest.mark.django_db
def test_method_permissions():
    """Only challenge admins should be able to view and change methods."""
    m: Method = MethodFactory()

    assert get_groups_with_set_perms(m) == {
        m.phase.challenge.admins_group: {"view_method", "change_method"}
    }
    assert get_users_with_perms(m, with_group_users=False).count() == 0


@pytest.mark.django_db
def test_submission_permissions():
    """
    Challenge admins and submission creators should be able to view
    submissions.
    """
    s: Submission = SubmissionFactory()

    assert get_groups_with_set_perms(s) == {
        s.phase.challenge.admins_group: {"view_submission"}
    }
    assert get_users_with_perms(
        s, attach_perms=True, with_group_users=False
    ) == {s.creator: ["view_submission"]}


@pytest.mark.parametrize("hidden_challenge", [True, False])
@pytest.mark.django_db
def test_published_evaluation_permissions(hidden_challenge):
    """
    Challenge admins can change and view published evaluations.

    If the challenge is hidden, only the participants can view published
    evaluations, otherwise anyone can view published evaluations.
    """
    e: Evaluation = EvaluationFactory(
        submission__phase__auto_publish_new_results=True,
        submission__phase__challenge__hidden=hidden_challenge,
        time_limit=60,
    )

    if hidden_challenge:
        viewer_group = e.submission.phase.challenge.participants_group
    else:
        viewer_group = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

    assert e.published is True
    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
        viewer_group: {"view_evaluation"},
    }
    assert get_users_with_perms(e, with_group_users=False).count() == 0


@pytest.mark.parametrize("hidden_challenge", [True, False])
@pytest.mark.django_db
def test_unpublished_evaluation_permissions(hidden_challenge):
    """Only challenge admins can change and view unpublished evaluations."""
    e: Evaluation = EvaluationFactory(
        submission__phase__auto_publish_new_results=False,
        submission__phase__challenge__hidden=hidden_challenge,
        time_limit=60,
    )

    assert e.published is False
    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        }
    }
    assert get_users_with_perms(e, with_group_users=False).count() == 0


@pytest.mark.parametrize("hidden_challenge", [True, False])
@pytest.mark.django_db
def test_unpublishing_results_removes_permissions(hidden_challenge):
    """
    If an evaluation is unpublished then the view permission should be
    removed.
    """
    e: Evaluation = EvaluationFactory(
        submission__phase__auto_publish_new_results=True,
        submission__phase__challenge__hidden=hidden_challenge,
        time_limit=60,
    )

    if hidden_challenge:
        viewer_group = e.submission.phase.challenge.participants_group
    else:
        viewer_group = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

    assert e.published is True
    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
        viewer_group: {"view_evaluation"},
    }

    e.published = False
    e.save()

    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        }
    }


@pytest.mark.django_db
def test_hiding_challenge_updates_perms(
    settings, django_capture_on_commit_callbacks
):
    """If a challenge is hidden then the viewer group should be updated"""
    e: Evaluation = EvaluationFactory(
        submission__phase__auto_publish_new_results=True,
        submission__phase__challenge__hidden=False,
        time_limit=60,
    )

    participants = e.submission.phase.challenge.participants_group
    all_users = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )

    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
        all_users: {"view_evaluation"},
    }

    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with django_capture_on_commit_callbacks(execute=True):
        e.submission.phase.challenge.hidden = True
        e.submission.phase.challenge.save()

    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
        participants: {"view_evaluation"},
    }


@pytest.mark.django_db
def test_unhiding_challenge_updates_perms(
    settings, django_capture_on_commit_callbacks
):
    """If a challenge is unhidden then the viewer group should be updated"""
    e: Evaluation = EvaluationFactory(
        submission__phase__auto_publish_new_results=True,
        submission__phase__challenge__hidden=True,
        time_limit=60,
    )

    participants = e.submission.phase.challenge.participants_group
    all_users = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )

    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
        participants: {"view_evaluation"},
    }

    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    with django_capture_on_commit_callbacks(execute=True):
        e.submission.phase.challenge.hidden = False
        e.submission.phase.challenge.save()

    assert get_groups_with_set_perms(e) == {
        e.submission.phase.challenge.admins_group: {
            "change_evaluation",
            "view_evaluation",
        },
        all_users: {"view_evaluation"},
    }


@pytest.mark.django_db
def test_external_evaluations_perms():
    phase = PhaseFactory()
    e = EvaluationFactory(submission__phase=phase)

    participants = phase.challenge.participants_group
    admins = phase.challenge.admins_group
    external_evaluators = phase.challenge.external_evaluators_group

    assert get_groups_with_set_perms(e) == {
        admins: {
            "view_evaluation",
            "change_evaluation",
        },
        participants: {"view_evaluation"},
    }

    assert get_groups_with_set_perms(e.submission) == {
        admins: {
            "view_submission",
        },
    }

    phase.external_evaluation = True
    phase.save()
    e2 = EvaluationFactory(
        submission__phase=phase,
        submission__algorithm_image=AlgorithmImageFactory(),
        submission__algorithm_model=AlgorithmModelFactory(),
    )

    assert get_groups_with_set_perms(e2) == {
        admins: {
            "view_evaluation",
            "change_evaluation",
        },
        participants: {"view_evaluation"},
        external_evaluators: {
            "claim_evaluation",
            "view_evaluation",
        },
    }

    assert get_groups_with_set_perms(e2.submission) == {
        admins: {"view_submission"},
    }

    assert get_groups_with_set_perms(e2.submission.algorithm_image) == {
        e2.submission.algorithm_image.algorithm.editors_group: {
            "view_algorithmimage",
            "change_algorithmimage",
        },
        external_evaluators: {"download_algorithmimage"},
    }

    assert get_groups_with_set_perms(e2.submission.algorithm_model) == {
        e2.submission.algorithm_model.algorithm.editors_group: {
            "view_algorithmmodel",
            "change_algorithmmodel",
        },
        external_evaluators: {"download_algorithmmodel"},
    }
