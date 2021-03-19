import logging

from celery import shared_task

from grandchallenge.publications.models import Publication
from grandchallenge.publications.utils import get_identifier_csl

logger = logging.getLogger(__name__)


@shared_task
def update_publication_metadata():
    for publication in Publication.objects.all():
        try:
            csl, new_identifier = get_identifier_csl(
                doi_or_arxiv=publication.identifier
            )
        except ValueError:
            logger.warning(
                f"Identifier {publication.identifier} not recognised"
            )
            continue

        publication.identifier = new_identifier
        publication.csl = csl
        publication.save()
