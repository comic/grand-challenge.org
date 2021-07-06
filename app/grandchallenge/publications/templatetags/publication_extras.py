from django import template

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.archives.models import Archive
from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.reader_studies.models import ReaderStudy

register = template.Library()


@register.filter
def get_associated_objects(publication):
    objects = {}
    for archive in publication.archive_set.all():
        objects[Archive.objects.filter(pk=archive.pk).get()] = (
            Archive.objects.filter(pk=archive.pk).get()._meta.model_name
        )

    for algorithm in publication.algorithm_set.all():
        objects[Algorithm.objects.filter(pk=algorithm.pk).get()] = (
            Algorithm.objects.filter(pk=algorithm.pk).get()._meta.model_name
        )

    for readerstudy in publication.readerstudy_set.all():
        objects[ReaderStudy.objects.filter(pk=readerstudy.pk).get()] = (
            ReaderStudy.objects.filter(pk=readerstudy.pk)
            .get()
            ._meta.model_name
        )

    for challenge in publication.challenge_set.all():
        objects[Challenge.objects.filter(pk=challenge.pk).get()] = (
            Challenge.objects.filter(pk=challenge.pk).get()._meta.model_name
        )

    for extchallenge in publication.externalchallenge_set.all():
        objects[ExternalChallenge.objects.filter(pk=extchallenge.pk).get()] = (
            ExternalChallenge.objects.filter(pk=extchallenge.pk)
            .get()
            ._meta.model_name
        )

    return objects
