from .factories import SubmissionFactory


def test_submission():
    submission = SubmissionFactory()
    assert submission.challenge.short_name == 'test_challenge'
