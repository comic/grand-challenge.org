from celery import shared_task

from grandchallenge.publications.models import Publication
from grandchallenge.publications.utils import get_identifier_csl


@shared_task
def update_publication_metadata():
    for publication in Publication.objects.all():
        csl, new_identifier = get_identifier_csl(
            doi_or_arxiv=publication.identifier
        )
        publication.identifier = new_identifier
        publication.csl = csl
        publication.save()
