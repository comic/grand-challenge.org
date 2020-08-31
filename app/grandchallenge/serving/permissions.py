from grandchallenge.evaluation.models import Submission


def user_can_download_submission(*, user, submission: Submission) -> bool:
    return submission.phase.challenge.is_admin(user=user)
