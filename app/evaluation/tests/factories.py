from factory import Factory, SubFactory

from comicmodels.models import ComicSite
from evaluation.models import Submission, Job, Method, Result


class ComicSiteFactory(Factory):
    class Meta:
        model = ComicSite

    short_name = 'test_challenge'


class SubmissionFactory(Factory):
    class Meta:
        model = Submission

    challenge = SubFactory(ComicSiteFactory)


class JobFactory(Factory):
    class Meta:
        model = Job


class MethodFactory(Factory):
    class Meta:
        model = Method


class ResultFactory(Factory):
    class Meta:
        model = Result
